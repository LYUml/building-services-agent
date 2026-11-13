"""Declared equal-section four-port rectangular cross, using existing native engines."""
import argparse
from collections import Counter
import importlib.metadata
import json
import math
from pathlib import Path
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.validate
import ifcopenshell.util.placement as placement
import ifcopenshell.util.element as element
import ifcopenshell.util.system as system
from ifcopenshell.util.shape_builder import ShapeBuilder
import numpy as np
import manifold3d as m
from . import rectangular_tee as tee
from .tee_geometry import stable_guid,placement_matrix
from .solid_clash import from_mesh
from .workspace import allowed
from .cli import digest

KEY='RECTANGULAR-CROSS'
NAMES=('main-a','main-b','branch-a','branch-b')


def validate(data):
    if not isinstance(data,dict) or not isinstance(data.get('port_directions'),dict) or set(data['port_directions'])!=set(NAMES): raise ValueError('Four explicit cross port directions required')
    directions=data['port_directions']
    if any(v not in ('SOURCE','SINK','SOURCEANDSINK') for v in directions.values()) or set(directions.values()) not in ({'SOURCE','SINK'},{'SOURCEANDSINK'}): raise ValueError('Explicit splitting/mixing or all bidirectional cross directions required')
    # Reuse source/placement/dimension guards without interpreting four ports as a tee.
    shadow=dict(data,port_directions=dict(zip(tee.NAMES,['SOURCEANDSINK']*3)))
    return tee.validate(shadow)


def port_frames(data):
    w,h,t,L,B=validate(data); transform=placement_matrix(data); result={}
    for name,point,normal,width in [('main-a',(0,0,-L),(0,0,-1),(1,0,0)),('main-b',(0,0,L),(0,0,1),(1,0,0)),
        ('branch-a',(-B,0,0),(-1,0,0),(0,0,1)),('branch-b',(B,0,0),(1,0,0),(0,0,-1))]:
        frame=np.eye(4); frame[:3,:3]=np.column_stack((width,np.cross(normal,width),normal));frame[:3,3]=point
        result[name]=transform@frame
    return result


def inspect(path,data,component=False):
    w,h,t,L,B=validate(data); transform=placement_matrix(data); model=ifcopenshell.open(str(path))
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(model,logger,express_rules=True)
    if logger.statements:raise ValueError('Cross schema/EXPRESS issues')
    obj=model.by_guid(stable_guid(data,'IfcDuctFitting',KEY))
    if obj.PredefinedType!='JUNCTION' or not np.allclose(placement.get_local_placement(obj.ObjectPlacement),transform,atol=1e-9,rtol=0): raise ValueError('Cross type/placement differs')
    props=element.get_psets(obj).get('BSA_DesignInputs',{})
    if props.get('Source')!=data['source'] or props.get('Classification')!=data['classification']: raise ValueError('Cross source/classification differs')
    reps=obj.Representation.Representations
    if len(reps)!=1 or reps[0].RepresentationType!='CSG' or len(reps[0].Items)!=1: raise ValueError('One cross CSG body required')
    wall=reps[0].Items[0]
    if not wall.is_a('IfcBooleanResult') or wall.Operator!='DIFFERENCE': raise ValueError('Cross outer-minus-inner wall required')
    for union,width,height in [(wall.FirstOperand,w+2*t,h+2*t),(wall.SecondOperand,w,h)]:
        if not union.is_a('IfcBooleanResult') or union.Operator!='UNION': raise ValueError('Two full cross prism union required')
        for solid,depth,origin,axis,reference in [(union.FirstOperand,2*L,(0,0,-L),(0,0,1),(1,0,0)),(union.SecondOperand,2*B,(-B,0,0),(1,0,0),(0,0,-1))]:
            if not solid.is_a('IfcExtrudedAreaSolid') or not solid.SweptArea.is_a('IfcRectangleProfileDef'):raise ValueError('Cross rectangular prism operands required')
            p=solid.SweptArea; frame=np.eye(4);frame[:3,:3]=np.column_stack((reference,np.cross(axis,reference),axis));frame[:3,3]=origin
            if p.Position is not None or not np.allclose([p.XDim,p.YDim,solid.Depth],[width,height,depth],atol=1e-10,rtol=0) or not np.allclose(placement.get_axis2placement(solid.Position),frame,atol=1e-10,rtol=0) or tuple(solid.ExtrudedDirection.DirectionRatios)!=(0.,0.,1.): raise ValueError('Cross literal section/depth/operand placement differs')
    ports=system.get_ports(obj)
    if len(ports)!=4 or {p.Name for p in ports}!=set(NAMES): raise ValueError('Four unique owned cross ports required')
    frames=port_frames(data)
    for p in ports:
        if p.GlobalId!=stable_guid(data,'IfcDistributionPort',KEY,p.Name) or p.FlowDirection!=data['port_directions'][p.Name] or not np.allclose(placement.get_local_placement(p.ObjectPlacement),frames[p.Name],atol=1e-9,rtol=0):raise ValueError('Cross port identity/direction/frame differs')
    if not component and (len(model.by_type('IfcDistributionElement'))!=1 or len(model.by_type('IfcDistributionPort'))!=4 or model.by_type('IfcRelConnectsPorts')): raise ValueError('Exact standalone cross inventory required')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    shape=ifcopenshell.geom.create_shape(settings,obj);v=np.array(shape.geometry.verts).reshape(-1,3);v=(v-transform[:3,3])@transform[:3,:3];f=np.array(shape.geometry.faces).reshape(-1,3)
    solid=from_mesh((v,f));ow,oh=w+2*t,h+2*t
    volume=((2*L+2*B)*ow-ow**2)*oh-((2*L+2*B)*w-w**2)*h
    if len(solid.decompose())!=1 or not math.isclose(solid.volume(),volume,rel_tol=1e-9,abs_tol=1e-10):raise ValueError('Cross connected material/independent prism volume differs')
    edges=Counter(tuple(sorted((int(a),int(b)))) for face in f for a,b in zip(face,[face[1],face[2],face[0]]));euler=len(v)-len(edges)+len(f)
    if any(n!=2 for n in edges.values()) or euler!=-4:raise ValueError('Cross closed four-ended wall topology differs')
    if not np.allclose([v.min(axis=0),v.max(axis=0)],[[-B,-oh/2,-L],[B,oh/2,L]],atol=1e-8,rtol=0):raise ValueError('Cross material bounds differ')
    probes=[m.Manifold.cube((w*.5,h*.5,2*L+.2),center=True),m.Manifold.cube((2*B+.2,h*.5,w*.5),center=True)]
    for probe in probes:
        common=solid^probe
        if common.status()!=m.Error.NoError or abs(common.volume())>1e-12:raise ValueError('Cross centre bore blocked')
    return dict(ports=4,closed_material=True,one_connected_material=True,euler_characteristic=euler,
        native_material_volume_m3=solid.volume(),independent_material_volume_m3=volume,
        source_geometry_and_port_frames=True,open_main_and_branch_bores=True,schema_express_pass=True)


