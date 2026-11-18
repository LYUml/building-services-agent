"""Read-only direct-dependency and host-path diagnostics; not engineering validation."""
import importlib.metadata as metadata
import hashlib
from pathlib import Path
import re
import sys
import tomllib
from . import workspace
from .host_runtime import PATH_ARGUMENTS


def dwg_runtime_paths(dotnet=None, worker=None):
    from .dwg_readback import host_runtime_files

    try:
        dotnet_path, worker_path, reader = host_runtime_files(dotnet, worker)
    except ValueError as error:
        return dict(paths_ready=False, execution_verified=False, problem=str(error))
    return dict(paths_ready=True, execution_verified=False,
                dotnet=str(dotnet_path), worker=str(worker_path), reader=str(reader))


def profile_paths(config):
    """Inspect an explicitly selected BSA startup profile without executing it."""
    config=Path(config).resolve();data=config.read_bytes()
    settings=tomllib.loads(data.decode('utf-8'))
    servers=settings.get('mcp_servers',{})
    server=servers.get('building_services') if isinstance(servers,dict) else None
    if not isinstance(server,dict):raise ValueError('building_services MCP profile required')
    args=server.get('args',[])
    if not isinstance(args,list) or any(not isinstance(a,str) for a in args):raise ValueError('MCP args must be a string list')
    def presence(value,kind):
        if not isinstance(value,str) or not value.strip():raise ValueError('Explicit MCP command/cwd/runtime path required')
        path=Path(value)
        return dict(path=value,kind=kind,absolute=path.is_absolute(),
            present=path.is_absolute() and (path.is_file() if kind=='file' else path.is_dir()),execution_verified=False)
    command=presence(server.get('command'),'file');cwd=presence(server.get('cwd'),'directory')
    runtimes={};index=0
    while index<len(args):
        flag,separator,value=args[index].partition('=');name=flag[2:] if flag.startswith('--') else ''
        if name not in PATH_ARGUMENTS:index+=1;continue
        if flag in runtimes or (not separator and (index+1==len(args) or args[index+1].startswith('--'))):
            raise ValueError('Unique MCP runtime flag with explicit path required: '+flag)
        runtimes[flag]=presence(value if separator else args[index+1],PATH_ARGUMENTS[name]);index+=1 if separator else 2
    environment = server.get('env', {})
    if not isinstance(environment, dict):
        raise ValueError('MCP environment must be a table')
    dwg_keys = ('BSA_ACADSHARP_DOTNET', 'BSA_ACADSHARP_WORKER')
    optional = {}
    if any(key in environment for key in dwg_keys):
        values = [environment.get(key, '') for key in dwg_keys]
        if any(not isinstance(value, str) for value in values):
            raise ValueError('DWG readback environment paths must be strings')
        optional['dwg_readback'] = dwg_runtime_paths(*values)
    if config.read_bytes()!=data:raise ValueError('MCP profile changed during inspection')
    return dict(config_path=str(config),config_sha256=hashlib.sha256(data).hexdigest(),
        command=command,cwd=cwd,runtimes=runtimes,
        paths_ready=(all(item['present'] for item in [command,cwd,*runtimes.values()])
                     and all(item['paths_ready'] for item in optional.values())),
        execution_verified=False,
        scope='Supported absolute BSA startup path presence only; not generic MCP configuration validation or engine execution',
        **optional)


def check(*,extras=(),autocad=None,mcp_config=None,dwg_readback=False):
    project=tomllib.loads((workspace.ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']
    optional=project['optional-dependencies'];extras=sorted(set(extras))
    if set(extras)-set(optional):raise ValueError('Unknown extras: '+', '.join(sorted(set(extras)-set(optional))))
    declarations=list(project['dependencies'])
    for extra in extras:declarations.extend(optional[extra])
    packages=[]
    for requirement in sorted(set(declarations),key=str.casefold):
        match=re.fullmatch(r'([A-Za-z0-9_.-]+)==([^;\s]+)',requirement)
        if not match:raise ValueError('Doctor requires an explicit exact dependency pin: '+requirement)
        name,expected=match.groups()
        try:actual=metadata.version(name)
        except metadata.PackageNotFoundError:actual=None
        packages.append(dict(package=name,expected=expected,installed=actual,matches=actual==expected))
    selected=workspace.project_root();runtime=None
    if autocad is not None:
        path=Path(autocad).resolve();runtime=dict(path=str(path),is_file=path.is_file(),execution_verified=False)
    profile=profile_paths(mcp_config) if mcp_config is not None else None
    ready=sys.version_info>=(3,11) and all(p['matches'] for p in packages) and (runtime is None or runtime['is_file']) and (profile is None or profile['paths_ready'])
    optional_runtime = {}
    if dwg_readback:
        dwg = dwg_runtime_paths()
        optional_runtime['dwg_readback'] = dwg
        ready = ready and dwg['paths_ready']
    return dict(status='direct_requirements_ready' if ready else 'needs_setup',
                python=sys.executable,python_supported=sys.version_info>=(3,11),extras=extras,
                project_root=str(selected or workspace.ROOT/'runs'),packages=packages,autocad=runtime,
                mcp_profile=profile,
                scope='Direct pinned distributions and optional host executable presence only; no native import, runtime execution, MCP connection or engineering acceptance',
                design_accepted=False,**optional_runtime)
