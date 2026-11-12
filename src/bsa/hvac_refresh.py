"""Prepare a fresh HVAC configuration after tool drift, preserving project source bytes."""
import argparse
import json
import os
from pathlib import Path
import re

from . import hvac_project,modules
from .cli import digest
from .module_contract import read_json

SCOPE='Tool-change replay preparation only; original project sources preserved, no old review acceptance transferred or engineering approval established'


def method_path(path):
    return any(path.is_relative_to(hvac_project.ROOT/folder) and path.suffix==suffix
        for folder,suffix in [('src/bsa','.py'),('scripts','.py'),('contracts','.json')])


def inspect(configuration):
    configuration=hvac_project.local(configuration);data=read_json(configuration)
    if set(data)!=hvac_project.KEYS or data['schema']!='bsa.hvac_project':raise ValueError('Exact HVAC configuration required')
    def resolve(value):
        if not isinstance(value,str) or not value.strip() or Path(value).is_absolute():raise ValueError('Relative selected-workspace configuration reference required')
        return hvac_project.local(configuration.parent/value)
    if not isinstance(data['files'],dict) or 'plan' not in data['files'] or set(data['files'])-set(hvac_project.FILES):raise ValueError('Supported explicit project files required')
    files={key:resolve(value) for key,value in data['files'].items()}
    if not isinstance(data['selectors'],dict) or set(data['selectors'])!=set(hvac_project.SELECTORS):raise ValueError('Exact original review selectors required')
    expected=data['input_hashes']
    if not isinstance(expected,dict) or not expected or any(not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha) for sha in expected.values()):raise ValueError('Original complete source hashes required')
    pins={resolve(name):sha for name,sha in expected.items()}
    if len(pins)!=len(expected) or configuration in pins or any(path not in pins for path in files.values()):raise ValueError('Distinct pinned project files required')
    changed=[];missing=[];project_changes=[]
    for path,sha in pins.items():
        actual=digest(path) if path.is_file() else None
        if actual==sha:continue
        row=dict(path=str(path),before=sha,after=actual)
        if not method_path(path):project_changes.append(row)
        elif actual is None:missing.append(row)
        else:changed.append(row)
    current=hvac_project.method_inputs()
    added=sorted(str(p) for p in current if p not in pins)
    source_pins={str(p):sha for p,sha in pins.items() if not method_path(p)}
    return dict(configuration=str(configuration),configuration_sha256=digest(configuration),
        files={key:str(path) for key,path in files.items()},selectors=data['selectors'],source_inputs=source_pins,
        tool_drift=dict(changed=changed,removed=missing,added=added),project_changes=project_changes,
        source_unchanged=not project_changes,design_accepted=False,scope=SCOPE)