def run(project,out):
    project,out=Path(project).resolve(),Path(out).resolve();data=json.loads(project.read_text());w,h,t,L,B=validate(data)
    if out.exists() or not all(allowed(p) for p in (project,out)) or out==project or out in project.parents:raise ValueError('Fresh selected workspace outside source required')
    versions={n:importlib.metadata.version(n) for n in ('ifcopenshell','manifold3d')}
    if versions!={'ifcopenshell':'0.8.5','manifold3d':'3.5.4'}:raise ValueError('Pinned cross native runtimes required')
    pins={str(project):digest(project)};out.mkdir(parents=True)
    model=api.run('project.create_file',version='IFC4');api.run('root.create_entity',model,ifc_class='IfcProject',name='Declared rectangular four-port cross')
    unit=api.run('unit.add_si_unit',model,unit_type='LENGTHUNIT');api.run('unit.assign_unit',model,units=[unit])
    context=api.run('context.add_context',model,context_type='Model');body=api.run('context.add_context',model,context_type='Model',context_identifier='Body',target_view='MODEL_VIEW',parent=context)
    obj=api.run('root.create_entity',model,ifc_class='IfcDuctFitting',predefined_type='JUNCTION',name=KEY);obj.GlobalId=stable_guid(data,'IfcDuctFitting',KEY)
    builder=ShapeBuilder(model)
    def prism_union(width,height):
        profile=model.create_entity('IfcRectangleProfileDef',ProfileType='AREA',XDim=float(width),YDim=float(height))
        a=builder.extrude(profile,magnitude=2*L,position=(0.,0.,-L))
        b=builder.extrude(profile,magnitude=2*B,position=(-B,0.,0.),position_z_axis=(1.,0.,0.),position_x_axis=(0.,0.,-1.))
        return api.run('geometry.add_boolean',model,first_item=a,second_items=[b],operator='UNION')[-1]
    wall=api.run('geometry.add_boolean',model,first_item=prism_union(w+2*t,h+2*t),second_items=[prism_union(w,h)],operator='DIFFERENCE')[-1]
    api.run('geometry.assign_representation',model,product=obj,representation=builder.get_representation(body,[wall],representation_type='CSG'))
    api.run('geometry.edit_object_placement',model,product=obj,matrix=placement_matrix(data),is_si=True)
    for name,frame in port_frames(data).items():
        p=api.run('system.add_port',model,element=obj);p.Name=name;p.GlobalId=stable_guid(data,'IfcDistributionPort',KEY,name);p.FlowDirection=data['port_directions'][name];p.PredefinedType='DUCT';p.SystemType='VENTILATION'
        api.run('geometry.edit_object_placement',model,product=p,matrix=frame,is_si=True)
    pset=api.run('pset.add_pset',model,product=obj,name='BSA_DesignInputs');api.run('pset.edit_pset',model,pset=pset,properties=dict(Source=data['source'],Classification=data['classification'],Scope='Ideal equal-section cross; no product/fabrication/loss acceptance'))
    target=out/'cross.ifc';model.write(str(target));check=inspect(target,data)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Cross source changed')
    result=dict(inputs=pins,versions=versions,generator_sha256=digest(Path(__file__)),checks=check,ifc_sha256=digest(target),design_accepted=False)
    (out/'cross.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project');p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(run(a.project,a.out),indent=2));raise SystemExit(2)
