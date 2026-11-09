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
    from .rectangular_geometry import verify
    from .circular_geometry import configure
    saved=ifcopenshell.open(str(ifc));settings=ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
    for device in source['devices']:
        if device['id'] not in used:continue
        matches=[obj for obj in saved.by_type('IfcDuctSegment') if obj.Name==device['id']]
        if len(matches)!=1:raise ProjectError('unique saved rectangular duct required')
        obj=matches[0];verify(obj,device,ifcopenshell.geom.create_shape(settings,obj))
    if {o.Name for o in saved.by_type('IfcDuctSegment')}!=used or len(saved.by_type('IfcDuctSegment'))!=len(used):raise ProjectError('exact saved rectangular duct coverage required')
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
    ducts={d['id'] for d in data[1]['devices'] if d['ifc_class']=='IfcDuctSegment'}
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
        scope='Source-bound axis-aligned hollow rectangular straight chains and prescribed level-air pressure budget; no finite bends, junction physics, fabrication or full acceptance')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'network-binding.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    for name in ('model','binding','out'):parser.add_argument('--'+name,type=Path,required=True)
    r=run(**vars(parser.parse_args()));print(json.dumps({k:r[k] for k in ('saved_ifc_geometry_match','calculated_checks_pass','design_accepted')}))
    raise SystemExit(0 if r['calculated_checks_pass'] else 2)
