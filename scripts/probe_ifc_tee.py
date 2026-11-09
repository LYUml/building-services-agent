"""Synthetic equal-bore tee trial using upstream IFC Boolean and mesh engines."""
import argparse
import json
import importlib.metadata
import math
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.shape
import ifcopenshell.util.placement
import manifold3d as manifold
from ifcopenshell.util.shape_builder import ShapeBuilder
from bsa.cli import digest


def run(spec_path,out):
    spec_path,out=Path(spec_path).resolve(),Path(out).resolve()
    data=json.loads(spec_path.read_text(encoding='utf-8-sig'))
    if set(data)!={'source','outer_radius_m','inner_radius_m','main_half_length_m','branch_length_m'} or not isinstance(data['source'],str) or not data['source'].strip():raise ValueError('exact sourced tee parameters required')
    R,r,L,B=[data[k] for k in ('outer_radius_m','inner_radius_m','main_half_length_m','branch_length_m')]
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (R,r,L,B)) or not 0<r<R<min(L,B):raise ValueError('finite 0 < bore radius < outer radius < both arm lengths required')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[1]) or out==spec_path or out in spec_path.parents:raise ValueError('new repository output required')
    versions={name:importlib.metadata.version(name) for name in ('ifcopenshell','manifold3d')}
    if versions!={'ifcopenshell':'0.8.5','manifold3d':'3.5.4'}:raise ValueError('verified pinned geometry runtimes required')
    before=digest(spec_path);out.mkdir(parents=True)
    f=ifcopenshell.file(schema='IFC4');project=api.run('root.create_entity',f,ifc_class='IfcProject',name='Synthetic equal-bore tee trial')
    metre=api.run('unit.add_si_unit',f,unit_type='LENGTHUNIT');api.run('unit.assign_unit',f,units=[metre])
    context=api.run('context.add_context',f,context_type='Model')
    body=api.run('context.add_context',f,context_type='Model',context_identifier='Body',target_view='MODEL_VIEW',parent=context)
    storey=api.run('root.create_entity',f,ifc_class='IfcBuildingStorey',name='Synthetic trial')
    api.run('aggregate.assign_object',f,products=[storey],relating_object=project)
    tee=api.run('root.create_entity',f,ifc_class='IfcPipeFitting',predefined_type='JUNCTION',name='SYNTHETIC-TEE')
    api.run('spatial.assign_container',f,products=[tee],relating_structure=storey)
    builder=ShapeBuilder(f)
    def cylinders(radius):
        a=builder.extrude(builder.circle(radius=radius),magnitude=2*L,position=(0.,0.,-L))
        b=builder.extrude(builder.circle(radius=radius),magnitude=B,position_z_axis=(1.,0.,0.),position_x_axis=(0.,1.,0.))
        return api.run('geometry.add_boolean',f,first_item=a,second_items=[b],operator='UNION')[-1]
    outer=cylinders(R);inner=cylinders(r)
    wall=api.run('geometry.add_boolean',f,first_item=outer,second_items=[inner],operator='DIFFERENCE')[-1]
    representation=builder.get_representation(body,[wall],representation_type='CSG')
    api.run('geometry.assign_representation',f,product=tee,representation=representation)
    api.run('geometry.edit_object_placement',f,product=tee,matrix=np.eye(4),is_si=True)
    ports=[]
    for name,xyz,axis in [('main-a',(0,0,-L),(0,0,-1)),('main-b',(0,0,L),(0,0,1)),('branch',(B,0,0),(1,0,0))]:
        port=api.run('system.add_port',f,element=tee);port.Name=name;port.FlowDirection='SOURCEANDSINK'
        mat=np.eye(4);mat[:3,3]=xyz;mat[:3,2]=axis
        mat[:3,0]=(0,1,0);mat[:3,1]=np.cross(mat[:3,2],mat[:3,0])
        api.run('geometry.edit_object_placement',f,product=port,matrix=mat,is_si=True);ports.append((port.GlobalId,list(xyz),list(axis)))
    ps=api.run('pset.add_pset',f,product=tee,name='BSA_TeeTrial')
    api.run('pset.edit_pset',f,pset=ps,properties=dict(Source=data['source'],OuterRadius_m=R,InnerRadius_m=r,MainHalfLength_m=L,BranchLength_m=B,Scope='Synthetic intersecting-cylinder wall; no manufacturer, K-factor or installation acceptance'))
    path=out/'tee.ifc';f.write(str(path))
    checks,volume,expected,empty_volumes,wall_overlap=verify_geometry(path,data,tee.GlobalId,ports)
    checks['source_unchanged']=digest(spec_path)==before
    result=dict(runtime=versions,source_file=str(spec_path),source_sha256=before,ifc_sha256=digest(path),parameters=data,checks=checks,
                measured_wall_volume_m3=volume,analytic_wall_volume_m3=expected,bore_probe_intersections_m3=empty_volumes,wall_control_intersection_m3=wall_overlap,
                geometry_trial_pass=all(checks.values()),design_accepted=False,scope='Synthetic equal-bore 90-degree intersecting-cylinder tee wall; no hydraulic loss, product or drawing validation')
    (out/'trial.json').write_text(json.dumps(result,indent=2));return result


def verify_geometry(path,data,guid,ports):
    R,r,L,B=[data[k] for k in ('outer_radius_m','inner_radius_m','main_half_length_m','branch_length_m')]
    saved=ifcopenshell.open(str(path));obj=saved.by_guid(guid)
    settings=ifcopenshell.geom.settings();settings.set('mesher-linear-deflection',1e-5);settings.set('mesher-angular-deflection',.05)
    shape=ifcopenshell.geom.create_shape(settings,obj)
    vertices=ifcopenshell.util.shape.get_vertices(shape.geometry);faces=ifcopenshell.util.shape.get_faces(shape.geometry)
    mesh=manifold.Manifold(manifold.Mesh64(np.array(vertices,dtype=np.float64,copy=True),np.array(faces,dtype=np.uint64,copy=True)))
    expected=math.pi*(R*R-r*r)*(2*L+B)-8*(R**3-r**3)/3
    probes=[manifold.Manifold.cylinder(2*L,r*.9,circular_segments=64,center=True),
            manifold.Manifold.cylinder(B,r*.9,circular_segments=64).rotate((0,90,0))]
    empty_volumes=[(mesh ^ probe).volume() for probe in probes]
    wall_probe=manifold.Manifold.cube((R-r,R-r,R-r),center=True).translate(((R+r)/2,0,-L/2))
    wall_overlap=(mesh ^ wall_probe).volume()
    checks=dict(mesh_valid=str(mesh.status())=='Error.NoError',one_connected_wall=len(mesh.decompose())==1,
                volume_matches_analytic=math.isclose(mesh.volume(),expected,rel_tol=.002),
                main_and_branch_bores_clear=all(abs(v)<1e-12 for v in empty_volumes),wall_control_detected=wall_overlap>1e-12,
                ports_match=all(np.allclose(ifcopenshell.util.placement.get_local_placement(saved.by_guid(g).ObjectPlacement)[:3,3],xyz) and np.allclose(ifcopenshell.util.placement.get_local_placement(saved.by_guid(g).ObjectPlacement)[:3,2],axis) for g,xyz,axis in ports))
    return checks,mesh.volume(),expected,empty_volumes,wall_overlap


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.spec,a.out);print(json.dumps(r,indent=2));raise SystemExit(0 if r['geometry_trial_pass'] else 2)
