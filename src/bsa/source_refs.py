"""Hash-bound host-workspace references shared by data and knowledge adapters."""
import hashlib
from pathlib import Path, PurePosixPath
from .workspace import ROOT, allowed, project_root


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def reference(path):
    path = Path(path).resolve()
    if not allowed(path) or not path.is_file():
        raise ValueError('Existing source in the selected workspace required')
    project = project_root()
    if project is not None and path.is_relative_to(project):
        return dict(workspace='project', path=path.relative_to(project).as_posix(), sha256=file_hash(path))
    return dict(workspace='tool', path=path.relative_to(ROOT).as_posix(), sha256=file_hash(path))


def resolve_reference(row):
    if not isinstance(row, dict) or set(row) != {'workspace', 'path', 'sha256'}:
        raise ValueError('Exact source reference required')
    name = row['path']
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or PurePosixPath(name).is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Normalized workspace-relative source reference required')
    root = ROOT if row['workspace'] == 'tool' else project_root() if row['workspace'] == 'project' else None
    if root is None:
        raise ValueError('Selected source workspace is unavailable')
    path = (root/name).resolve()
    if not path.is_relative_to(root) or not allowed(path) or not path.is_file() or file_hash(path) != row['sha256']:
        raise ValueError('Source missing, changed or outside workspace')
    return path
