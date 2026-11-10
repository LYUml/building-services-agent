"""Synthetic straight/transition/straight material and port continuity research."""
import argparse
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.validate
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system_util
import numpy as np
import manifold3d as m

from probe_ifc_transition_wall import run as wall_probe
from bsa.cli import digest
from bsa import rectangular_geometry as rectangular
from bsa.circular_geometry import frame,verify_closed_wall
from bsa.solid_clash import from_mesh
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


def inspect(path,descriptions,identities,expected_ports,expected_volume):
    model=ifcopenshell.open(str(path));logger=ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model,logger,express_rules=True)
    if logger.statements:raise ValueError('Saved assembly schema/EXPRESS issues')
    if len(model.by_type('IfcDistributionElement'))!=3:raise ValueError('Unexpected or unrepresented distribution elements')
    native=ifcopenshell.geom.settings();native.set(native.USE_WORLD_COORDS,True)
    solids=[];component_volumes=[]
    for name,guid in identities.items():
        obj=model.by_guid(guid);shape=ifcopenshell.geom.create_shape(native,obj)
        verts=np.asarray(shape.geometry.verts).reshape(-1,3);faces=np.asarray(shape.geometry.faces).reshape(-1,3)
        if name in descriptions:rectangular.verify(obj,descriptions[name],shape)
        else:
            if not np.allclose(placement.get_local_placement(obj.ObjectPlacement),np.eye(4),atol=1e-10,rtol=0):
                raise ValueError('Transition placement differs from its source')
            expected_bounds=[[-.3,-.15,0.],[.3,.15,expected_ports['transition.out']['matrix'][2][3]]]
            if not np.allclose([verts.min(axis=0),verts.max(axis=0)],expected_bounds,atol=1e-9,rtol=0):
                raise ValueError('Transition material bounds differ from source stations')
        solid=from_mesh((verts,faces));solids.append(solid);component_volumes.append(solid.volume())
        if {p.Name for p in system_util.get_ports(obj)}!={name+'.in',name+'.out'}:
            raise ValueError('Component port ownership differs')
    systems=model.by_type('IfcDistributionSystem')
    if len(systems)!=1 or systems[0].PredefinedType!='VENTILATION':raise ValueError('One declared ventilation system required')
    members={obj.GlobalId for relation in systems[0].IsGroupedBy for obj in relation.RelatedObjects}
    if members!=set(identities.values()):raise ValueError('Saved system membership differs')
    ports={p.Name:p for p in model.by_type('IfcDistributionPort')}
    if set(ports)!=set(expected_ports):raise ValueError('Saved port identity coverage differs')
    for name,expected in expected_ports.items():
        port=ports[name];actual=placement.get_local_placement(port.ObjectPlacement)
        if port.FlowDirection!=expected['direction'] or not np.allclose(actual,expected['matrix'],atol=1e-9,rtol=0):
            raise ValueError('Saved port direction/frame differs')
    pairs=[('up.out','transition.in'),('transition.out','down.in')]
    links={(r.RelatingPort.Name,r.RelatedPort.Name) for r in model.by_type('IfcRelConnectsPorts')}
    if links!=set(pairs):raise ValueError('Directed connection topology differs')
    for a,b in pairs:
        pa,pb=(placement.get_local_placement(ports[n].ObjectPlacement) for n in (a,b))
        if not np.allclose(pa[:3,3],pb[:3,3],atol=1e-9,rtol=0) or not np.allclose(pa[:3,2],-pb[:3,2],atol=1e-9,rtol=0):
            raise ValueError('Connected port planes are not coincident and opposed')
    union=m.Manifold.batch_boolean(solids,m.OpType.Add)
    if union.status()!=m.Error.NoError or len(union.decompose())!=1:raise ValueError('Assembly material is not one connected solid')
    mesh=union.to_mesh64();v=np.asarray(mesh.vert_properties)[:,:3];f=np.asarray(mesh.tri_verts)
    volume,error,euler=verify_closed_wall(v,f,expected_volume)
    if not math.isclose(sum(component_volumes),volume,rel_tol=1e-9,abs_tol=1e-10):raise ValueError('Unexpected assembly material overlap')
    length=v[:,2].max()-v[:,2].min();centre=(v[:,2].max()+v[:,2].min())/2
    bore=m.Manifold.cube((.1,.1,length+.2),center=True).translate((0.,0.,centre))
    common=union^bore
    if common.status()!=m.Error.NoError or abs(common.volume())>1e-12:raise ValueError('Assembly centre bore blocked')
    return dict(schema_express_issue_count=0,represented_components=3,ports=len(ports),directed_connections=len(links),
                opposed_coincident_interfaces=2,one_connected_material=True,material_volume_m3=volume,
                independent_material_volume_m3=expected_volume,relative_volume_error=error,euler_characteristic=euler,
                centre_through_bore_overlap_m3=common.volume(),component_volume_sum_m3=sum(component_volumes))


