"""Bind verified common native water results to existing jurisdiction pipe rules."""
import argparse
from pathlib import Path
import json
import os
from .cli import digest
from .module_contract import read_json,validate
from .modules import ROOT,verify_result
from .epanet_pipe_regulations import prepare
from .regulations import evaluate,source_paths,method_paths


def paths(basis,pack,sources):
    data=read_json(pack)
    if not data.get('rules') or any(r['method']!='hvac_water_piping' for r in data['rules']):raise ValueError('Existing HVAC water-piping rule method required')
    official=source_paths(data,sources)
    methods={Path(__file__),*[Path(__file__).with_name(n) for n in ('epanet_pipe_regulations.py','regulations.py','water_pipe_rules.py')],*method_paths(data)}
    methods.update({ROOT/'src/bsa/module_contract.py',ROOT/'contracts/modules/rule-assessment-v1.json'})
    return {Path(basis).resolve(),Path(pack).resolve(),*methods,*[p for p in official if p.is_file()]},official


def assessment(checks,pack,producer_hash,coordinate_frame):
    rules={r['id']:r for r in pack['rules']};rows=[]
    for entity,result in sorted(checks.items()):
        for row in result['checks']:
            rule=rules[row['id']];source=pack['sources'][rule['source_id']]
            original=row['status'];state='pass' if original=='pass' else 'fail' if original=='review_required' else 'pending'
            rows.append(dict(entity_id=entity,rule_id=row['id'],status=state,original_status=original,
                source_id=rule['source_id'],source_sha256=source['sha256'],edition=source['edition'],
                clause=rule['clause'],scope=row['scope']))
    states=[r['status'] for r in rows]
    return validate(dict(schema='bsa.rule-assessment/1',coordinate_frame=coordinate_frame,jurisdiction=pack['jurisdiction'],rule_pack=pack['id'],
        producer_sha256=producer_hash,status='fail' if 'fail' in states else 'pending' if 'pending' in states else 'pass',
        coverage=[dict(entity_id=entity,implemented=result['coverage']['implemented'],pending=result['coverage']['pending']) for entity,result in sorted(checks.items())],
        checks=rows,coverage_complete=False,regulatory_compliance='not_established',design_accepted=False))


def binding(producer,basis,pack,sources):
    producer=Path(producer).resolve();module=verify_result(producer)
    if module['execution']['status']!='completed' or module['payload_schema']!='bsa.bound-water-graph/1' or module['payload']['status']!='pass':raise ValueError('Passing verified saved-native water graph required')
    payload=module['payload'];network=read_json(producer.parent/payload['network_input']['path']);hydraulic=read_json(producer.parent/payload['report']['path'])
    origin='Verified saved-native water module '+str(producer)+' SHA256 '+digest(producer)
    fluid,projects=prepare(network,read_json(basis),hydraulic,origin)
    if any(p.get('jurisdiction')!=pack['jurisdiction'] or p.get('rule_pack')!=pack['id'] for p in projects.values()):raise ValueError('Explicit matching jurisdiction/rule pack required for every pipe')
    checks={id:evaluate(pack,p,sources) for id,p in projects.items()}
    exceeded=any(c['status']=='review_required' for r in checks.values() for c in r['checks'])
    status='fail' if exceeded else 'pass' if checks and all(r['supported_checks_pass'] for r in checks.values()) else 'pending'
    return module,fluid,projects,checks,status


