"""Source-declared equal-section sharp rectangular tee; no product/loss acceptance."""
import argparse
from collections import Counter
import importlib.metadata
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.placement as placement
import ifcopenshell.util.element as element_util
import ifcopenshell.util.system as system_util
import ifcopenshell.validate
from ifcopenshell.util.shape_builder import ShapeBuilder
import numpy as np
import manifold3d as m

from .cli import digest
from .workspace import allowed
from .solid_clash import from_mesh
from .tee_geometry import project_namespace,stable_guid,placement_matrix

NAMES=('main-a','main-b','branch')


def validate(data):
    keys={'project_uuid','source','classification','internal_width_m','internal_height_m','wall_thickness_m',
          'main_half_length_m','branch_length_m','port_directions','placement'}
    if not isinstance(data,dict) or set(data)!=keys:raise ValueError('Exact sourced rectangular tee fields required')
    project_namespace(data);placement_matrix(data)
    if not isinstance(data['source'],str) or not data['source'].strip() or data['classification'] not in ('given','assumed','secondary_transcription'):
        raise ValueError('Explicit source and geometry classification required')
    values=[data[k] for k in ('internal_width_m','internal_height_m','wall_thickness_m','main_half_length_m','branch_length_m')]
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values):raise ValueError('Positive finite metre dimensions required')
    w,h,t,L,B=values
    if min(L,B)<=w/2+t:raise ValueError('Arm ends must lie beyond the branch junction')
    directions=data['port_directions']
    if not isinstance(directions,dict) or set(directions)!=set(NAMES):raise ValueError('Three explicit port directions required')
    if any(v not in ('SOURCE','SINK','SOURCEANDSINK') for v in directions.values()):raise ValueError('Unsupported port direction')
    if set(directions.values())!={'SOURCEANDSINK'} and (set(directions.values())!={'SOURCE','SINK'}):
        raise ValueError('Use all bidirectional ports or explicit mixing/splitting SOURCE/SINK ports')
    return w,h,t,L,B


def port_frames(data):
    w,h,t,L,B=validate(data);transform=placement_matrix(data);frames={}
    for name,point,normal,width in [('main-a',(0,0,-L),(0,0,-1),(1,0,0)),
                                    ('main-b',(0,0,L),(0,0,1),(1,0,0)),
                                    ('branch',(B,0,0),(1,0,0),(0,0,-1))]:
        frame=np.eye(4);frame[:3,:3]=np.column_stack((width,np.cross(normal,width),normal));frame[:3,3]=point
        frames[name]=transform@frame
    return frames