def run(configuration,target,out):
    configuration,target,out=[hvac_project.local(p) for p in (configuration,target,out)]
    if target.exists() or out.exists() or target==configuration or target.is_relative_to(out) or out.is_relative_to(target):raise ValueError('Fresh separate configuration and refresh output required')
    original=inspect(configuration)
    if original['project_changes']:raise ValueError('Project data changed; source review is required before a new configuration')
    files={key:Path(path) for key,path in original['files'].items()}
    protected=[configuration,*files.values(),*(Path(p) for p in original['source_inputs'])]
    if any(out==p or out in p.parents or target==p for p in protected):raise ValueError('Refresh outputs must preserve all original sources')
    if 'requirements_result' in files:
        previous=files['requirements_result'].parent
        if out.is_relative_to(previous) or previous.is_relative_to(out) or target.is_relative_to(previous):raise ValueError('Refresh outputs must stay outside the original requirements run')
    methods={str(p):digest(p) for p in hvac_project.method_inputs()}
    pins={**original['source_inputs'],str(configuration):original['configuration_sha256'],**methods}
    out.mkdir(parents=True)
    result=dict(schema='bsa.hvac-project-refresh/1',original=original,target_configuration=str(target),inputs=pins,
        status='failed',stages={},stage_errors={},design_accepted=False,scope=SCOPE)
    stage='requirements'
    try:
        request=dict(schema='bsa.module-request/1',project_id=out.name,scenario_id='tool-change-replay',capability='requirements.source-inventory',
            coordinate_frame=dict(id='requirements-no-geometry-claim',kind='source-world-si',length_unit='m',georeferenced=False),
            sources=dict(plan=dict(path=os.path.relpath(files['plan'],out),sha256=digest(files['plan']))))
        path=out/'requirements-request.json';path.write_text(json.dumps(request,indent=2),encoding='utf-8')
        inventory=modules.run(path,'bsa.source-requirements',out/'requirements')
        result['stages']['requirements']=inventory['execution']['status']
        if inventory['execution']['status']!='completed':result['status']='requirements_unavailable'
        else:
            if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Source or tool changed during refresh')
            stage='configuration'
            options={key:value for key,value in files.items() if key not in ('plan','requirements_result')}
            hvac_project.create(files['plan'],target,requirements_result=out/'requirements/result.json',**options,**original['selectors'])
            result['stages']['configuration']='created_fresh';result['target_sha256']=digest(target);result['status']='prepared'
    except (ValueError,OSError,KeyError,ImportError) as exc:result['stage_errors'][stage]=type(exc).__name__+': '+str(exc)
    result['source_and_tools_unchanged']=all(Path(p).is_file() and digest(Path(p))==sha for p,sha in pins.items()) and methods=={str(p):digest(p) for p in hvac_project.method_inputs()}
    if not result['source_and_tools_unchanged']:result['status']='source_changed'
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'refresh.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(out):
    out=hvac_project.local(out);result=read_json(out/'refresh.json')
    if result.get('schema')!='bsa.hvac-project-refresh/1' or result.get('status')!='prepared' or result.get('scope')!=SCOPE or result.get('design_accepted') is not False or result.get('source_and_tools_unchanged') is not True:raise ValueError('Complete unaccepted refresh preparation required')
    if not result.get('inputs') or any(not hvac_project.local(p).is_file() or digest(Path(p))!=sha for p,sha in result['inputs'].items()):raise ValueError('Refresh source or method changed')
    original=inspect(result['original']['configuration'])
    if original!=result['original'] or original['project_changes']:raise ValueError('Original configuration/source drift differs')
    methods={str(p):digest(p) for p in hvac_project.method_inputs()}
    required={**original['source_inputs'],original['configuration']:original['configuration_sha256'],**methods}
    if result['inputs']!=required:raise ValueError('Refresh source/method inventory differs')
    if result.get('artifacts')!={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file() and p!=out/'refresh.json'}:raise ValueError('Refresh artifacts changed')
    target=hvac_project.local(result['target_configuration'])
    if digest(target)!=result.get('target_sha256'):raise ValueError('Fresh configuration changed')
    files,selectors,_=hvac_project.load(target)
    expected={key:Path(path) for key,path in original['files'].items()};expected['requirements_result']=out/'requirements/result.json'
    if files!=expected or selectors!=original['selectors']:raise ValueError('Refresh replaced original project inputs or review selectors')
    if result.get('stages')!=dict(requirements='completed',configuration='created_fresh') or result.get('stage_errors'):raise ValueError('Refresh stages incomplete')
    inventory=modules.verify_result(out/'requirements/result.json')['payload']
    return dict(integrity_pass=True,project_sources_unchanged=True,original_configuration_preserved=True,
        requirements=len(inventory['requirements']),unresolved_inputs=len(inventory['unresolved_inputs']),
        configuration=str(target),engineering_executed=False,design_accepted=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    check=commands.add_parser('inspect');check.add_argument('configuration')
    prepare=commands.add_parser('prepare');prepare.add_argument('configuration');prepare.add_argument('--target',required=True);prepare.add_argument('--out',required=True)
    audit=commands.add_parser('verify');audit.add_argument('folder')
    args=parser.parse_args()
    if args.command=='inspect':result=inspect(args.configuration)
    elif args.command=='verify':result=verify(args.folder)
    else:result=run(args.configuration,args.target,args.out)
    print(json.dumps(result,indent=2));return 0 if result.get('integrity_pass') or result.get('status')=='prepared' else 2


if __name__=='__main__':raise SystemExit(main())
