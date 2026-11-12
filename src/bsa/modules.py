"""Run versioned module requests through trusted,replaceable provider boundaries."""
import argparse
import json
from pathlib import Path
from .cli import digest
from . import module_contract
from .providers import get_provider
from .workspace import allowed

ROOT=Path(__file__).resolve().parents[2]


def method_paths(provider):
    schemas=[ROOT/'contracts/modules'/module_contract.SCHEMAS[id] for id in ('bsa.module-request/1','bsa.module-result/1',provider.PAYLOAD)]
    return [Path(__file__),Path(module_contract.__file__),ROOT/'src/bsa/workspace.py',Path(provider.__file__),ROOT/'src/bsa/providers/__init__.py',*schemas]


def run(request_path,provider_id,out,*,runtime=None,disabled=False):
    request_path,out=Path(request_path).resolve(),Path(out).resolve()
    if not allowed(request_path) or not allowed(out):raise ValueError('Request and output must be in the tool repository or explicit host project workspace')
    request_sha=digest(request_path);request=module_contract.validate(module_contract.read_json(request_path),'bsa.module-request/1')
    provider=get_provider(provider_id);provider.validate_request(request)
    pins={str(request_path):request_sha};paths={}
    for role,row in request['sources'].items():
        if Path(row['path']).is_absolute():raise ValueError('Relative repository-local source paths required')
        p=(request_path.parent/row['path']).resolve()
        if not allowed(p) or not p.is_file() or digest(p)!=row['sha256']:raise ValueError('Module source missing or changed')
        pins[str(p)]=row['sha256'];paths[role]=p
    for p in method_paths(provider):pins[str(p.resolve())]=digest(p)
    runtime=runtime or {}
    protected=[Path(p) for p in pins]+[Path(p).resolve() for p in runtime.values() if p is not None]
    if out.exists() or any(out==p or out in p.parents for p in protected):raise ValueError('New module output separate from all sources/runtimes required')
    out.mkdir(parents=True)
    if disabled:execution=dict(status='unavailable',diagnostics=[dict(code='provider_disabled',message='Selected provider is disabled by host configuration')],payload=None,pins={})
    else:execution=provider.execute(request,paths,runtime,out)
    for name,sha in execution['pins'].items():
        if name in pins and pins[name]!=sha:raise ValueError('Conflicting module source snapshots')
        pins[name]=sha
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Module source or provider changed during execution')
    result=dict(schema='bsa.module-result/1',request=dict(path=str(request_path),sha256=request_sha),project_id=request['project_id'],scenario_id=request['scenario_id'],capability=request['capability'],provider=provider.DESCRIPTION,
        execution=dict(status=execution['status'],diagnostics=execution['diagnostics']),acceptance=dict(status='pending',scope=getattr(provider,'ACCEPTANCE_SCOPE','Scoped spatial exchange only;thermal,airflow,MEP,regulatory and full design acceptance remain separate')),
        inputs=pins,artifacts={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()},payload_schema=provider.PAYLOAD,payload=execution['payload'],design_accepted=False)
    try:
        module_contract.validate(result,'bsa.module-result/1')
        if result['payload'] is not None and result['payload']['coordinate_frame']!=request['coordinate_frame']:raise ValueError('Provider changed the common coordinate frame')
    except ValueError as exc:
        if result['execution']['status']!='completed':raise
        result['execution']=dict(status='failed',diagnostics=[dict(code='payload_contract_invalid',message=str(exc))]);result['payload']=None
        module_contract.validate(result,'bsa.module-result/1')
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Module inputs changed during result validation')
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify_result(path):
    path=Path(path).resolve();result=module_contract.validate(module_contract.read_json(path),'bsa.module-result/1')
    for name,sha in result['inputs'].items():
        p=Path(name).resolve()
        if not allowed(p) or digest(p)!=sha:raise ValueError('Module input evidence changed')
    for name,sha in result['artifacts'].items():
        p=(path.parent/name).resolve()
        if not p.is_relative_to(path.parent) or digest(p)!=sha:raise ValueError('Module artifact evidence changed')
    source=Path(result['request']['path']).resolve()
    if result['inputs'].get(str(source))!=result['request']['sha256']:raise ValueError('Module request identity differs')
    request=module_contract.validate(module_contract.read_json(source),'bsa.module-request/1')
    provider=get_provider(result['provider']['id']);provider.validate_request(request)
    for row in request['sources'].values():
        p=(source.parent/row['path']).resolve()
        if result['inputs'].get(str(p))!=row['sha256']:raise ValueError('Module omitted a declared request source')
    for p in method_paths(provider):
        if result['inputs'].get(str(p.resolve()))!=digest(p):raise ValueError('Module omitted current method/schema evidence')
    actual={p.relative_to(path.parent).as_posix() for p in path.parent.rglob('*') if p.is_file() and p!=path}
    if actual!=set(result['artifacts']):raise ValueError('Module artifact inventory differs')
    if any(result[k]!=request[k] for k in ('project_id','scenario_id','capability')):raise ValueError('Module request/result correspondence differs')
    if result['provider']!=provider.DESCRIPTION:raise ValueError('Module provider identity differs')
    if result['payload'] is not None and result['payload']['coordinate_frame']!=request['coordinate_frame']:raise ValueError('Module frame correspondence differs')
    if hasattr(provider,'verify_evidence'):provider.verify_evidence(result,path)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('request');p.add_argument('--provider',required=True);p.add_argument('--out',required=True)
    p.add_argument('--upstream');p.add_argument('--deps');p.add_argument('--sources');p.add_argument('--disable-provider',action='store_true');a=p.parse_args()
    result=run(a.request,a.provider,a.out,runtime=dict(upstream=a.upstream,deps=a.deps,sources=a.sources),disabled=a.disable_provider)
    print(result['execution']['status']+';engineering acceptance pending')
    raise SystemExit(0 if result['execution']['status']=='completed' else 2)
