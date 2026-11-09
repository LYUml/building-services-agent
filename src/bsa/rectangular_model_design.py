"""Finite rectangular sizing followed by fixed-centreline native model regeneration."""
import argparse
import copy
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .bim import validate,run as author
from .rectangular_geometry import specification
from .network_binding import _prepare
from .rectangular_design import validate_catalogue,run as design
from .rectangular_binding import run as coordinate
from .network_model_design import verify_identities

BASIS='rectangular walls; fixed centrelines and endpoints'


def resize(model,binding,choices,catalogue,geometry):
    import numpy as np
    result=copy.deepcopy(model);options={r['id']:r for r in catalogue['options']}
    devices={d['id']:d for d in result['devices']}
    for segment,choice in choices.items():
        option=options[choice];wall=geometry['options'][choice]
        for name in binding['segments'][segment]:
            d=devices[name];spec=specification(d)
            points={p['id']:np.array(d['origin_m'])+p['offset_m'] for p in d['ports']}
            size=list(d['size_m']);origin=list(d['origin_m'])
            for local,inner in enumerate((option['width_m'],option['height_m'])):
                world=int(np.argmax(abs(spec['matrix'][:3,local])))
                size[world]=inner+2*wall['wall_thickness_m']
                origin[world]=float(spec['matrix'][world,3]-size[world]/2)
            d['size_m']=size;d['origin_m']=origin
            for port in d['ports']:port['offset_m']=(points[port['id']]-origin).tolist()
            key='rectangular-revision/'+name
            if key in result['sources']:raise ProjectError('rectangular revision source namespace collision')
            result['sources'][key]=model['sources'][d['source']]+'; dimensions: '+catalogue['sources'][option['source']]+'; wall: '+geometry['sources'][wall['source']]
            d['source']=key;d['properties'].update(InternalWidth_m=option['width_m'],InternalHeight_m=option['height_m'],WallThickness_m=wall['wall_thickness_m'])
    validate(result)
    return result


def run(project,model,binding,catalogue,geometry,out):
    paths=[Path(p).resolve() for p in (project,model,binding,catalogue,geometry)];out=Path(out).resolve()
    if out.exists() or any(out==p or out in p.parents for p in paths):raise ProjectError('new separate rectangular model-design output required')
    before={str(p):digest(p) for p in paths};n,m,b,c,g=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
    if not m.get('project_uuid'):raise ProjectError('stable project namespace required for rectangular revision')
    baseline,_=_prepare(n,m,b,rectangular=True);options,_,_=validate_catalogue(baseline,c)
    if not isinstance(g,dict) or set(g)!={'basis','sources','options'} or g['basis']!=BASIS or not isinstance(g['sources'],dict) or not g['sources']:raise ProjectError('explicit sourced rectangular wall geometry contract required')
    if any(not isinstance(v,str) or not v.strip() for v in g['sources'].values()) or not isinstance(g['options'],dict) or set(g['options'])!=set(options):raise ProjectError('exact sourced wall option coverage required')
    for row in g['options'].values():
        if not isinstance(row,dict) or set(row)!={'wall_thickness_m','source'} or row['source'] not in g['sources']:raise ProjectError('known wall source required')
        t=row['wall_thickness_m']
        if type(t) not in (int,float) or not math.isfinite(t) or t<=0:raise ProjectError('positive finite wall thickness required')
    filtered=copy.deepcopy(c);rejected=[]
    for segment,allowed in c['allowed_options'].items():
        kept=[]
        for choice in allowed:
            try:resize(m,b,{segment:choice},c,g);kept.append(choice)
            except ProjectError as exc:rejected.append(dict(segment=segment,option=choice,reason=str(exc)))
        filtered['allowed_options'][segment]=kept
    out.mkdir(parents=True);author(paths[1],out/'baseline-bim')
    baseline_path=out/'baseline-network.json';baseline_path.write_text(json.dumps(baseline,indent=2),encoding='utf-8')
    catalogue_path=out/'filtered-catalogue.json';catalogue_path.write_text(json.dumps(filtered,indent=2),encoding='utf-8')
    result=dict(inputs=before,rejected_geometry_options=rejected,calculated_checks_pass=False,stable_object_port_ids_match=False,
        fixed_endpoints_pass=False,selected=None,design_accepted=False,scope='Finite rectangular sizing and source-defined straight-wall regeneration only; no physical junction, clash, fabrication, fan or full code acceptance')
    if all(filtered['allowed_options'].values()):
        sizing=design(baseline_path,catalogue_path,out/'sizing')
        if sizing['selected']:
            revised=resize(m,b,sizing['selected']['choices'],c,g)
            revised_path=out/'selected-model.json';revised_path.write_text(json.dumps(revised,indent=2),encoding='utf-8')
            skeleton=json.loads((out/'sizing/selected-network.json').read_text())
            for node in skeleton['nodes']:node.pop('elevation_m')
            for segment in skeleton['segments']:
                for key in ('width_m','height_m','length_m'):segment.pop(key)
            skeleton_path=out/'selected-skeleton.json';skeleton_path.write_text(json.dumps(skeleton,indent=2),encoding='utf-8')
            checked=coordinate(skeleton_path,revised_path,paths[2],out/'selected-coordination')
            verify_identities(out/'baseline-bim/model.ifc',out/'selected-coordination/bim/model.ifc')
            import ifcopenshell
            import ifcopenshell.util.placement as placement
            import ifcopenshell.util.system as system
            saved=ifcopenshell.open(str(out/'selected-coordination/bim/model.ifc'))
            for device in m['devices']:
                obj=next(x for x in saved.by_type(device['ifc_class']) if x.Name==device['id'])
                ports={p.Name:p for p in system.get_ports(obj)}
                for port in device.get('ports',[]):
                    actual=placement.get_local_placement(ports[port['id']].ObjectPlacement)[:3,3]
                    expected=[a+b for a,b in zip(device['origin_m'],port['offset_m'])]
                    if math.dist(actual,expected)>1e-8:raise ProjectError('rectangular revision moved original endpoint')
            pressure=json.loads((out/'selected-coordination/analysis/network.json').read_text())['required_source_total_pressure_pa']
            if not math.isclose(pressure,sizing['selected']['required_source_total_pressure_pa'],rel_tol=1e-9,abs_tol=1e-8):raise ProjectError('selected native-bound pressure differs from sizing')
            result.update(selected=sizing['selected'],calculated_checks_pass=checked['calculated_checks_pass'],stable_object_port_ids_match=True,fixed_endpoints_pass=True)
    if any(digest(Path(p))!=sha for p,sha in before.items()):raise ProjectError('rectangular model-design sources changed')
    result['inputs_unchanged']=True;result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'model-design.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    for name in ('model','binding','catalogue','geometry','out'):parser.add_argument('--'+name,type=Path,required=True)
    r=run(**vars(parser.parse_args()));print(json.dumps({k:r[k] for k in ('calculated_checks_pass','selected','fixed_endpoints_pass','design_accepted')}))
    raise SystemExit(0 if r['calculated_checks_pass'] else 2)
