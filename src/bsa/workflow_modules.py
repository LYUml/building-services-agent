"""Thin compatibility boundary between existing workflow plans and public modules."""
from pathlib import Path
from . import module_contract
from .cli import digest
from .modules import ROOT,method_paths
from .providers import get_provider


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
