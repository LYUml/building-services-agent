"""Bind saved IFC space solids to explicit annual thermal boxes, without area metadata."""
import argparse
from collections import Counter
import copy
import itertools
import json
import math
from pathlib import Path
import shutil
from .cli import digest
from .engine import ProjectError
from .annual_energy import MULTIZONE_MODEL,validate


def validate_contract(project,binding):
    if not isinstance(binding,dict) or set(binding) not in ({'source','spaces','north_axis_deg'},{'source','spaces','north_axis_deg','hvac_devices'}) or not isinstance(binding['source'],str) or not binding['source'].strip():
        raise ProjectError('explicit sourced thermal IFC binding required')
    north=binding['north_axis_deg']
    if type(north) not in (int,float) or not math.isfinite(north) or not 0<=north<360:raise ProjectError('explicit EnergyPlus north axis 0..<360 degrees required')
    rows=binding['spaces']
    if not isinstance(rows,list) or not 1<=len(rows)<=100:raise ProjectError('one to 100 space mappings required')
    guids=set();ids=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'guid','id','source'} or any(not isinstance(row[k],str) or not row[k].strip() for k in row):raise ProjectError('space GUID, thermal ID and source required')
        if row['guid'] in guids or row['id'].upper() in ids:raise ProjectError('duplicate thermal mapping identity')
        guids.add(row['guid']);ids.add(row['id'].upper())
    if not isinstance(project,dict) or project.get('model')!=MULTIZONE_MODEL or not isinstance(project.get('building'),dict) or any(k in project['building'] for k in ('spaces','zone_width_m','zone_depth_m','height_m','north_axis_deg')):
        raise ProjectError('thermal template must omit geometry; saved IFC supplies it')
    # Validate non-geometric settings with an explicitly temporary validation fixture.
    candidate=copy.deepcopy(project)
    candidate['building']['north_axis_deg']=north
    candidate['building']['spaces']=[dict(id=r['id'],source=r['source'],origin_m=[i*2,0,0],size_m=[1,1,1]) for i,r in enumerate(rows)]
    validate(candidate)
    from .hvac_devices import validate as validate_devices
    validate_devices(project,binding)
    return binding


def extract(path,binding):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.unit as unit
    import numpy as np
    path=Path(path);before=digest(path);model=ifcopenshell.open(str(path))
    projects=model.by_type('IfcProject')
    if len(projects)!=1 or not projects[0].UnitsInContext or len([u for u in projects[0].UnitsInContext.Units if getattr(u,'UnitType',None)=='LENGTHUNIT'])!=1:
        raise ProjectError('one IFC project and explicit length unit required')
    factor=unit.calculate_unit_scale(model)
    base=next(u for u in projects[0].UnitsInContext.Units if getattr(u,'UnitType',None)=='LENGTHUNIT')
    seen=set()
    while base.is_a('IfcConversionBasedUnit'):
        if base.id() in seen:raise ProjectError('cyclic IFC length unit')
        seen.add(base.id());base=base.ConversionFactor.UnitComponent
    if not base.is_a('IfcSIUnit') or base.Name!='METRE':raise ProjectError('IFC length unit must resolve to metres')
    if not math.isfinite(factor) or factor<=0:raise ProjectError('known positive IFC length unit required')
    roots=[r.GlobalId for r in model.by_type('IfcRoot')]
    if len(roots)!=len(set(roots)):raise ProjectError('duplicate IFC GUID')
    spaces={s.GlobalId:s for s in model.by_type('IfcSpace')}
    if set(spaces)!={r['guid'] for r in binding['spaces']}:raise ProjectError('thermal mapping must cover every saved IFC space exactly')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    rows=[];evidence=[]
    for row in binding['spaces']:
        obj=spaces[row['guid']]
        bodies=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body'] if obj.Representation else []
        if len(bodies)!=1:raise ProjectError('one explicit IFC space Body required')
        try:shape=ifcopenshell.geom.create_shape(settings,obj)
        except Exception as exc:raise ProjectError('IFC space geometry could not be evaluated') from exc
        vertices=np.asarray(shape.geometry.verts,dtype=float).reshape(-1,3)
        faces=np.asarray(shape.geometry.faces,dtype=int).reshape(-1,3)
        if not len(vertices) or not len(faces) or not np.isfinite(vertices).all():raise ProjectError('finite closed space mesh required')
        lo=vertices.min(axis=0);hi=vertices.max(axis=0);size=hi-lo;tol=1e-7
        if np.any(size<.001):raise ProjectError('positive thermal space solid required')
        # Every vertex must be a box corner, and every triangle must occupy one
        # boundary plane. Bounds alone cannot establish a rectangular solid.
        corners=[]
        for v in vertices:
            if not np.all(np.minimum(abs(v-lo),abs(v-hi))<=tol):raise ProjectError('only actual axis-aligned box spaces supported')
            corners.append(tuple(int(abs(v[k]-hi[k])<=tol) for k in range(3)))
        if set(corners)!=set(itertools.product((0,1),repeat=3)):raise ProjectError('complete box corners required')
        edges=Counter();areas=Counter();volume=0
        for f in faces:
            points=vertices[f]-lo;keys=[corners[i] for i in f]
            if len(set(keys))!=3:raise ProjectError('degenerate space triangle')
            planes=[(axis,side) for axis in range(3) for side in (0,1) if all(k[axis]==side for k in keys)]
            if len(planes)!=1:raise ProjectError('space mesh contains non-boundary triangles')
            area=float(np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0]))/2)
            areas[planes[0]]+=area
            volume+=float(np.dot(points[0],np.cross(points[1],points[2]))/6)
            for a,b in zip(keys,keys[1:]+keys[:1]):edges[(a,b)]+=1
        if any(count!=1 or edges[(b,a)]!=1 for (a,b),count in list(edges.items())):raise ProjectError('space mesh is not closed with consistent winding')
        if any(not math.isclose(areas[(axis,side)],float(np.prod(np.delete(size,axis))),rel_tol=1e-8,abs_tol=1e-7) for axis in range(3) for side in (0,1)) or not math.isclose(abs(volume),float(np.prod(size)),rel_tol=1e-8,abs_tol=1e-7):
            raise ProjectError('space solid face area/volume differs from box')
        rows.append(dict(id=row['id'],source=row['source']+'; saved IFC '+row['guid']+' SHA256 '+before,origin_m=lo.tolist(),size_m=size.tolist()))
        evidence.append(dict(guid=row['guid'],thermal_id=row['id'],saved_name=obj.Name,origin_m=lo.tolist(),size_m=size.tolist(),floor_area_m2=float(size[0]*size[1]),volume_m3=abs(volume),triangles=len(faces)))
    if digest(path)!=before:raise ProjectError('IFC source changed during thermal extraction')
    return rows,dict(ifc_sha256=before,length_unit_scale_to_m=factor,geometry_coordinates='IfcOpenShell world-coordinate SI metres',spaces=evidence,complete_space_coverage=True)


