"""Install or explicitly refresh project-scoped local MCP runtime settings."""
import argparse
import copy
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib
from . import workspace
from .cli import digest

SERVER='building_services'


def settings(python,autocad=None,pdftoppm=None):
    root=workspace.ROOT.resolve();project=workspace.project_root() or root
    project=project.resolve()
    if project==root.parent/'polyu_bse3124':raise ValueError('Completed historical project is read-only')
    data=project if project!=root else root/'runs'
    if not data.is_dir():raise ValueError('Existing host-selected project/test root required')
    python=Path(python).resolve()
    if not python.is_file():raise ValueError('Explicit existing engineering Python required')
    args=['-X','utf8','-m','bsa.mcp_server']
    for name,value in (('autocad',autocad),('pdftoppm',pdftoppm)):
        if value is not None:
            value=Path(value).resolve()
            if not value.is_file():raise ValueError('Explicit existing host runtime required: '+name)
            args.extend(['--'+name,value.as_posix()])
    return project,dict(command=python.as_posix(),args=args,cwd=root.as_posix(),startup_timeout_sec=120,tool_timeout_sec=1200,enabled=True,env=dict(BSA_PROJECT_ROOT=data.as_posix()))


def render(config):
    quote=lambda value:json.dumps(value,ensure_ascii=False)
    lines=['[mcp_servers.'+SERVER+']']
    for key in ('command','args','cwd','startup_timeout_sec','tool_timeout_sec','enabled'):
        value=config[key];lines.append(key+' = '+('true' if value is True else quote(value)))
    lines.extend(['','[mcp_servers.'+SERVER+'.env]','BSA_PROJECT_ROOT = '+quote(config['env']['BSA_PROJECT_ROOT'])])
    return '\n'.join(lines)+'\n'


def refreshed(original,data,config):
    existing=data['mcp_servers'][SERVER];desired=copy.deepcopy(existing)
    args=list(existing.get('args',[]));prefix=['-X','utf8','-m','bsa.mcp_server']
    if args[:4]!=prefix or not all(isinstance(v,str) for v in args):raise ValueError('Only the known BSA module launcher can be refreshed')
    for flag in ('--autocad','--pdftoppm'):
        if flag not in config['args']:continue
        value=config['args'][config['args'].index(flag)+1]
        if args.count(flag)>1 or (flag in args and (args.index(flag)+1>=len(args) or args[args.index(flag)+1].startswith('--'))):raise ValueError('Ambiguous existing runtime arguments')
        if flag in args:args[args.index(flag)+1]=value
        else:args.extend([flag,value])
    desired.update(command=config['command'],cwd=config['cwd'],args=args)
    desired['env']=dict(existing.get('env',{}));desired['env']['BSA_PROJECT_ROOT']=config['env']['BSA_PROJECT_ROOT']
    if desired==existing:return original
    import tomlkit
    if importlib.metadata.version('tomlkit')!='0.15.1':raise ValueError('Pinned tomlkit==0.15.1 required for refresh')
    document=tomlkit.parse(original.decode('utf-8'))
    if tomlkit.dumps(document).encode('utf-8')!=original:raise ValueError('Existing layout cannot be roundtripped unchanged')
    table=document['mcp_servers'][SERVER]
    for key in ('command','cwd','args'):table[key]=desired[key]
    if 'env' not in table:table['env']=tomlkit.table()
    table['env']['BSA_PROJECT_ROOT']=desired['env']['BSA_PROJECT_ROOT']
    payload=tomlkit.dumps(document).encode('utf-8');expected=copy.deepcopy(data);expected['mcp_servers'][SERVER]=desired
    if tomllib.loads(payload.decode('utf-8'))!=expected:raise ValueError('Unmanaged settings changed during refresh')
    return payload


def write_config(target,original,payload):
    target.parent.mkdir(parents=True,exist_ok=True)
    if (target.read_bytes() if target.exists() else b'')!=original:raise ValueError('Local config changed during setup')
    if target.exists():
        backup=target.with_name('config.before-building-services.toml')
        if backup.exists() and backup.read_bytes()!=original:
            import hashlib
            backup=target.with_name('config.before-building-services.'+hashlib.sha256(original).hexdigest()[:16]+'.toml')
        if backup.exists():
            if backup.read_bytes()!=original:raise ValueError('Existing backup differs')
        else:
            with backup.open('xb') as stream:stream.write(original)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.bsa-config-',delete=False) as stream:
            temporary=Path(stream.name);stream.write(payload);stream.flush();os.fsync(stream.fileno())
        if (target.read_bytes() if target.exists() else b'')!=original:raise ValueError('Local config changed before replacement')
        os.replace(temporary,target)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def install(python,autocad=None,pdftoppm=None,refresh=False):
    project,config=settings(python,autocad,pdftoppm);target=(project/'.codex/config.toml').resolve()
    if not target.is_relative_to(project):raise ValueError('Local config path escapes selected workspace')
    original=target.read_bytes() if target.exists() else b''
    data=tomllib.loads(original.decode('utf-8'));existing=data.get('mcp_servers',{}).get(SERVER)
    if existing is not None:
        if refresh:payload=refreshed(original,data,config)
        elif existing!=config:raise ValueError('Existing local BSA config differs; preserve it for explicit reconciliation')
        else:payload=original
        if payload==original:return dict(configured=True,changed=False,config_path=str(target),config_sha256=digest(target),project_root=str(project))
    else:
        suffix=render(config).encode('utf-8');payload=original+(b'\n\n' if original else b'')+suffix
    parsed=tomllib.loads(payload.decode('utf-8'))
    if existing is None and parsed['mcp_servers'][SERVER]!=config:raise ValueError('Rendered startup config differs')
    # Preserve every unrelated setting byte. Do not alter global config, trust,
    # credentials, policy, model settings or user application processes.
    write_config(target,original,payload)
    return dict(configured=True,changed=True,config_path=str(target),config_sha256=digest(target),project_root=str(project))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--python',default=sys.executable);p.add_argument('--autocad');p.add_argument('--pdftoppm');p.add_argument('--refresh',action='store_true');a=p.parse_args();print(json.dumps(install(a.python,a.autocad,a.pdftoppm,refresh=a.refresh),indent=2))
