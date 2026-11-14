"""Shared native obstacle-box append engine, preserving saved source entities."""
import hashlib
import json
import math
from pathlib import Path
import uuid
from .cli import digest
from .engine import ProjectError
from .three_phase import ROOT
from .workspace import allowed


def append(ifc,rows,inputs,out,*,prefix,pset_name,metadata,body_context_id=None):
    import ifcopenshell
    import ifcopenshell.api as api
    import ifcopenshell.geom
    import ifcopenshell.util.unit
    import ifcopenshell.validate
    import numpy as np
    from .box_geometry import box_mesh
    ifc,out=Path(ifc).resolve(),Path(out).resolve()
    paths={ifc,*(Path(p).resolve() for p in inputs)}
    if not allowed(out) or out.exists() or any(out==p or out in p.parents for p in paths):raise ProjectError('new separate host-selected workspace obstacle output required')
    before={str(p):digest(p) for p in paths}
    model=ifcopenshell.open(str(ifc))
    if model.schema!='IFC4' or not math.isclose(ifcopenshell.util.unit.calculate_unit_scale(model),1,abs_tol=1e-12):raise ProjectError('explicit metre IFC4 required')
    projects=model.by_type('IfcProject');storeys=model.by_type('IfcBuildingStorey')
    bodies=[c for c in model.by_type('IfcGeometricRepresentationSubContext') if c.ContextIdentifier=='Body' and c.ContextType=='Model']
    if body_context_id is not None:
        if type(body_context_id) is not int:raise ProjectError('explicit integer body context ID required')
        bodies=[c for c in bodies if c.id()==body_context_id]
    if len(projects)!=1 or len(storeys)!=1 or len(bodies)!=1:raise ProjectError('one project/storey/model body context required')
    original={e.id():hashlib.sha256(str(e).encode()).hexdigest() for e in model}
    namespace=uuid.UUID(hex=ifcopenshell.guid.expand(projects[0].GlobalId))
    for row in rows:
        name=prefix+row['id']
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
        pset=api.run('pset.add_pset',model,product=obj,name=pset_name)
        api.run('pset.edit_pset',model,pset=pset,properties={'InputID':row['id'],'Source':row['source'],**metadata,**row.get('properties',{})})
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
    report=dict(inputs=before,inputs_unchanged=True,original_entities_unchanged=True,original_entity_count=len(original),obstacles=rows,body_context_id=bodies[0].id(),
                saved_ifc_sha256=digest(target),calculated_checks_pass=True,design_accepted=False,
                scope='explicit source-linked closed IFC obstacle boxes; original entities preserved',
                pending=['source obstacle applicability/completeness','route-to-obstacle clearance/clash','BIM viewer and full engineering acceptance'])
    (out/'obstacles.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
