"""Resolve exact verified envelope,inlet or short-stub IFC producer artifacts."""
from pathlib import Path
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from . import spatial_terminal_ifc as author,spatial_terminal_inlets as inlets,spatial_terminal_stubs as stubs


def verified_base(inlet,pins):
    path=Path(inlet['terminal_ifc']);expected=pins.get(str(path))
    if not allowed(path) or expected is None or digest(path)!=expected:raise ValueError('Verified base terminal inventory changed')
    report=read_json(path)
    if digest(path)!=expected:raise ValueError('Base terminal inventory changed while reading')
    return report


def resolve(source):
    source=Path(source).resolve()
    if not allowed(source):raise ValueError('Selected terminal producer required')
    before=digest(source)
    if source.name=='terminal-ifc.json':
        report=author.verify(source.parent);target=source.parent/'Terminal Envelope Study.ifc';pins=dict(report['inputs']);expected=report['ifc_sha256']
    elif source.name=='terminal-inlets.json':
        inlet=inlets.verify(source.parent);pins=dict(inlet['inputs']);report=verified_base(inlet,pins);target=source.parent/'Terminal Inlet Study.ifc';expected=inlet['ifc_sha256']
    elif source.name=='terminal-stubs.json':
        stub=stubs.verify(source.parent);pins=dict(stub['inputs']);inlet_path=Path(stub['inlets'])
        if digest(inlet_path)!=pins[str(inlet_path)]:raise ValueError('Verified inlet ancestry changed')
        inlet=read_json(inlet_path);report=verified_base(inlet,pins);target=source.parent/'Terminal Stub Study.ifc';expected=stub['ifc_sha256']
    else:raise ValueError('Exact terminal IFC,inlet or stub producer report required')
    if digest(source)!=before or digest(target)!=expected:raise ValueError('Terminal producer/model changed while resolving')
    pins[str(source)]=before;pins[str(target)]=expected;pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    return target,dict(terminals=report['terminals'],inputs=pins,model_path=str(target))