def run(producer,basis,pack,sources,out):
    producer,basis,pack,sources,out=[Path(p).resolve() for p in (producer,basis,pack,sources,out)]
    if not out.is_relative_to(ROOT):raise ValueError('Repository-local rule output required')
    files,official=paths(basis,pack,sources);module=verify_result(producer)
    pins={str(p):digest(p) for p in files|{producer}};pins.update(module['inputs'])
    snapshot={str(p):digest(p) if p.is_file() else None for p in official}
    if out.exists() or any(out==Path(p) or out in Path(p).parents for p in [*pins,*snapshot]):raise ValueError('New rule output separate from sources required')
    _,fluid,projects,checks,status=binding(producer,basis,read_json(pack),sources)
    if any(digest(Path(p))!=h for p,h in pins.items()) or any((digest(Path(p)) if Path(p).is_file() else None)!=h for p,h in snapshot.items()):raise ValueError('Water rule source changed')
    verify_result(producer);out.mkdir(parents=True)
    (out/'bound-pipe-projects.json').write_text(json.dumps(projects,indent=2),encoding='utf-8')
    report=dict(producer_result=str(producer),basis=str(basis),pack=str(pack),sources=str(sources),inputs=pins,source_snapshot=snapshot,
        missing_sources=[p for p,h in snapshot.items() if h is None],fluid_basis=fluid,segment_checks=checks,status=status,
        artifacts={'bound-pipe-projects.json':digest(out/'bound-pipe-projects.json')},design_accepted=False,regulatory_compliance='not_established',
        scope='Saved-native selected-system water quantities bound to scoped HVAC water-piping rules only;code diameter,fluid/edition/applicability remain sourced assertions;not domestic-water or full conformity')
    report['assessment']=assessment(checks,read_json(pack),digest(producer),module['payload']['coordinate_frame'])
    (out/'module-water-rules.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


def verify(folder):
    folder=Path(folder).resolve()
    if (folder/'provider/result.json').is_file():return registered_report(folder)
    report=read_json(folder/'module-water-rules.json')
    files,official=paths(report['basis'],report['pack'],report['sources']);module=verify_result(report['producer_result'])
    expected_pins={str(p):digest(p) for p in files|{Path(report['producer_result'])}};expected_pins.update(module['inputs'])
    if expected_pins!=report['inputs']:raise ValueError('Water rule input/method inventory differs')
    snapshot={str(p):digest(p) if p.is_file() else None for p in official}
    if snapshot!=report['source_snapshot'] or report['missing_sources']!=[p for p,h in snapshot.items() if h is None]:raise ValueError('Water rule source availability changed')
    _,fluid,projects,checks,status=binding(report['producer_result'],report['basis'],read_json(report['pack']),report['sources'])
    if report['assessment']!=assessment(checks,read_json(report['pack']),digest(Path(report['producer_result'])),module['payload']['coordinate_frame']):raise ValueError('Common rule assessment differs from replay')
    if read_json(folder/'bound-pipe-projects.json')!=projects or report['artifacts']!={'bound-pipe-projects.json':digest(folder/'bound-pipe-projects.json')}:raise ValueError('Water rule bound facts differ')
    if report['segment_checks']!=checks or report['fluid_basis']!=fluid or report['status']!=status or report['design_accepted'] is not False or report['regulatory_compliance']!='not_established':raise ValueError('Water rule results differ from replay')
    return report


def run_registered(producer,basis,pack,sources,out,*,disabled=False):
    """Materialize the same verified producer into the trusted rule boundary."""
    from .modules import run as run_module
    producer,basis,pack,sources,out=[Path(p).resolve() for p in (producer,basis,pack,sources,out)]
    upstream=verify_result(producer)
    if out.exists():raise ValueError('New registered rule task output required')
    out.mkdir(parents=True)
    request=dict(schema='bsa.module-request/1',project_id=upstream['project_id'],scenario_id=upstream['scenario_id'],
        capability='regulation.water.saved-native',coordinate_frame=upstream['payload']['coordinate_frame'],
        sources={k:dict(path=os.path.relpath(p,out),sha256=digest(p)) for k,p in [('producer',producer),('basis',basis),('pack',pack)]})
    path=out/'request.json';path.write_text(json.dumps(request,indent=2),encoding='utf-8')
    run_module(path,'bsa.hvac-water-rules',out/'provider',runtime=dict(sources=sources),disabled=disabled)
    return registered_report(out)


def registered_report(folder):
    result=verify_result(Path(folder)/'provider/result.json')
    if result['provider']['id']!='bsa.hvac-water-rules':raise ValueError('Unexpected registered water rule provider')
    if result['execution']['status']=='completed':return verify(Path(folder)/'provider/rules')
    request_path=Path(result['request']['path']);request=read_json(request_path)
    sources={k:str((request_path.parent/r['path']).resolve()) for k,r in request['sources'].items()}
    return dict(producer_result=sources['producer'],basis=sources['basis'],pack=sources['pack'],
        status='fail' if result['execution']['status']=='failed' else 'pending',inputs=result['inputs'],
        scope='Registered water rule provider '+result['execution']['status']+';no engineering assessment produced')


def validate_gates(tasks):
    """Prevent known water/drawing consumers from borrowing another model's check."""
    known={t['id']:t for t in tasks};ancestors={}
    for task in tasks:
        parents=set(task.get('requires_pass',[]))|({task['depends_on']} if task.get('depends_on') else set())
        upstream=set(parents)
        for parent in parents:upstream.update(ancestors.get(parent,set()))
        ancestors[task['id']]=upstream
        for name in upstream:
            rule=known[name]
            if rule['kind']!='module_water_rules':continue
            producer=known[rule['depends_on']];model=producer.get('depends_on')
            if task['kind'] in ('ifc_views','ifc_views_native'):
                view=known.get(task.get('depends_on'),{}) if task['kind']=='ifc_views_native' else task
                if view.get('kind')!='ifc_views' or model is None or view.get('depends_on')!=model:raise ValueError('Water rule drawing gate requires the same native authoring producer')
            elif task['kind'] in ('water_network','water_coordination','circulation_duty','epanet_pipe_regulations','regulated_water_model','water_pipe_regulations','module_analysis','module_authoring','ifc_drawing','ifc_native'):
                raise ValueError('Water rule gate has no supported same-producer handoff for this consumer;replacement inputs forbidden')


def verify_workflow(tasks,root,plan_root,report_tasks):
    from .workflow_modules import result_path
    known={t['id']:t for t in tasks}
    for task in tasks:
        if task['kind']!='module_water_rules':continue
        folder=Path(root)/task['id'];path=folder/'module-water-rules.json';registered=folder/'provider/result.json'
        if not path.is_file() and not registered.is_file() and report_tasks[task['id']]['status']!='pass':continue
        if registered.is_file()!=bool(task.get('provider')):raise ValueError('Water rule provider differs from declared task')
        report=verify(folder);expected=result_path(root,known[task['depends_on']]).resolve()
        if registered.is_file():
            result=verify_result(registered)
            selection=read_json(Path(root)/'workflow.json')['module_selection']
            disabled='bsa.hvac-water-rules' in selection['disabled_providers']
            if disabled!=any(d['code']=='provider_disabled' for d in result['execution']['diagnostics']):raise ValueError('Water rule disable state differs from host selection')
        keys=('basis','pack','sources') if 'sources' in report else ('basis','pack')
        if Path(report['producer_result']).resolve()!=expected or any(Path(report[k]).resolve()!=(Path(plan_root)/task[k]).resolve() for k in keys):raise ValueError('Workflow water rule inputs differ from declared producer/basis/pack/sources')
        if report_tasks[task['id']]['status']!=report['status']:raise ValueError('Workflow water rule status contradicts retained result')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('producer')
    for key in ('basis','pack','sources','out'):p.add_argument('--'+key,required=True)
    args=p.parse_args();result=run(args.producer,args.basis,args.pack,args.sources,args.out);verify(args.out)
    print(result['status']+';full compliance not established');raise SystemExit(0 if result['status']=='pass' else 2)
