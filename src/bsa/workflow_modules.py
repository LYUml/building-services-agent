"""Thin compatibility boundary between existing workflow plans and public modules."""
from pathlib import Path
import json
import os
from . import module_contract
from .cli import digest
from .modules import ROOT,method_paths
from .providers import get_provider

RULE_PROVIDERS={'module_electrical_rules':'bsa.electrical-path-rules','module_water_rules':'bsa.hvac-water-rules'}

def selected_rule_provider(task,selection):
    provider=selection['providers'].get(task['id'],task.get('provider'))
    if provider is not None and provider!=RULE_PROVIDERS.get(task['kind']):raise ValueError('Compatible registered rule provider required for '+task['id'])
    return provider


def host_selection(tasks,overrides=None,disabled=()):
    """Validate trusted host choices separately from source plan task data."""
    known={t['id']:t for t in tasks if t['kind'] in ('module_exchange','module_authoring','module_analysis',*RULE_PROVIDERS)}
    overrides={} if overrides is None else overrides
    if not isinstance(overrides,dict) or set(overrides)-set(known):raise ValueError('Module overrides must name existing module tasks')
    if not isinstance(disabled,(list,tuple)) or any(not isinstance(p,str) for p in disabled) or len(set(disabled))!=len(disabled):raise ValueError('Unique disabled provider IDs required')
    for provider in [*overrides.values(),*disabled]:get_provider(provider)
    for task in known.values():
        if task['kind'] in RULE_PROVIDERS:selected_rule_provider(task,dict(providers=overrides))
    return dict(schema='bsa.workflow-module-selection/1',providers=dict(overrides),disabled_providers=sorted(disabled))


def execution_status(result,kind):
    status={'completed':'pass','failed':'fail','unavailable':'pending','pending':'pending'}[result['execution']['status']]
    if kind=='module_analysis' and result['execution']['status']=='completed':
        if result['payload_schema'] not in ('bsa.electrical-circuits/1','bsa.air-budget/1','bsa.bound-air-budget/1','bsa.water-graph/1','bsa.bound-water-graph/1'):raise ValueError('Supported numerical analysis payload required')
        status=result['payload']['status']
    return status


def selection_inputs(tasks,root,selection):
    if not isinstance(selection,dict) or set(selection)!={'schema','providers','disabled_providers'} or selection['schema']!='bsa.workflow-module-selection/1':raise ValueError('Supported exact module host selection required')
    expected=host_selection(tasks,selection['providers'],selection['disabled_providers'])
    if selection!=expected:raise ValueError('Noncanonical module host selection')
    paths=set()
    for task in tasks:
        if task['kind'] in ('module_exchange','module_authoring','module_analysis'):
            paths.update(inputs(Path(root)/task['request'],selection['providers'].get(task['id'],task['provider']),inherited=bool(task.get('depends_on'))))
        elif task['kind'] in RULE_PROVIDERS:
            provider=selected_rule_provider(task,selection)
            if provider:paths.update(method_paths(get_provider(provider)))
    return paths


def result_path(run,task):
    return Path(run)/task['id']/('exchange/result.json' if task.get('depends_on') else 'result.json')


def authored_model(run,producer):
    """Resolve a verified common artifact rather than guessing a provider filename."""
    from .modules import verify_result
    path=result_path(run,producer);result=verify_result(path)
    if result['execution']['status']!='completed' or result['payload_schema']!='bsa.model-artifact/1' or result['payload'] is None or result['payload']['model']['format']!='IFC4':raise ValueError('Verified completed IFC4 model artifact required')
    return (path.parent/result['payload']['model']['path']).resolve(),result['payload']['coordinate_frame']


def bound_air_context(path):
    """Expose hash-linked domain files for existing consumers without filename guesses."""
    from .modules import verify_result
    path=Path(path).resolve();result=verify_result(path)
    if result['execution']['status']!='completed' or result['payload_schema']!='bsa.bound-air-budget/1' or result['payload']['status']!='pass':raise ValueError('Passing saved-native air budget required')
    payload=result['payload']
    if 'network_input' not in payload:raise ValueError('Explicit derived network input artifact required for downstream fan analysis')
    request_path=Path(result['request']['path']);request=module_contract.read_json(request_path)
    files={k:(request_path.parent/request['sources'][k]['path']).resolve() for k in ('model','binding')}
    files.update(project=path.parent/payload['network_input']['path'],ifc=path.parent/payload['model']['path'],analysis=path.parent/payload['report']['path'])
    return files,result


