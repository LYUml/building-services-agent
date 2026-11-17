"""Exact installed-method evidence exceptions; never project workspace access."""
import importlib.metadata
from pathlib import Path
from .cli import digest
from .workspace import allowed


def fluids_method_paths():
    try:
        distribution=importlib.metadata.distribution('fluids')
    except importlib.metadata.PackageNotFoundError:return set()
    if distribution.version!='1.3.1':return set()
    return {Path(distribution.locate_file('fluids/'+name)).resolve() for name in ('core.py','friction.py')}


def inherited_inputs_current(pins):
    trusted=fluids_method_paths()
    return all((allowed(Path(name)) or Path(name).resolve() in trusted) and digest(Path(name))==sha
               for name,sha in pins.items())
