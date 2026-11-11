"""Bind a verified electrical module and explicit radial topology to existing rules."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .module_contract import read_json
from .modules import ROOT,verify_result
from .electrical_paths import calculate_paths,bind_facts
from .regulations import evaluate,source_paths
from .rule_assessment import assessment

METRIC='installation_origin_to_fixed_equipment_voltage_drop'


def paths(topology,basis,pack,sources):
    data=read_json(pack)
    if not data.get('rules') or any(r['method'] not in ('deemed_to_satisfy_maximum','prescriptive_maximum') or r.get('metric')!=METRIC for r in data['rules']):raise ValueError('Existing whole-path voltage-drop rules required')
    official=source_paths(data,sources)
    methods={Path(__file__),*[ROOT/'src/bsa'/n for n in ('electrical_paths.py','regulations.py','rule_assessment.py','module_contract.py')],ROOT/'contracts/modules/rule-assessment-v1.json'}
    return {Path(p).resolve() for p in (topology,basis,pack)}|methods|{p for p in official if p.is_file()},official


def binding(producer,topology,basis,pack,sources):
    module=verify_result(producer)
    if module['execution']['status']!='completed' or module['payload_schema']!='bsa.electrical-circuits/1' or module['payload']['status']!='pass':raise ValueError('Passing verified electrical module required')
    request_path=Path(module['request']['path']);request=read_json(request_path)
    project=read_json((request_path.parent/request['sources']['project']['path']).resolve())
    calculation=calculate_paths(project,read_json(topology))
    if calculation['branch_calculation']!=read_json(Path(producer).parent/module['payload']['report']['path']):raise ValueError('Path calculation differs from inherited branch result')
    declared=read_json(basis)
    if not isinstance(declared.get('facts'),dict):raise ValueError('Explicit sourced regulatory facts required')
    if METRIC in declared['facts']:raise ValueError('Computed full-path voltage drop cannot be overridden in basis')
    projects=bind_facts(calculation,declared,'Verified electrical module '+str(producer)+' SHA256 '+digest(Path(producer))+' with explicit source radial topology')
    checks={name:evaluate(pack,p,sources) for name,p in projects.items()}
    common=assessment(checks,pack,digest(Path(producer)),module['payload']['coordinate_frame'])
    return module,calculation,projects,checks,common


def run(producer,topology,basis,pack,sources,out):
    producer,topology,basis,pack,sources,out=[Path(p).resolve() for p in (producer,topology,basis,pack,sources,out)]
    if not out.is_relative_to(ROOT):raise ValueError('Repository-local rule output required')
    files,official=paths(topology,basis,pack,sources);module=verify_result(producer)
    pins={str(p):digest(p) for p in files|{producer}};pins.update(module['inputs'])
    snapshot={str(p):digest(p) if p.is_file() else None for p in official}
    if out.exists() or any(out==Path(p) or out in Path(p).parents for p in [*pins,*snapshot]):raise ValueError('New rule output separate from sources required')
    _,calculation,projects,checks,common=binding(producer,topology,basis,read_json(pack),sources)
    if any(digest(Path(p))!=h for p,h in pins.items()) or any((digest(Path(p)) if Path(p).is_file() else None)!=h for p,h in snapshot.items()):raise ValueError('Electrical rule source changed')
    out.mkdir(parents=True)
    for name,data in [('path-calculation.json',calculation),('bound-projects.json',projects)]:
        (out/name).write_text(json.dumps(data,indent=2),encoding='utf-8')
    report=dict(producer_result=str(producer),topology=str(topology),basis=str(basis),pack=str(pack),sources=str(sources),
        inputs=pins,source_snapshot=snapshot,missing_sources=[p for p,h in snapshot.items() if h is None],
        circuit_checks=checks,assessment=common,status=common['status'],artifacts={n:digest(out/n) for n in ('path-calculation.json','bound-projects.json')},
        regulatory_compliance='not_established',design_accepted=False,
        scope='Verified branch module plus explicit same-phase radial feeders;whole-path voltage-drop rule only;actual topology,ratings,protection and full compliance remain pending')
    (out/'electrical-module-rules.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


def verify(folder):
    folder=Path(folder).resolve();report=read_json(folder/'electrical-module-rules.json')
    files,official=paths(report['topology'],report['basis'],report['pack'],report['sources']);module=verify_result(report['producer_result'])
    pins={str(p):digest(p) for p in files|{Path(report['producer_result'])}};pins.update(module['inputs'])
    if pins!=report['inputs']:raise ValueError('Electrical rule source/method inventory differs')
    snapshot={str(p):digest(p) if p.is_file() else None for p in official}
    if snapshot!=report['source_snapshot'] or report['missing_sources']!=[p for p,h in snapshot.items() if h is None]:raise ValueError('Electrical rule source availability differs')
    _,calculation,projects,checks,common=binding(report['producer_result'],report['topology'],report['basis'],read_json(report['pack']),report['sources'])
    for name,data in [('path-calculation.json',calculation),('bound-projects.json',projects)]:
        if read_json(folder/name)!=data:raise ValueError('Electrical rule bound path/facts differ')
    if report['artifacts']!={n:digest(folder/n) for n in ('path-calculation.json','bound-projects.json')} or report['circuit_checks']!=checks or report['assessment']!=common or report['status']!=common['status'] or report['design_accepted'] is not False or report['regulatory_compliance']!='not_established':raise ValueError('Electrical rule assessment differs from replay')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('producer')
    for key in ('topology','basis','pack','sources','out'):p.add_argument('--'+key,required=True)
    a=p.parse_args();r=run(a.producer,a.topology,a.basis,a.pack,a.sources,a.out);verify(a.out);print(r['status']+';full compliance not established');raise SystemExit(0 if r['status']=='pass' else 2)
