"""Thin compatibility boundary between existing workflow plans and public modules."""
from pathlib import Path
from . import module_contract
from .cli import digest
from .modules import ROOT,method_paths
from .providers import get_provider


def host_selection(tasks,overrides=None,disabled=()):
    """Validate trusted host choices separately from source plan task data."""
    known={t['id']:t for t in tasks if t['kind']=='module_exchange'}
    overrides={} if overrides is None else overrides
    if not isinstance(overrides,dict) or set(overrides)-set(known):raise ValueError('Module overrides must name existing module tasks')
    if not isinstance(disabled,(list,tuple)) or any(not isinstance(p,str) for p in disabled) or len(set(disabled))!=len(disabled):raise ValueError('Unique disabled provider IDs required')
    for provider in [*overrides.values(),*disabled]:get_provider(provider)
    return dict(schema='bsa.workflow-module-selection/1',providers=dict(overrides),disabled_providers=sorted(disabled))


def selection_inputs(tasks,root,selection):
    if not isinstance(selection,dict) or set(selection)!={'schema','providers','disabled_providers'} or selection['schema']!='bsa.workflow-module-selection/1':raise ValueError('Supported exact module host selection required')
    expected=host_selection(tasks,selection['providers'],selection['disabled_providers'])
    if selection!=expected:raise ValueError('Noncanonical module host selection')
    paths=set()
    for task in tasks:
        if task['kind']=='module_exchange':
            paths.update(inputs(Path(root)/task['request'],selection['providers'].get(task['id'],task['provider'])))
    return paths


def verify_selection(tasks,run,selection):
    """Bind selected provider and disabled state to actual retained module results."""
    from .modules import verify_result
    for task in tasks:
        if task['kind']!='module_exchange':continue
        path=Path(run)/task['id']/'result.json'
        if not path.is_file():continue
        result=verify_result(path);provider=selection['providers'].get(task['id'],task['provider'])
        if result['provider']['id']!=provider:raise ValueError('Executed module provider differs from host selection')
        disabled=provider in selection['disabled_providers']
        recorded=any(d['code']=='provider_disabled' for d in result['execution']['diagnostics'])
        if disabled!=recorded:raise ValueError('Executed module disable state differs from host selection')


def inputs(request_path,provider_id):
    request_path=Path(request_path).resolve()
    if not request_path.is_relative_to(ROOT):raise ValueError('Module requests must remain in repository')
    request=module_contract.validate(module_contract.read_json(request_path),'bsa.module-request/1')
    provider=get_provider(provider_id);provider.validate_request(request)
    paths={request_path,Path(__file__),*method_paths(provider)}
    for row in request['sources'].values():
        if Path(row['path']).is_absolute():raise ValueError('Relative module sources required')
        path=(request_path.parent/row['path']).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or digest(path)!=row['sha256']:raise ValueError('Module source missing or changed')
        paths.add(path)
    return paths
