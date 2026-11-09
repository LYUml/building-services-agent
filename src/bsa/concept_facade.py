"""Source-bound native IFC facade concept; explicit thicknesses, actual voids, no product ratings."""
import argparse
import json
import math
from pathlib import Path
import uuid
import numpy as np
from .cli import digest
from .engine import ProjectError
from .concept_layout import geometry_handoff,validate_settings as layout_settings


def settings(row):
    if not isinstance(row,dict) or set(row)!={'source','wall_thickness_m','window_envelope_thickness_m'} or not isinstance(row['source'],str) or not row['source'].strip():raise ProjectError('explicit sourced facade thickness decisions required')
    for key in ('wall_thickness_m','window_envelope_thickness_m'):
        if type(row[key]) not in (float,int) or not math.isfinite(row[key]) or not .001<=row[key]<=1:raise ProjectError('bounded positive facade thickness required')
    if row['window_envelope_thickness_m']>row['wall_thickness_m']:raise ProjectError('window envelope must fit within wall thickness')
    return row


def specs(handoff,source,basis):
    from .thermal_windows import FACES
    spaces={r['id']:r for r in source['spaces']}
    for w in handoff['draft_window_rectangles']:
        row=spaces[w['zone']];axis,sign,h=FACES[w['face']]
        n=np.eye(3)[axis]*sign;x=np.cross(n,[0,0,1]);origin=np.array(row['origin_m'],dtype=float)
        origin[axis]+=row['size_m'][axis] if sign>0 else 0
        if x[h]<0:origin[h]+=row['size_m'][h]
        matrix=np.eye(4);matrix[:3,0]=x;matrix[:3,1]=n;matrix[:3,2]=[0,0,1];matrix[:3,3]=origin
        yield w,row,matrix,row['size_m'][h],row['size_m'][2]


def inspect(model,source,handoff,basis):
    import ifcopenshell.geom
    import ifcopenshell.util.element as element
    from .circular_geometry import configure,verify_closed_wall
    from .box_geometry import box_mesh
    from .concept_spaces import inspect_spaces
    inspect_spaces(model,source)
    count=len(handoff['draft_window_rectangles'])
    if any(len(model.by_type(c))!=count for c in ('IfcWall','IfcWindow','IfcOpeningElement','IfcRelVoidsElement','IfcRelFillsElement')):raise ProjectError('exact facade object/relation coverage required')
    geom=ifcopenshell.geom.settings();geom.set(geom.USE_WORLD_COORDS,True);configure(geom)
    namespace=uuid.UUID(source['project_uuid']);records=[]
    for w,row,matrix,length,height in specs(handoff,source,basis):
        objects=[]
        for cls in ('IfcWall','IfcOpeningElement','IfcWindow'):
            name=cls+'_'+w['id'];found=[o for o in model.by_type(cls) if o.Name==name]
            if len(found)!=1:raise ProjectError('unique facade identity required')
            obj=found[0];expected=__import__('ifcopenshell').guid.compress(uuid.uuid5(namespace,name).hex)
            if obj.GlobalId!=expected:raise ProjectError('facade stable identity differs')
            p=element.get_psets(obj).get('BSA_ConceptFacade',{})
            if p.get('Source')!=basis['source'] or p.get('InputID')!=w['id'] or p.get('Scope')!='Unapproved geometry envelope; no product or thermal rating':raise ProjectError('facade source metadata differs')
            objects.append(obj)
        wall,opening,window=objects
        if len(opening.VoidsElements)!=1 or opening.VoidsElements[0].RelatingBuildingElement!=wall or len(window.FillsVoids)!=1 or window.FillsVoids[0].RelatingOpeningElement!=opening:raise ProjectError('facade void/filling host differs')
        for obj in (wall,window):
            if len(obj.ContainedInStructure)!=1 or obj.ContainedInStructure[0].RelatingStructure.Name!=row['storey']:raise ProjectError('facade storey differs')
        t=basis['wall_thickness_m'];g=basis['window_envelope_thickness_m'];expected_volume=(length*height-w['width_m']*w['height_m'])*t
        shape=ifcopenshell.geom.create_shape(geom,wall);v=np.array(shape.geometry.verts).reshape(-1,3);f=np.array(shape.geometry.faces).reshape(-1,3)
        volume,relative,euler=verify_closed_wall(v,f,expected_volume)
        # Native world vertices must lie on the exact outer/inner wall and reveal planes.
        local=(v-matrix[:3,3])@matrix[:3,:3]
        for dim,bounds in enumerate(((0,length),(0,t),(0,height))):
            if not math.isclose(local[:,dim].min(),bounds[0],abs_tol=1e-7) or not math.isclose(local[:,dim].max(),bounds[1],abs_tol=1e-7):raise ProjectError('saved facade wall bounds differ')
        corners=np.array([[x,y,z] for x,z in ((0,0),(length,0),(length,height),(0,height),(w['offset_m'],w['sill_m']),(w['offset_m']+w['width_m'],w['sill_m']),(w['offset_m']+w['width_m'],w['sill_m']+w['height_m']),(w['offset_m'],w['sill_m']+w['height_m'])) for y in (0,t)])
        if len(local)!=16 or not all(any(np.allclose(v,c,atol=1e-7,rtol=0) for v in local) for c in corners):raise ProjectError('native wall opening corners differ')
        for obj,depth,offset in ((opening,t+.02,-.01),(window,g,(t-g)/2)):
            shape=ifcopenshell.geom.create_shape(geom,obj);verts=np.array(shape.geometry.verts).reshape(-1,3);faces=np.array(shape.geometry.faces).reshape(-1,3)
            lo,size,mass=box_mesh((verts-matrix[:3,3])@matrix[:3,:3],faces)
            if not np.allclose(lo,[w['offset_m'],offset,w['sill_m']],atol=1e-7,rtol=0) or not np.allclose(size,[w['width_m'],depth,w['height_m']],atol=1e-7,rtol=0):raise ProjectError('saved facade opening/window placement differs')
        if not math.isclose(window.OverallWidth,w['width_m']) or not math.isclose(window.OverallHeight,w['height_m']):raise ProjectError('saved window dimensions differ')
        records.append(dict(id=w['id'],wall_guid=wall.GlobalId,window_guid=window.GlobalId,opening_guid=opening.GlobalId,wall_volume_m3=volume,through_opening_euler=euler,opening_area_m2=w['width_m']*w['height_m']))
    return records