def inspect(path,data):
    w,h,t,L,B=validate(data);transform=placement_matrix(data)
    model=ifcopenshell.open(str(path));logger=ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model,logger,express_rules=True)
    if logger.statements:raise ValueError('Saved rectangular tee schema/EXPRESS issues')
    fitting=model.by_guid(stable_guid(data,'IfcDuctFitting','RECTANGULAR-TEE'))
    if fitting.PredefinedType!='JUNCTION' or not np.allclose(placement.get_local_placement(fitting.ObjectPlacement),transform,atol=1e-9,rtol=0):
        raise ValueError('Saved tee type/placement differs')
    properties=element_util.get_psets(fitting).get('BSA_DesignInputs',{})
    if properties.get('Source')!=data['source'] or properties.get('Classification')!=data['classification']:
        raise ValueError('Saved tee source/classification differs')
    body=fitting.Representation.Representations
    if len(body)!=1 or body[0].RepresentationType!='CSG' or len(body[0].Items)!=1:raise ValueError('One native CSG tee body required')
    wall=body[0].Items[0]
    if not wall.is_a('IfcBooleanResult') or wall.Operator!='DIFFERENCE':raise ValueError('Explicit outer-minus-inner wall required')
    for union,width,height in [(wall.FirstOperand,w+2*t,h+2*t),(wall.SecondOperand,w,h)]:
        if not union.is_a('IfcBooleanResult') or union.Operator!='UNION':raise ValueError('Main/branch union required')
        for solid,depth,origin,axis,reference in [(union.FirstOperand,2*L,(0,0,-L),(0,0,1),(1,0,0)),
                                                 (union.SecondOperand,B,(0,0,0),(1,0,0),(0,0,-1))]:
            if not solid.is_a('IfcExtrudedAreaSolid') or not solid.SweptArea.is_a('IfcRectangleProfileDef'):
                raise ValueError('Explicit rectangular prism operands required')
            profile=solid.SweptArea
            if profile.Position is not None or not np.allclose([profile.XDim,profile.YDim,solid.Depth],[width,height,depth],atol=1e-10,rtol=0):
                raise ValueError('Saved tee cross-section/length differs')
            expected=np.eye(4);expected[:3,:3]=np.column_stack((reference,np.cross(axis,reference),axis));expected[:3,3]=origin
            if not np.allclose(placement.get_axis2placement(solid.Position),expected,atol=1e-10,rtol=0) or tuple(solid.ExtrudedDirection.DirectionRatios)!=(0.,0.,1.):
                raise ValueError('Saved tee operand placement differs')
    ports=system_util.get_ports(fitting)
    if len(ports)!=3 or {p.Name for p in ports}!=set(NAMES):raise ValueError('Three owned tee ports required')
    for port in ports:
        if port.GlobalId!=stable_guid(data,'IfcDistributionPort','RECTANGULAR-TEE',port.Name) or port.FlowDirection!=data['port_directions'][port.Name]:raise ValueError('Saved tee port identity/direction differs')
        if not np.allclose(placement.get_local_placement(port.ObjectPlacement),port_frames(data)[port.Name],atol=1e-9,rtol=0):raise ValueError('Saved tee port frame differs')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    shape=ifcopenshell.geom.create_shape(settings,fitting)
    vertices=np.asarray(shape.geometry.verts).reshape(-1,3)
    vertices=(vertices-transform[:3,3])@transform[:3,:3]
    faces=np.asarray(shape.geometry.faces).reshape(-1,3);solid=from_mesh((vertices,faces))
    if len(solid.decompose())!=1:raise ValueError('One connected tee material required')
    outer_w,outer_h=w+2*t,h+2*t
    expected_volume=((2*L+B)*outer_w-outer_w**2/2)*outer_h-((2*L+B)*w-w**2/2)*h
    if not math.isclose(solid.volume(),expected_volume,rel_tol=1e-9,abs_tol=1e-10):raise ValueError('Tee material volume differs from independent prism integration')
    edges=Counter(tuple(sorted((int(a),int(b)))) for face in faces for a,b in zip(face,[face[1],face[2],face[0]]))
    euler=len(vertices)-len(edges)+len(faces)
    if any(v!=2 for v in edges.values()) or euler!=-2:raise ValueError('Tee mesh does not preserve three-port bore topology')
    expected_bounds=[[-outer_w/2,-outer_h/2,-L],[B,outer_h/2,L]]
    if not np.allclose([vertices.min(axis=0),vertices.max(axis=0)],expected_bounds,atol=1e-8,rtol=0):raise ValueError('Tee material bounds differ')
    main_probe=m.Manifold.cube((w*.5,h*.5,2*L+.2),center=True)
    branch_probe=m.Manifold.cube((B+.1,h*.5,w*.5),center=True).translate(((B+.1)/2,0,0))
    overlaps=[]
    for probe in (main_probe,branch_probe):
        common=solid^probe
        if common.status()!=m.Error.NoError or abs(common.volume())>1e-12:raise ValueError('Tee air-bore probe intersects material')
        overlaps.append(common.volume())
    return dict(schema_express_issue_count=0,ports=3,one_connected_material=True,euler_characteristic=euler,
                native_material_volume_m3=solid.volume(),independent_material_volume_m3=expected_volume,
                bore_probe_overlap_m3=overlaps,saved_source_geometry_and_port_frames=True)


