"""Replay full-model existing clash analysis against a verified terminal-envelope IFC."""
import argparse
import importlib.metadata
import json
from pathlib import Path
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from . import spatial_terminal_ifc as author,clash,solid_clash,circular_geometry


def pins_for(source,policy,report):
    pins=dict(report['inputs']);pins[str(source)]=digest(source);pins[str(policy)]=digest(policy)
    target=source.parent/'Terminal Envelope Study.ifc';pins[str(target)]=digest(target)
    for module in (author,clash,solid_clash,circular_geometry):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    contact=Path(__file__).with_name('contact_clearance.py').resolve();pins[str(contact)]=digest(contact)
    if importlib.metadata.version('ifcopenshell')!='0.8.5' or importlib.metadata.version('manifold3d')!='3.5.4':raise ValueError('Pinned native IFC/Manifold runtimes required')
    return pins


def classify(report,calculation):
    added={r['guid'] for r in report['terminals']};inventory={r['guid'] for r in calculation['elements']}
    if not added<=inventory:raise ValueError('Clash inventory omitted added terminal envelopes')
    partitions={key:dict(intersections=[],clearance_violations=[]) for key in ('terminal_terminal','terminal_existing','existing_existing')}
    for kind in ('intersections','clearance_violations'):
        for row in calculation[kind]:
            count=len(set(row['pair'])&added);key='terminal_terminal' if count==2 else 'terminal_existing' if count else 'existing_existing';partitions[key][kind].append(row)
    return dict(added_terminal_guids=sorted(added),partitions=partitions,whole_model_checks=calculation['checks'],status='pass' if calculation['calculated_checks_pass'] else 'fail',design_accepted=False,
        scope='Complete represented physical-element clash result retained;partitions identify added-terminal involvement,not waivers. Supplied envelope/tolerance policy is not installed clearance or full engineering acceptance')


def run(source,policy,out):
    source,policy,out=[Path(p).resolve() for p in (source,policy,out)]
    if not all(allowed(p) for p in (source,policy,out)) or out.exists() or source.name!='terminal-ifc.json':raise ValueError('Verified terminal IFC,selected policy and fresh output required')
    before=digest(source);report=author.verify(source.parent);pins=pins_for(source,policy,report)
    if pins[str(source)]!=before:raise ValueError('Terminal source changed during verification')
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Coordination output overlaps sources')
    specification=clash.validate_policy(read_json(policy));calculation=clash.inspect(source.parent/'Terminal Envelope Study.ifc',specification);summary=classify(report,calculation)
    author.verify(source.parent)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Coordination source/method changed')
    result=dict(terminal_ifc=str(source),policy=str(policy),inputs=pins,calculation=calculation,summary=summary,design_accepted=False)
    out.mkdir(parents=True);(out/'terminal-coordination.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected coordination workspace required')
    result=read_json(folder/'terminal-coordination.json')
    if set(result)!={'terminal_ifc','policy','inputs','calculation','summary','design_accepted'} or result['design_accepted'] is not False:raise ValueError('Exact unaccepted coordination report required')
    source=Path(result['terminal_ifc']);policy=Path(result['policy'])
    if not all(allowed(p) for p in (source,policy)) or source.name!='terminal-ifc.json':raise ValueError('Selected original terminal model required')
    report=author.verify(source.parent);pins=pins_for(source,policy,report)
    if result['inputs']!=pins or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Coordination source/method pins differ')
    calculation=clash.inspect(source.parent/'Terminal Envelope Study.ifc',clash.validate_policy(read_json(policy)))
    if calculation!=result['calculation'] or classify(report,calculation)!=result['summary']:raise ValueError('Coordination result differs from native replay')
    return result


def verify_workflow(tasks,root,plan_root,record):
    for task in tasks:
        if task['kind']!='spatial_terminal_coordination':continue
        folder=Path(root)/task['id']
        if not (folder/'terminal-coordination.json').is_file():
            if record[task['id']]['status']=='pass':raise ValueError('Passing BIM task lacks report')
            continue
        report=verify(folder)
        if Path(report['terminal_ifc'])!=(Path(root)/task['depends_on']/'terminal-ifc.json').resolve() or Path(report['policy'])!=(Path(plan_root)/task['policy']).resolve():raise ValueError('Spatial BIM task replaced declared inputs')
        expected=report['summary']['status'] if task['kind']=='spatial_terminal_coordination' else 'pass'
        if record[task['id']]['status']!=expected or record[task['depends_on']]['status']!='pass':raise ValueError('Spatial BIM task dependency/status differs')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('--policy',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.source,args.policy,args.out)