def run(out):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT) or out==ROOT or out.exists():raise ValueError('New repository research output required')
    out.mkdir(parents=True)
    wall=wall_probe(out/'wall');source=out/'wall/transition-wall-probe.ifc';source_sha=digest(source)
    model=ifcopenshell.open(str(source));fitting=model.by_type('IfcDuctFitting')[0]
    for placeholder in list(model.by_type('IfcDuctSegment')):
        api.run('root.remove_product',model,product=placeholder)
    body=fitting.Representation.Representations[0].ContextOfItems
    length=.2+wall['transition_length_m'];thickness=.005
    descriptions={};objects={'transition':fitting}
    for name,width,height,z in [('up',.59,.29,-.3),('down',.39,.19,length)]:
        outer_w,outer_h=width+2*thickness,height+2*thickness
        device=dict(ifc_class='IfcDuctSegment',origin_m=[-outer_w/2,-outer_h/2,z],size_m=[outer_w,outer_h,.3],
                    properties=dict(InternalWidth_m=width,InternalHeight_m=height,WallThickness_m=thickness),
                    ports=[dict(id='in',direction='SINK',offset_m=[outer_w/2,outer_h/2,0]),
                           dict(id='out',direction='SOURCE',offset_m=[outer_w/2,outer_h/2,.3])])
        obj=api.run('root.create_entity',model,ifc_class='IfcDuctSegment',name='Synthetic '+name)
        rectangular.author(model,body,obj,device)
        pset=api.run('pset.add_pset',model,product=obj,name='BSA_DesignInputs')
        api.run('pset.edit_pset',model,pset=pset,properties=device['properties'])
        descriptions[name]=device;objects[name]=obj
    ports={};expected={}
    positions={'up':(-.3,0.),'transition':(0.,length),'down':(length,length+.3)}
    for name,obj in objects.items():
        for end,z in zip(('in','out'),positions[name]):
            port=api.run('system.add_port',model,element=obj);port.Name=name+'.'+end
            port.FlowDirection='SINK' if end=='in' else 'SOURCE';port.PredefinedType='DUCT';port.SystemType='VENTILATION'
            matrix=frame((0.,0.,-1. if end=='in' else 1.));matrix[:3,3]=(0.,0.,z)
            api.run('geometry.edit_object_placement',model,product=port,matrix=matrix,is_si=True)
            ports[port.Name]=port;expected[port.Name]=dict(direction=port.FlowDirection,matrix=matrix.tolist())
    for a,b in [('up.out','transition.in'),('transition.out','down.in')]:
        api.run('system.connect_port',model,port1=ports[a],port2=ports[b],direction='SOURCE')
    distribution=api.run('root.create_entity',model,ifc_class='IfcDistributionSystem',name='Synthetic ventilation assembly',predefined_type='VENTILATION')
    api.run('system.assign_system',model,products=list(objects.values()),system=distribution)
    identities={name:obj.GlobalId for name,obj in objects.items()}
    volume=wall['independent_material_volume_m3']+sum(rectangular.specification(d)['volume'] for d in descriptions.values())
    target=out/'transition-assembly.ifc';model.write(str(target))
    checks=inspect(target,descriptions,identities,expected,volume)
    negative={}
    for case in ('port_shift','solid_shift','transition_shift'):
        altered=ifcopenshell.open(str(target))
        if case=='port_shift':
            port=next(p for p in altered.by_type('IfcDistributionPort') if p.Name=='transition.out')
            matrix=placement.get_local_placement(port.ObjectPlacement);matrix[2,3]+=.001
            api.run('geometry.edit_object_placement',altered,product=port,matrix=matrix,is_si=True)
        elif case=='solid_shift':
            solid=altered.by_guid(identities['down']).Representation.Representations[0].Items[0]
            solid.Position.Location.Coordinates=(0.,0.,.001)
        else:
            obj=altered.by_guid(identities['transition']);matrix=np.eye(4);matrix[0,3]=.001
            api.run('geometry.edit_object_placement',altered,product=obj,matrix=matrix,is_si=True)
        bad=out/(case+'.ifc');altered.write(str(bad))
        try:inspect(bad,descriptions,identities,expected,volume)
        except (ValueError,ProjectError) as exc:negative[case]=str(exc)
        else:raise ValueError('Invalid assembly control accepted')
    if digest(source)!=source_sha:raise ValueError('Source transition wall changed')
    result=dict(checks=checks,negative_controls=negative,source_ifc_sha256=source_sha,ifc_sha256=digest(target),
                script_sha256=digest(Path(__file__)),production_adapter=False,design_accepted=False,
                scope='Synthetic centred section-plane-offset transition and straight pair; no constant sheet-normal wall/product/loss/actual-project acceptance')
    (out/'probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    result=run(parser.parse_args().out);print(json.dumps(result,indent=2))