def run(ifc,project,layout,basis,out):
    import ifcopenshell
    import ifcopenshell.api as api
    import ifcopenshell.validate
    ifc,project,layout,basis,out=map(Path,(ifc,project,layout,basis,out))
    pins={str(p.resolve()):digest(p) for p in (ifc,project,layout,basis)}
    source=json.loads(project.read_text(encoding='utf-8-sig'));l=layout_settings(json.loads(layout.read_text(encoding='utf-8-sig')));b=settings(json.loads(basis.read_text(encoding='utf-8-sig')))
    h=geometry_handoff(ifc,source,l['window_wall_ratio']);model=ifcopenshell.open(str(ifc));original={o.id():o.to_string() for o in model}
    if any(model.by_type(c) for c in ('IfcWall','IfcWindow','IfcOpeningElement')):raise ProjectError('unmodified concept source required')
    context=next(c for c in model.by_type('IfcGeometricRepresentationSubContext') if c.ContextIdentifier=='Body')
    ns=uuid.UUID(source['project_uuid'])
    def create(cls,w,matrix,length,height,thickness):
        name=cls+'_'+w['id'];o=api.run('root.create_entity',model,ifc_class=cls,name=name);o.GlobalId=ifcopenshell.guid.compress(uuid.uuid5(ns,name).hex)
        rep=api.run('geometry.add_wall_representation',model,context=context,length=length,height=height,thickness=thickness)
        api.run('geometry.assign_representation',model,product=o,representation=rep)
        api.run('geometry.edit_object_placement',model,product=o,matrix=matrix)
        ps=api.run('pset.add_pset',model,product=o,name='BSA_ConceptFacade')
        api.run('pset.edit_pset',model,pset=ps,properties=dict(Source=b['source'],InputID=w['id'],Scope='Unapproved geometry envelope; no product or thermal rating'))
        return o
    for w,row,m,length,height in specs(h,source,b):
        wall=create('IfcWall',w,m,length,height,b['wall_thickness_m'])
        om=m.copy();om[:3,3]+=(m[:3,:3]@np.array([w['offset_m'],-.01,w['sill_m']]))
        opening=create('IfcOpeningElement',w,om,w['width_m'],w['height_m'],b['wall_thickness_m']+.02)
        api.run('feature.add_feature',model,feature=opening,element=wall)
        wm=m.copy();wm[:3,3]+=(m[:3,:3]@np.array([w['offset_m'],(b['wall_thickness_m']-b['window_envelope_thickness_m'])/2,w['sill_m']]))
        window=create('IfcWindow',w,wm,w['width_m'],w['height_m'],b['window_envelope_thickness_m']);window.OverallWidth=w['width_m'];window.OverallHeight=w['height_m']
        api.run('feature.add_filling',model,opening=opening,element=window)
        storey=next(o for o in model.by_type('IfcBuildingStorey') if o.Name==row['storey'])
        api.run('spatial.assign_container',model,products=[wall,window],relating_structure=storey)
    out.mkdir(parents=True,exist_ok=False);target=out/'facade.ifc';model.write(str(target));saved=ifcopenshell.open(str(target))
    if any(saved.by_id(i).to_string()!=value for i,value in original.items()):raise ProjectError('original IFC records changed')
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(saved,logger,express_rules=True)
    if logger.statements:raise ProjectError('facade IFC schema validation failed: '+str(logger.statements[:1]))
    records=inspect(saved,source,h,b)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ProjectError('facade source changed')
    result=dict(inputs=pins,ifc_sha256=digest(target),records=records,original_records_preserved=True,native_geometry_checks_pass=True,design_accepted=False,thermal_model_ready=False,pending=['corner joints, slabs/roof, partitions and architectural completeness','real frame/glazing/product/material properties','site shading and performance simulation','native CAD drawings and full engineering acceptance'])
    (out/'facade.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('ifc','project','layout','basis','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.ifc,a.project,a.layout,a.basis,a.out)))