def run(project,out):
    project,out=Path(project).resolve(),Path(out).resolve();data=json.loads(project.read_text(encoding='utf-8'))
    w,h,t,L,B=validate(data)
    if out.exists() or not all(allowed(p) for p in (project,out)) or out==project or out in project.parents:
        raise ValueError('New selected workspace output outside source required')
    versions={name:importlib.metadata.version(name) for name in ('ifcopenshell','manifold3d')}
    if versions!={'ifcopenshell':'0.8.5','manifold3d':'3.5.4'}:raise ValueError('Pinned IFC/Boolean runtimes required')
    before=digest(project);out.mkdir(parents=True)
    model=api.run('project.create_file',version='IFC4');api.run('root.create_entity',model,ifc_class='IfcProject',name='Declared ideal rectangular tee')
    unit=api.run('unit.add_si_unit',model,unit_type='LENGTHUNIT');api.run('unit.assign_unit',model,units=[unit])
    context=api.run('context.add_context',model,context_type='Model')
    body=api.run('context.add_context',model,context_type='Model',context_identifier='Body',target_view='MODEL_VIEW',parent=context)
    fitting=api.run('root.create_entity',model,ifc_class='IfcDuctFitting',predefined_type='JUNCTION',name='RECTANGULAR-TEE')
    fitting.GlobalId=stable_guid(data,'IfcDuctFitting','RECTANGULAR-TEE');builder=ShapeBuilder(model)
    def prisms(width,height):
        profile=model.create_entity('IfcRectangleProfileDef',ProfileType='AREA',XDim=width,YDim=height)
        main=builder.extrude(profile,magnitude=2*L,position=(0.,0.,-L))
        branch=builder.extrude(profile,magnitude=B,position_z_axis=(1.,0.,0.),position_x_axis=(0.,0.,-1.))
        return api.run('geometry.add_boolean',model,first_item=main,second_items=[branch],operator='UNION')[-1]
    outer,inner=prisms(w+2*t,h+2*t),prisms(w,h)
    wall=api.run('geometry.add_boolean',model,first_item=outer,second_items=[inner],operator='DIFFERENCE')[-1]
    representation=builder.get_representation(body,[wall],representation_type='CSG')
    api.run('geometry.assign_representation',model,product=fitting,representation=representation)
    api.run('geometry.edit_object_placement',model,product=fitting,matrix=placement_matrix(data),is_si=True)
    for name,matrix in port_frames(data).items():
        port=api.run('system.add_port',model,element=fitting);port.Name=name
        port.GlobalId=stable_guid(data,'IfcDistributionPort','RECTANGULAR-TEE',name)
        port.FlowDirection=data['port_directions'][name];port.PredefinedType='DUCT';port.SystemType='VENTILATION'
        api.run('geometry.edit_object_placement',model,product=port,matrix=matrix,is_si=True)
    pset=api.run('pset.add_pset',model,product=fitting,name='BSA_DesignInputs')
    api.run('pset.edit_pset',model,pset=pset,properties=dict(Source=data['source'],Classification=data['classification'],
        Scope='Ideal equal-section intersecting rectangular prism wall; no product, loss or fabrication acceptance'))
    target=out/'rectangular-tee.ifc';model.write(str(target));checks=inspect(target,data)
    if digest(project)!=before:raise ValueError('Tee source changed during authoring')
    result=dict(inputs={str(project):before},generator_sha256=digest(Path(__file__)),ifc_sha256=digest(target),
                versions=versions,parameters=data,checks=checks,geometry_checks_pass=True,design_accepted=False,
                scope='Source-declared ideal equal-section sharp rectangular tee only; no radiused takeoff, variable sections, losses, products, assembly or jurisdiction acceptance')
    (out/'rectangular-tee.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project');parser.add_argument('--out',required=True)
    args=parser.parse_args();result=run(args.project,args.out)
    print(result['checks']);print('Complete fitting/project acceptance pending')
    raise SystemExit(2)
