"""Compose a declared four-port cross with existing centred transition adapters."""
from collections import Counter
import itertools
import json
import math
from pathlib import Path
import uuid
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import manifold3d as m
import numpy as np
from . import rectangular_cross as cross,rectangular_transition as transition
from .rectangular_tee_transitions import relative_placement
from .rectangular_tee_assembly import opposite
from .tee_geometry import stable_guid,project_namespace,placement_matrix
from .solid_clash import from_mesh
from .workspace import allowed
from .cli import digest

KEY='RECTANGULAR-CROSS-TRANSITIONS'


def children(spec,arms):
    cross.validate(spec)
    if not isinstance(arms,dict) or set(arms)!=set(cross.NAMES):raise ValueError('Every cross arm must explicitly be bare or a transition')
    result={};frames=cross.port_frames(spec)
    for name,row in arms.items():
        if row=={'kind':'bare'}:continue
        if not isinstance(row,dict) or set(row)!={'kind','end_section_m','start_length_m','end_length_m','transition_length_m','upstream_angle_degrees','geometry_method'} or row['kind']!='transition':raise ValueError('Complete explicit cross transition declaration required')
        frame=frames[name];direction=spec['port_directions'][name]
        child=dict(project_uuid=str(uuid.uuid5(project_namespace(spec),KEY+':'+name)),source=spec['source']+'; cross transition '+name,classification=spec['classification'],wall_model='section_plane_offset',start_section_m=[spec['internal_width_m'],spec['internal_height_m']],section_offset_m=spec['wall_thickness_m'],port_directions=dict(start=opposite(direction),end=direction),placement=dict(source='Source cross cap '+name,origin_m=frame[:3,3].tolist(),rotation=frame[:3,:3].tolist()),**{k:v for k,v in row.items() if k!='kind'})
        transition.validate(child);result[name]=child
    return result


def inspect(path,spec,arms):
    child_specs=children(spec,arms); core=cross.inspect(path,spec,component=True);file=ifcopenshell.open(str(path))
    obj=file.by_guid(stable_guid(spec,'IfcDuctFitting',cross.KEY));objects=[obj];ports={p.GlobalId:p for p in system.get_ports(obj)};core_ports={p.Name:p for p in ports.values()};links=set();vol=core['independent_material_volume_m3'];external=cross.port_frames(spec)
    for name,child in child_specs.items():
        check=transition.inspect(path,child,component=True);vol+=check['independent_material_volume_m3']
        added=file.by_guid(stable_guid(child,'IfcDuctFitting',transition.KEY));objects.append(added);owned={p.Name:p for p in system.get_ports(added)};ports.update({p.GlobalId:p for p in owned.values()})
        a,b=core_ports[name].GlobalId,owned['start'].GlobalId
        direction=spec['port_directions'][name]
        if direction in ('SOURCE','SOURCEANDSINK'):links.add((a,b))
        if direction in ('SINK','SOURCEANDSINK'):links.add((b,a))
        external[name]=transition.port_frames(child)['end']
    if {o.GlobalId for o in file.by_type('IfcDistributionElement')}!={o.GlobalId for o in objects} or len(file.by_type('IfcDistributionElement'))!=len(objects) or len(file.by_type('IfcDistributionPort'))!=len(ports):raise ValueError('Cross assembly exact body/port inventory differs')
    actual=[(r.RelatingPort.GlobalId,r.RelatedPort.GlobalId) for r in file.by_type('IfcRelConnectsPorts')]
    if len(actual)!=len(links) or set(actual)!=links:raise ValueError('Cross assembly links differ')
    for a,b in links:
        x,y=[placement.get_local_placement(ports[g].ObjectPlacement) for g in (a,b)]
        if not np.allclose(x[:3,3],y[:3,3],atol=1e-9,rtol=0) or not np.allclose(x[:3,2],-y[:3,2],atol=1e-9,rtol=0):raise ValueError('Cross transition interface planes differ')
    groups=file.by_type('IfcDistributionSystem')
    if len(groups)!=1 or groups[0].GlobalId!=stable_guid(spec,'IfcDistributionSystem',KEY) or {o.GlobalId for r in groups[0].IsGroupedBy for o in r.RelatedObjects}!={o.GlobalId for o in objects}:raise ValueError('Exact cross assembly ventilation system required')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);transform=placement_matrix(spec);solids=[]
    for o in objects:
        shape=ifcopenshell.geom.create_shape(settings,o);v=np.array(shape.geometry.verts).reshape(-1,3);v=(v-transform[:3,3])@transform[:3,:3];f=np.array(shape.geometry.faces).reshape(-1,3);solids.append(from_mesh((v,f)))
    for a,b in itertools.combinations(solids,2):
        if abs((a^b).volume())>1e-12:raise ValueError('Cross assembly components interpenetrate')
    union=m.Manifold.batch_boolean(solids,m.OpType.Add)
    if union.status()!=m.Error.NoError or len(union.decompose())!=1 or not math.isclose(union.volume(),vol,rel_tol=1e-9,abs_tol=1e-10):raise ValueError('Cross assembly material disconnected or volume differs')
    mesh=union.to_mesh64();v=np.asarray(mesh.vert_properties)[:,:3];f=np.asarray(mesh.tri_verts);edges=Counter(tuple(sorted((int(a),int(b)))) for face in f for a,b in zip(face,[face[1],face[2],face[0]]));euler=len(v)-len(edges)+len(f)
    if any(n!=2 for n in edges.values()) or euler!=-4:raise ValueError('Cross assembly four-ended closed wall topology differs')
    # Independently probe the two complete centre passages, including tapered ends.
    w,h,t,L,B=cross.validate(spec);sizes={name:child_specs[name]['end_section_m'] if name in child_specs else [w,h] for name in cross.NAMES};lengths={name:transition.total_length(child_specs[name]) if name in child_specs else 0 for name in cross.NAMES}
    for a,b,axis,reach in [('main-a','main-b',2,L),('branch-a','branch-b',0,B)]:
        width=min(w,sizes[a][0],sizes[b][0])*.5;height=min(h,sizes[a][1],sizes[b][1])*.5
        lo=-reach-lengths[a]-.1;hi=reach+lengths[b]+.1
        size=[width,height,hi-lo] if axis==2 else [hi-lo,height,width];centre=[0.,0.,0.];centre[axis]=(lo+hi)/2
        common=union^m.Manifold.cube(size,center=True).translate(centre)
        if common.status()!=m.Error.NoError or abs(common.volume())>1e-12:raise ValueError('Composed cross centre passage blocked')
    return dict(components=len(objects),ports=len(ports),actual_links=len(links),four_boundary_arms=True,
        one_connected_material=True,euler_characteristic=euler,material_volume_m3=union.volume(),independent_material_volume_m3=vol,external_end_frames={n:f.tolist() for n,f in external.items()},design_accepted=False)