def inherited_request(task,tasks,root,run):
    from .workflow import IFC_ARTIFACTS
    request_path=(Path(root)/task['request']).resolve()
    request=module_contract.read_json(request_path)
    inputs(request_path,task['provider'],inherited=True)
    producer=next(t for t in tasks if t['id']==task['depends_on'])
    if producer['kind']=='module_authoring':
        model,frame=authored_model(run,producer)
        if frame!=request['coordinate_frame']:raise ValueError('Authoring and spatial source frames differ')
    else:model=(Path(run)/producer['id']/IFC_ARTIFACTS[producer['kind']]).resolve()
    destination=(Path(run)/task['id']/'request.json').resolve()
    if task['kind']=='module_analysis' and request['capability']=='analysis.water.ifc-steady-graph':
        sources={k:(request_path.parent/r['path']).resolve() for k,r in request['sources'].items()}
        sources['ifc']=model
        request['sources']={k:dict(path=os.path.relpath(path,destination.parent),sha256=digest(path)) for k,path in sources.items()}
        return destination,request
    if task['kind']=='module_analysis':
        from .modules import verify_result
        authored=verify_result(result_path(run,producer));source_request_path=Path(authored['request']['path']);source_request=module_contract.read_json(source_request_path)
        if authored['capability']!='authoring.ifc.bim':raise ValueError('Canonical BIM project source required')
        model_source=(source_request_path.parent/source_request['sources']['project']['path']).resolve()
        sources={k:(request_path.parent/r['path']).resolve() for k,r in request['sources'].items()}
        sources.update(ifc=model,model=model_source)
        request['sources']={k:dict(path=os.path.relpath(path,destination.parent),sha256=digest(path)) for k,path in sources.items()}
        return destination,request
    binding=(request_path.parent/request['sources']['binding']['path']).resolve()
    request['sources']={'ifc':dict(path=os.path.relpath(model,destination.parent),sha256=digest(model)),
        'binding':dict(path=os.path.relpath(binding,destination.parent),sha256=digest(binding))}
    return destination,request


def materialize(task,tasks,root,run):
    destination,request=inherited_request(task,tasks,root,run)
    destination.parent.mkdir(parents=True,exist_ok=False)
    destination.write_text(json.dumps(request,indent=2),encoding='utf-8')
    return destination


def verify_selection(tasks,run,selection,root=None,report_tasks=None):
    """Bind selected provider and disabled state to actual retained module results."""
    from .modules import verify_result
    for task in tasks:
        if task['kind'] not in ('module_exchange','module_authoring','module_analysis'):continue
        path=result_path(run,task)
        if not path.is_file():continue
        if task.get('depends_on'):
            if root is None:raise ValueError('Source plan directory required for inherited module verification')
            destination,expected=inherited_request(task,tasks,root,run)
            if module_contract.read_json(destination)!=expected:raise ValueError('Materialized module request differs from saved producer')
        result=verify_result(path);provider=selection['providers'].get(task['id'],task['provider'])
        if report_tasks is not None and report_tasks[task['id']]['status']!=execution_status(result,task['kind']):raise ValueError('Workflow task status contradicts retained module result')
        if result['provider']['id']!=provider:raise ValueError('Executed module provider differs from host selection')
        disabled=provider in selection['disabled_providers']
        recorded=any(d['code']=='provider_disabled' for d in result['execution']['diagnostics'])
        if disabled!=recorded:raise ValueError('Executed module disable state differs from host selection')


def inputs(request_path,provider_id,*,inherited=False):
    request_path=Path(request_path).resolve()
    if not request_path.is_relative_to(ROOT):raise ValueError('Module requests must remain in repository')
    request=module_contract.validate(module_contract.read_json(request_path),'bsa.module-request/1')
    provider=get_provider(provider_id)
    if inherited:
        expected={'project','binding'} if request['capability'] in ('analysis.air.rectangular-ifc-tree','analysis.water.ifc-steady-graph') else {'binding'}
        if request['capability']!=provider.CAPABILITY or set(request['sources'])!=expected:raise ValueError('Inherited module template has wrong source roles;replacement IFC forbidden')
    else:provider.validate_request(request)
    paths={request_path,Path(__file__),*method_paths(provider)}
    for row in request['sources'].values():
        if Path(row['path']).is_absolute():raise ValueError('Relative module sources required')
        path=(request_path.parent/row['path']).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or digest(path)!=row['sha256']:raise ValueError('Module source missing or changed')
        paths.add(path)
    return paths
