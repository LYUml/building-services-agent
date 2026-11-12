"""Resolve exact verified terminal envelope or logical-inlet IFC producer artifacts."""
from pathlib import Path
from .cli import digest
from .workspace import allowed
from . import spatial_terminal_ifc as author,spatial_terminal_inlets as inlets


def resolve(source):
    source=Path(source).resolve()
    if not allowed(source):raise ValueError('Selected terminal producer required')
    before=digest(source)
    if source.name=='terminal-ifc.json':
        report=author.verify(source.parent);target=source.parent/'Terminal Envelope Study.ifc';pins=dict(report['inputs'])
    elif source.name=='terminal-inlets.json':
        inlet=inlets.verify(source.parent);report=author.verify(Path(inlet['terminal_ifc']).parent);target=source.parent/'Terminal Inlet Study.ifc';pins=dict(inlet['inputs'])
    else:raise ValueError('Exact terminal IFC or inlet producer report required')
    if digest(source)!=before:raise ValueError('Terminal producer changed while resolving')
    pins[str(source)]=before;pins[str(target)]=digest(target);pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    return target,dict(terminals=report['terminals'],inputs=pins,model_path=str(target))
