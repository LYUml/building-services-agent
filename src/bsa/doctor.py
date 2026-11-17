"""Read-only direct-dependency and host-path diagnostics; not engineering validation."""
import importlib.metadata as metadata
from pathlib import Path
import re
import sys
import tomllib
from . import workspace


def check(*,extras=(),autocad=None):
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
    ready=sys.version_info>=(3,11) and all(p['matches'] for p in packages) and (runtime is None or runtime['is_file'])
    return dict(status='direct_requirements_ready' if ready else 'needs_setup',
                python=sys.executable,python_supported=sys.version_info>=(3,11),extras=extras,
                project_root=str(selected or workspace.ROOT/'runs'),packages=packages,autocad=runtime,
                scope='Direct pinned distributions and optional host executable presence only; no native import, runtime execution, MCP connection or engineering acceptance',
                design_accepted=False)
