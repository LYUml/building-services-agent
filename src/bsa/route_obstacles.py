"""Append explicitly sourced routing obstacles to a separate saved IFC copy."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import uuid

from .cli import digest
from .engine import ProjectError
from .route_search import search


def contract(routing,heights):
    search(routing)  # Validate planar source contract; no search result is trusted as BIM evidence.
    rows=routing['obstacles']
    if not isinstance(heights,dict) or set(heights)!={r['id'] for r in rows}:
        raise ProjectError('exact obstacle height/source coverage required')
    result=[]
    for row in rows:
        z=heights[row['id']]
        if not isinstance(z,dict) or not isinstance(z.get('source'),str) or not z['source'].strip():raise ProjectError('obstacle height provenance required')
        lo,hi=z.get('min_z_m'),z.get('max_z_m')
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (lo,hi)) or hi-lo<.001:
            raise ProjectError('finite positive obstacle height required')
        result.append(dict(id=row['id'],origin_m=[*row['min_m'],lo],size_m=[row['max_m'][i]-row['min_m'][i] for i in (0,1)]+[hi-lo],source=row['source']+'; height: '+z['source']))
    if not result:raise ProjectError('nonempty obstacle inventory required')
    return result


def run(ifc,routing,heights,out):
    import ifcopenshell
    import ifcopenshell.api as api
    import ifcopenshell.geom
    import ifcopenshell.util.unit
    import ifcopenshell.validate
    import numpy as np
    from .box_geometry import box_mesh
    paths=[Path(p).resolve() for p in (ifc,routing,heights)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain sources')
    before={str(p):digest(p) for p in paths}
    rows=contract(*(json.loads(p.read_text(encoding='utf-8-sig')) for p in paths[1:]))
    model=ifcopenshell.open(str(paths[0]))
    if model.schema!='IFC4' or not math.isclose(ifcopenshell.util.unit.calculate_unit_scale(model),1,abs_tol=1e-12):raise ProjectError('explicit metre IFC4 required')
    projects=model.by_type('IfcProject');storeys=model.by_type('IfcBuildingStorey')
    bodies=[c for c in model.by_type('IfcGeometricRepresentationSubContext') if c.ContextIdentifier=='Body' and c.ContextType=='Model']
    if len(projects)!=1 or len(storeys)!=1 or len(bodies)!=1:raise ProjectError('one project/storey/model body context required')
    original={e.id():hashlib.sha256(str(e).encode()).hexdigest() for e in model}
    namespace=uuid.UUID(hex=ifcopenshell.guid.expand(projects[0].GlobalId))
    for row in rows:
        name='ROUTING_OBSTACLE_'+row['id']
        guid=ifcopenshell.guid.compress(uuid.uuid5(namespace,name).hex)
        if any(e.GlobalId==guid or e.Name==name for e in model.by_type('IfcRoot')):raise ProjectError('obstacle identity already exists')
        obj=api.run('root.create_entity',model,ifc_class='IfcBuildingElementProxy',name=name);obj.GlobalId=guid
        w,d,h=row['size_m'];vertices=[(0.,0.,0.),(w,0.,0.),(w,d,0.),(0.,d,0.),(0.,0.,h),(w,0.,h),(w,d,h),(0.,d,h)]
        faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        rep=api.run('geometry.add_mesh_representation',model,context=bodies[0],vertices=[vertices],faces=[faces])
        api.run('geometry.assign_representation',model,product=obj,representation=rep)
        matrix=np.eye(4);matrix[:3,3]=row['origin_m']
        api.run('geometry.edit_object_placement',model,product=obj,matrix=matrix,is_si=True)
        # Add a new relationship instead of editing any source containment row.
        model.create_entity('IfcRelContainedInSpatialStructure',GlobalId=ifcopenshell.guid.new(),RelatedElements=[obj],RelatingStructure=storeys[0])
        pset=api.run('pset.add_pset',model,product=obj,name='BSA_RoutingObstacle')
        api.run('pset.edit_pset',model,pset=pset,properties={'InputID':row['id'],'Source':row['source'],'RoutingInputSHA256':before[str(paths[1])],'HeightInputSHA256':before[str(paths[2])]})
        row['guid']=guid
    out.mkdir(parents=True,exist_ok=False);target=out/'model.ifc';model.write(str(target))
    saved=ifcopenshell.open(str(target))
    if any(hashlib.sha256(str(saved.by_id(i)).encode()).hexdigest()!=h for i,h in original.items()):raise ProjectError('original IFC entities changed')
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(saved,logger,express_rules=True)
    if logger.statements:raise ProjectError('obstacle IFC schema verification failed')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    for row in rows:
        shape=ifcopenshell.geom.create_shape(settings,saved.by_guid(row['guid']))
        vertices=np.array(shape.geometry.verts).reshape(-1,3);faces=np.array(shape.geometry.faces).reshape(-1,3)
        lo,size,volume=box_mesh(vertices,faces)
        if not np.allclose(lo,row['origin_m'],atol=1e-8,rtol=0) or not np.allclose(size,row['size_m'],atol=1e-8,rtol=0):raise ProjectError('saved obstacle differs from source bounds')
        row['saved_volume_m3']=volume
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('obstacle source changed')
    report=dict(inputs=before,inputs_unchanged=True,original_entities_unchanged=True,original_entity_count=len(original),obstacles=rows,
                saved_ifc_sha256=digest(target),calculated_checks_pass=True,design_accepted=False,
                scope='explicit rectangular routing footprint plus sourced height to saved closed IFC box; source entities preserved',
                pending=['source obstacle applicability/completeness','route-to-obstacle clearance/clash','BIM viewer and full engineering acceptance'])
    (out/'obstacles.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('ifc',type=Path)
    for key in ('routing','heights','out'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(run(args.ifc,args.routing,args.heights,args.out),indent=2))


if __name__=='__main__':main()
