"""Install an append-only, project-scoped local MCP startup configuration."""
import argparse
import json
from pathlib import Path
import sys
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


def install(python,autocad=None,pdftoppm=None):
    project,config=settings(python,autocad,pdftoppm);target=(project/'.codex/config.toml').resolve()
    if not target.is_relative_to(project):raise ValueError('Local config path escapes selected workspace')
    original=target.read_bytes() if target.exists() else b''
    data=tomllib.loads(original.decode('utf-8'));existing=data.get('mcp_servers',{}).get(SERVER)
    if existing is not None:
        if existing!=config:raise ValueError('Existing local BSA config differs; preserve it for explicit reconciliation')
        return dict(configured=True,changed=False,config_path=str(target),config_sha256=digest(target),project_root=str(project))
    suffix=render(config).encode('utf-8');payload=original+(b'\n\n' if original else b'')+suffix
    parsed=tomllib.loads(payload.decode('utf-8'))
    if parsed['mcp_servers'][SERVER]!=config:raise ValueError('Rendered startup config differs')
    # Preserve every unrelated setting byte. Do not alter global config, trust,
    # credentials, policy, model settings or user application processes.
    target.parent.mkdir(parents=True,exist_ok=True)
    if (target.read_bytes() if target.exists() else b'')!=original:raise ValueError('Local config changed during setup')
    if target.exists():
        backup=target.with_name('config.before-building-services.toml')
        with backup.open('xb') as stream:stream.write(original)
        target.write_bytes(payload)
    else:
        with target.open('xb') as stream:stream.write(payload)
    return dict(configured=True,changed=True,config_path=str(target),config_sha256=digest(target),project_root=str(project))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--python',default=sys.executable);p.add_argument('--autocad');p.add_argument('--pdftoppm');a=p.parse_args();print(json.dumps(install(a.python,a.autocad,a.pdftoppm),indent=2))
