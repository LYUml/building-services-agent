"""Bind neutral saved-space geometry to the existing source-pinned office LPD rules."""
import argparse
import copy
import json
from pathlib import Path
from .cli import digest
from .module_contract import read_json
from .modules import verify_result
from .regulations import evaluate,source_paths


def prepare(result,bases,pack):
    if result['execution']['status']!='completed' or result['payload_schema'] not in ('bsa.spatial-boxes/1','bsa.spatial-polygons/1'):raise ValueError('Completed supported neutral spaces required')
    if result['payload_schema']=='bsa.spatial-polygons/1':
        from .module_contract import validate
        validate(result['payload'])
    if not pack.get('rules') or any(r['method']!='office_lighting_power_density' for r in pack['rules']):raise ValueError('Only the existing office LPD rule method is supported')
    spaces={s['id']:s for s in result['payload']['spaces']}
    if not isinstance(bases,dict) or set(bases)!=set(spaces):raise ValueError('Explicit lighting bases must cover every neutral space exactly')
    projects={};ids=set()
    for guid,space in spaces.items():
        basis=bases[guid]
        if not isinstance(basis,dict) or set(basis)!={'jurisdiction','rule_pack','edition_decisions','facts','lighting_space'}:raise ValueError('Exact sourced lighting basis required')
        if basis['jurisdiction']!=pack['jurisdiction'] or basis['rule_pack']!=pack['id']:raise ValueError('Explicit matching jurisdiction and rule pack required')
        if not isinstance(basis['lighting_space'],dict) or set(basis['lighting_space'])!={'luminaires'}:raise ValueError('Lighting basis must not repeat or replace inherited area')
        lights=basis['lighting_space']['luminaires']
        if not isinstance(lights,list):raise ValueError('Declared luminaire inventory required')
        for light in lights:
            if not isinstance(light,dict) or not isinstance(light.get('id'),str) or not light['id'] or light['id'] in ids:raise ValueError('Unique luminaire identities across all spaces required')
            ids.add(light['id'])
        project=copy.deepcopy(basis)
        project['lighting_space']['internal_floor_area']=dict(value=space['floor_area_m2'],unit='m2',
            source='Geometry-derived neutral saved-space '+guid+';statutory internal-area applicability requires the separate sourced fact')
        projects[guid]=project
    return projects


def input_paths(basis,pack,sources):
    pack=Path(pack).resolve();data=read_json(pack)
    # Known methods are checked before native execution or output creation.
    if not data.get('rules') or any(r['method']!='office_lighting_power_density' for r in data['rules']):raise ValueError('Office LPD rule method required')
    official=source_paths(data,sources)
    methods={Path(__file__),Path(__file__).with_name('regulations.py'),Path(__file__).with_name('lighting_rules.py')}
    return {Path(basis).resolve(),pack,*methods,*[p for p in official if p.is_file()]},official


def run(producer,basis,pack,sources,out):
    producer,basis,pack,sources,out=[Path(p).resolve() for p in (producer,basis,pack,sources,out)]
    result=verify_result(producer);paths,official=input_paths(basis,pack,sources)
    pins={str(p):digest(p) for p in paths|{producer}};pins.update(result['inputs'])
    source_snapshot={str(p):digest(p) if p.is_file() else None for p in official}
    if out.exists() or any(out==Path(p) or out in Path(p).parents for p in [*pins,*source_snapshot]):raise ValueError('New rule output separate from sources required')
    data=read_json(pack);projects=prepare(result,read_json(basis),data)
    checks={guid:evaluate(data,project,sources) for guid,project in projects.items()}
    exceeded=any(c['status']=='review_required' for r in checks.values() for c in r['checks'])
    status='fail' if exceeded else 'pass' if all(r['supported_checks_pass'] for r in checks.values()) else 'pending'
    verify_result(producer)
    if any(digest(Path(p))!=sha for p,sha in pins.items()) or any((digest(Path(p)) if Path(p).is_file() else None)!=sha for p,sha in source_snapshot.items()):raise ValueError('Spatial lighting rule source changed')
    out.mkdir(parents=True)
    (out/'bound-space-projects.json').write_text(json.dumps(projects,indent=2),encoding='utf-8')
    report=dict(inputs=pins,producer_result=str(producer),basis=str(basis),pack=str(pack),sources=str(sources),space_checks=checks,status=status,
        source_snapshot=source_snapshot,missing_sources=[p for p,h in source_snapshot.items() if h is None],
        regulatory_compliance='not_established',design_accepted=False,
        scope='Geometry-bound selected office LPD checks only;statutory area,watts,inventory and applicability remain sourced assertions;no circuit,photometry,controls or full compliance acceptance')
    report['artifacts']={'bound-space-projects.json':digest(out/'bound-space-projects.json')}
    (out/'spatial-lighting-rules.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def verify(folder):
    folder=Path(folder);report=read_json(folder/'spatial-lighting-rules.json')
    for name,sha in report['inputs'].items():
        if digest(Path(name))!=sha:raise ValueError('Spatial lighting rule input changed')
    for name,sha in report['source_snapshot'].items():
        if (digest(Path(name)) if Path(name).is_file() else None)!=sha:raise ValueError('Official rule source availability changed;execute a new run')
    projects=prepare(verify_result(report['producer_result']),read_json(report['basis']),read_json(report['pack']))
    if read_json(folder/'bound-space-projects.json')!=projects or digest(folder/'bound-space-projects.json')!=report['artifacts']['bound-space-projects.json']:raise ValueError('Spatial lighting rule binding changed')
    expected={g:evaluate(read_json(report['pack']),p,report['sources']) for g,p in projects.items()}
    exceeded=any(c['status']=='review_required' for r in expected.values() for c in r['checks'])
    status='fail' if exceeded else 'pass' if all(r['supported_checks_pass'] for r in expected.values()) else 'pending'
    if report['space_checks']!=expected or report['status']!=status:raise ValueError('Spatial lighting rule result differs from replay')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('producer')
    for key in ('basis','pack','sources','out'):parser.add_argument('--'+key,required=True)
    args=parser.parse_args();result=run(args.producer,args.basis,args.pack,args.sources,args.out)
    print(result['status']+';full compliance not established');raise SystemExit(0 if result['status']=='pass' else 2)
