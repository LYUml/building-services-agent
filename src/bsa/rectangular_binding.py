"""Source-bound rectangular straight duct chains, saved IFC verification and pressure analysis."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network_binding import _prepare,_reconcile


def inspect_saved(ifc,source,derived,binding):
    from .bim import validate
    validate(source)
    used={name for chain in binding['segments'].values() for name in chain}
    import ifcopenshell
    import ifcopenshell.geom
    from .rectangular_geometry import verify,specification
    from . import rectangular_elbow
    import numpy as np
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system
    from .circular_geometry import configure
    saved=ifcopenshell.open(str(ifc));settings=ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
    for device in source['devices']:
        if device['id'] not in used:continue
        matches=[obj for obj in saved.by_type(device['ifc_class']) if obj.Name==device['id']]
        if len(matches)!=1:raise ProjectError('unique saved rectangular duct required')
        obj=matches[0];module=rectangular_elbow if device.get('body_shape')==rectangular_elbow.WALL else None
        (module.verify if module else verify)(obj,device,ifcopenshell.geom.create_shape(settings,obj))
        spec=(module.specification if module else specification)(device);ports={p.Name:p for p in system.get_ports(obj)}
        if set(ports)!={p['id'] for p in device['ports']}:raise ProjectError('saved rectangular source port set differs')
        for port in device['ports']:
            frame=placement.get_local_placement(ports[port['id']].ObjectPlacement)
            if not np.allclose(frame[:3,3],np.array(device['origin_m'])+port['offset_m'],atol=1e-8,rtol=0) or not np.allclose(frame[:3,2],spec['normals'][port['id']],atol=1e-8,rtol=0):raise ProjectError('saved rectangular port position/normal differs')
    all_ducts=saved.by_type('IfcDuctSegment')+saved.by_type('IfcDuctFitting')
    if {o.Name for o in all_ducts}!=used or len(all_ducts)!=len(used):raise ProjectError('exact saved rectangular duct coverage required')
    _reconcile(ifc,derived,binding,source,rectangular=True)
    return True


def run(project,model,binding,out):
    from .bim import run as author
    from .rectangular_network import run as analyse
    paths=[Path(p).resolve() for p in (project,model,binding)];out=Path(out).resolve()
    if out.exists() or any(out==p or out in p.parents for p in paths):raise ProjectError('new separate output required')
    before={str(p):digest(p) for p in paths}
    data=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
    derived,evidence=_prepare(*data,rectangular=True)
    used={name for row in data[2]['segments'].values() for name in row}
    ducts={d['id'] for d in data[1]['devices'] if d['ifc_class'] in ('IfcDuctSegment','IfcDuctFitting')}
    if used!=ducts:raise ProjectError('exact rectangular duct route coverage required')
    out.mkdir(parents=True)
    native=author(paths[1],out/'bim')
    if not native['model_checks_pass'] or any(not d.get('rectangular_checks') for d in native['devices'] if d['id'] in used):raise ProjectError('saved rectangular native wall verification required')
    generated=out/'network-input.json';generated.write_text(json.dumps(derived,indent=2),encoding='utf-8')
    inspect_saved(out/'bim/model.ifc',data[1],generated,data[2])
    calculation=analyse(generated,out/'analysis')
    if any(digest(Path(p))!=sha for p,sha in before.items()):raise ProjectError('rectangular binding inputs changed')
    result=dict(inputs=before,inputs_unchanged=True,segments=evidence,saved_ifc_geometry_match=True,
        calculated_checks_pass=calculation['calculated_checks_pass'],design_accepted=False,regulatory_compliance='not_established',
        scope='Source-bound hollow rectangular straight/90-degree bend chains with source-defined excess K and prescribed level-air pressure; no junction physics, fabrication or full acceptance')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'network-binding.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    for name in ('model','binding','out'):parser.add_argument('--'+name,type=Path,required=True)
    r=run(**vars(parser.parse_args()));print(json.dumps({k:r[k] for k in ('saved_ifc_geometry_match','calculated_checks_pass','design_accepted')}))
    raise SystemExit(0 if r['calculated_checks_pass'] else 2)


def verified_study(project,model,binding,ifc,analysis):
    """Rebuild source geometry and inspect saved native walls before trusting a study."""
    import copy
    import math
    from .rectangular_network import calculate
    from .engine import ProjectError
    from .cli import digest
    p,m,b,study=[json.loads(Path(path).read_text(encoding="utf-8-sig")) for path in (project,model,binding,analysis)]
    skeleton=copy.deepcopy(p)
    for node in skeleton['nodes']:node.pop('elevation_m')
    for segment in skeleton['segments']:
        for key in ('width_m','height_m','length_m'):segment.pop(key)
    from .rectangular_elbow import WALL as RECTANGULAR_BEND
    devices={d['id']:d for d in m['devices']}
    for segment in skeleton['segments']:
        if any(devices[name].get('body_shape')==RECTANGULAR_BEND for name in b['segments'][segment['id']]):segment.pop('minor_k',None)
    rederived,_=_prepare(skeleton,m,b,rectangular=True)
    if rederived!=p:raise ProjectError('fan network differs from native source geometry derivation')
    inspect_saved(ifc,m,project,b)
    fresh=calculate(p)
    if fresh['calculated_checks_pass'] is not True or study.get('calculated_checks_pass') is not True or study.get('input_sha256')!=digest(Path(project)):raise ProjectError('passing matching rectangular study required')
    for key in ('supply_flow_m3_s','required_source_total_pressure_pa'):
        actual=study.get(key)
        if type(actual) not in (int,float) or not math.isfinite(actual) or not math.isclose(actual,fresh[key],rel_tol=1e-10,abs_tol=1e-10):raise ProjectError('saved rectangular study differs from fresh analysis')
    return fresh
