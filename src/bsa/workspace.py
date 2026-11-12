"""Host-selected project data workspace, separate from the installed tool source."""
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def project_root():
    value=os.environ.get('BSA_PROJECT_ROOT')
    if not value:return None
    path=Path(value)
    if not path.is_absolute():raise ValueError('BSA_PROJECT_ROOT must be an absolute host path')
    path=path.resolve()
    if not path.is_dir() or path==Path(path.anchor):raise ValueError('Existing non-volume-root project directory required')
    return path


def allowed(path):
    path=Path(path).resolve();project=project_root()
    return path.is_relative_to(ROOT) or (project is not None and path.is_relative_to(project))


def intake_output(path):
    path=Path(path).resolve();project=project_root()
    return path.is_relative_to(ROOT/'runs') or (project is not None and path.is_relative_to(project))