def run(project,binding,ifc,weather,out,exe):
    from .annual_energy import run as run_annual
    project,binding,ifc,weather,out=[Path(v).resolve() for v in (project,binding,ifc,weather,out)]
    inputs={str(p):digest(p) for p in (project,binding,ifc,weather)}
    if any(out==p or out in p.parents for p in (project,binding,ifc,weather)):raise ProjectError('separate thermal output required')
    p=json.loads(project.read_text(encoding='utf-8-sig'));b=json.loads(binding.read_text(encoding='utf-8-sig'));validate_contract(p,b)
    rows,audit=extract(ifc,b);p['building']['spaces']=rows;p['building']['north_axis_deg']=b['north_axis_deg'];validate(p)
    audit.update(north_axis_deg=b['north_axis_deg'],orientation_source=b['source'],orientation_scope='explicit EnergyPlus Building North Axis; not inferred from IFC TrueNorth/georeferencing')
    device_audit=None
    if 'hvac_devices' in b:
        from .hvac_devices import bind
        device_audit=bind(ifc,p,b,audit)
        validate(p)
    out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(ifc,out/'model.ifc')
    (out/'bound-project.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
    (out/'geometry-binding.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    annual=run_annual(out/'bound-project.json',weather,out/'annual',exe)
    if any(digest(Path(path))!=sha for path,sha in inputs.items()) or digest(out/'model.ifc')!=audit['ifc_sha256']:raise ProjectError('thermal binding source changed')
    derived=None
    if device_audit:
        from .hvac_devices import append_results
        derived=append_results(out/'model.ifc',out/'analysis.ifc',annual,out/'annual/annual.json',device_audit)
    else:shutil.copyfile(out/'model.ifc',out/'analysis.ifc')
    result=dict(inputs=inputs,inputs_unchanged=True,geometry=audit,calculated_checks_pass=annual['calculated_checks_pass'],design_accepted=False,pending=['actual thermal boundary/material/gain/weather applicability','detailed HVAC/plant and engineering acceptance'])
    if device_audit:result.update(hvac_device_binding=device_audit,annotated_ifc=derived)
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'thermal-binding.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    for key in ('binding','ifc','weather','out','energyplus'):parser.add_argument('--'+key,required=True,type=Path)
    a=parser.parse_args();r=run(a.project,a.binding,a.ifc,a.weather,a.out,a.energyplus)
    print(json.dumps(r,indent=2));return 0 if r['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