def run(project,out):
    project,out=Path(project).resolve(),Path(out).resolve();data=json.loads(project.read_text())
    if not isinstance(data,dict) or set(data)!={'cross','arms'}:raise ValueError('Exact cross spec/arms project required')
    spec=data['cross'];child_specs=children(spec,data['arms'])
    if out.exists() or not all(allowed(p) for p in (project,out)) or out==project or out in project.parents:raise ValueError('Fresh selected workspace output outside source required')
    before=digest(project);source=out/'cross-spec.json';out.mkdir(parents=True);source.write_text(json.dumps(spec,indent=2));cross.run(source,out/'core');file=ifcopenshell.open(str(out/'core/cross.ifc'));core=file.by_guid(stable_guid(spec,'IfcDuctFitting',cross.KEY));core_ports={p.Name:p for p in system.get_ports(core)};objects=[core]
    for name,child in child_specs.items():
        source=out/(name+'.json');source.write_text(json.dumps(child,indent=2));transition.run(source,out/name)
        library=ifcopenshell.open(str(out/name/'transition.ifc'));original=library.by_guid(stable_guid(child,'IfcDuctFitting',transition.KEY));added=api.run('project.append_asset',file,library=library,element=original,assume_asset_uniqueness_by_name=False);objects.append(added)
        frame=placement_matrix(child);added.ObjectPlacement=relative_placement(file,np.linalg.inv(placement_matrix(spec))@frame,core.ObjectPlacement)
        ports={p.Name:p for p in system.get_ports(added)}
        for pname,p in ports.items():
            local=np.diag([1.,-1. if pname=='start' else 1.,-1. if pname=='start' else 1.,1.]);local[2,3]=0 if pname=='start' else transition.total_length(child);p.ObjectPlacement=relative_placement(file,local,added.ObjectPlacement)
        api.run('system.connect_port',file,port1=core_ports[name],port2=ports['start'],direction=spec['port_directions'][name])
    group=api.run('root.create_entity',file,ifc_class='IfcDistributionSystem',name='Declared four-port cross assembly',predefined_type='VENTILATION');group.GlobalId=stable_guid(spec,'IfcDistributionSystem',KEY);api.run('system.assign_system',file,products=objects,system=group)
    target=out/'assembly.ifc';file.write(str(target));check=inspect(target,spec,data['arms'])
    if digest(project)!=before:raise ValueError('Cross assembly source changed')
    result=dict(inputs={str(project):before},ifc_sha256=digest(target),generator_sha256=digest(Path(__file__)),checks=check,design_accepted=False)
    (out/'assembly.json').write_text(json.dumps(result,indent=2));return result
