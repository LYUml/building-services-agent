"""Connect three synthetic hollow pipes to the upstream-Boolean tee trial."""
import argparse
import itertools
import json
import math
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.element as element
import ifcopenshell.util.placement as placement
import ifcopenshell.util.shape as shape_util
import ifcopenshell.util.system as system
from ifcopenshell.util.shape_builder import ShapeBuilder
from bsa.cli import digest
from bsa.solid_clash import from_mesh
from probe_ifc_tee import run as tee_trial,verify_geometry


def verify(path,spec,lengths):
    f=ifcopenshell.open(str(path));tee=f.by_type('IfcPipeFitting')[0]
    tee_ports={p.Name:p for p in system.get_ports(tee)}
    R,r,L,B=[spec[k] for k in ('outer_radius_m','inner_radius_m','main_half_length_m','branch_length_m')]
    anchors={'main-a':((0,0,-L),(0,0,-1)),'main-b':((0,0,L),(0,0,1)),'branch':((B,0,0),(1,0,0))}
    ports=[(tee_ports[k].GlobalId,*v) for k,v in anchors.items()]
    tee_checks,*_=verify_geometry(path,spec,tee.GlobalId,ports)
    checks=dict(tee_geometry=all(tee_checks.values()),exact_pipe_names={p.Name for p in f.by_type('IfcPipeSegment')}==set(lengths) and len(f.by_type('IfcPipeSegment'))==3)
    expected_links=set();pipe_checks={}
    for pipe in f.by_type('IfcPipeSegment'):
        xyz,axis=anchors[pipe.Name];xyz=np.array(xyz);axis=np.array(axis)
        ps={p.Name:p for p in system.get_ports(pipe)}
        solid=pipe.Representation.Representations[0].Items[0];profile=solid.SweptArea
        mat=placement.get_local_placement(pipe.ObjectPlacement) @ placement.get_axis2placement(solid.Position)
        start=mat[:3,3];end=start+mat[:3,:3] @ np.array(solid.ExtrudedDirection.DirectionRatios)*solid.Depth
        pin=placement.get_local_placement(ps['in'].ObjectPlacement);pout=placement.get_local_placement(ps['out'].ObjectPlacement)
        pipe_checks[pipe.Name]=bool(len(ps)==2 and np.allclose(start,xyz,atol=1e-9,rtol=0) and np.allclose(end,xyz+axis*lengths[pipe.Name],atol=1e-9,rtol=0)
            and np.allclose(pin[:3,3],start,atol=1e-9,rtol=0) and np.allclose(pout[:3,3],end,atol=1e-9,rtol=0)
            and np.allclose(pin[:3,2],-axis) and np.allclose(pout[:3,2],axis)
            and profile.is_a('IfcCircleHollowProfileDef') and math.isclose(profile.Radius,R) and math.isclose(profile.WallThickness,R-r))
        a,b=tee_ports[pipe.Name].id(),ps['in'].id();expected_links.update(((a,b),(b,a)))
    links=[(x.RelatingPort.id(),x.RelatedPort.id()) for x in f.by_type('IfcRelConnectsPorts')]
    checks['reversible_port_directions']=all(p.FlowDirection=='SOURCEANDSINK' for p in f.by_type('IfcDistributionPort'))
    checks['connections_match']=set(links)==expected_links and len(links)==len(expected_links)
    checks['pipe_geometry_ports_match']=all(pipe_checks.values())
    settings=ifcopenshell.geom.settings();settings.set('use-world-coords',True);settings.set('mesher-linear-deflection',1e-5);settings.set('mesher-angular-deflection',.05)
    solids={}
    for obj in [tee]+f.by_type('IfcPipeSegment'):
        shape=ifcopenshell.geom.create_shape(settings,obj)
        solids[obj.Name]=from_mesh((shape_util.get_vertices(shape.geometry).copy(),shape_util.get_faces(shape.geometry).copy()))
    overlaps={a+' / '+b:(solids[a]^solids[b]).volume() for a,b in itertools.combinations(solids,2)}
    checks['no_material_interpenetration']=all(abs(v)<1e-12 for v in overlaps.values())
    return dict(checks=checks,pipe_checks=pipe_checks,overlap_volumes_m3=overlaps,assembly_checks_pass=all(checks.values()),design_accepted=False)


def run(tee_spec,assembly_spec,out):
    tee_spec,assembly_spec,out=[Path(p).resolve() for p in (tee_spec,assembly_spec,out)]
    data=json.loads(assembly_spec.read_text(encoding='utf-8-sig'))
    if set(data)!={'source','pipe_lengths_m'} or not isinstance(data['source'],str) or not data['source'].strip():raise ValueError('sourced assembly lengths required')
    lengths=data['pipe_lengths_m']
    if not isinstance(lengths,dict) or set(lengths)!={'main-a','main-b','branch'} or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in lengths.values()):raise ValueError('three positive finite lengths required')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[1]) or any(out==p or out in p.parents for p in (tee_spec,assembly_spec)):raise ValueError('new repository output required')
    before={str(p):digest(p) for p in (tee_spec,assembly_spec)};out.mkdir(parents=True)
    trial=tee_trial(tee_spec,out/'tee')
    if not trial['geometry_trial_pass']:raise ValueError('tee geometry failed')
    spec=trial['parameters'];R=spec['outer_radius_m'];r=spec['inner_radius_m']
    f=ifcopenshell.open(str(out/'tee/tee.ifc'));tee=f.by_type('IfcPipeFitting')[0];builder=ShapeBuilder(f)
    body=f.by_type('IfcGeometricRepresentationSubContext')[0];storey=f.by_type('IfcBuildingStorey')[0]
    for port in list(system.get_ports(tee)):
        mat=placement.get_local_placement(port.ObjectPlacement);xyz=mat[:3,3];axis=mat[:3,2];length=lengths[port.Name]
        pipe=api.run('root.create_entity',f,ifc_class='IfcPipeSegment',name=port.Name)
        profile=f.create_entity('IfcCircleHollowProfileDef',ProfileType='AREA',Radius=R,WallThickness=R-r)
        solid=builder.extrude(profile,magnitude=length,position=xyz,position_z_axis=axis,position_x_axis=mat[:3,0])
        rep=builder.get_representation(body,[solid]);api.run('geometry.assign_representation',f,product=pipe,representation=rep)
        api.run('geometry.edit_object_placement',f,product=pipe,matrix=np.eye(4),is_si=True)
        api.run('spatial.assign_container',f,products=[pipe],relating_structure=storey)
        for name,pos,normal in [('in',xyz,-axis),('out',xyz+axis*length,axis)]:
            p=api.run('system.add_port',f,element=pipe);p.Name=name;p.FlowDirection='SOURCEANDSINK'
            m=np.eye(4);m[:3,3]=pos;m[:3,2]=normal;m[:3,0]=mat[:3,0];m[:3,1]=np.cross(normal,m[:3,0])
            api.run('geometry.edit_object_placement',f,product=p,matrix=m,is_si=True)
            if name=='in':api.run('system.connect_port',f,port1=port,port2=p,direction='SOURCEANDSINK')
        ps=api.run('pset.add_pset',f,product=pipe,name='BSA_AssemblyTrial')
        api.run('pset.edit_pset',f,pset=ps,properties={'Source':data['source'],'Length_m':length})
    path=out/'assembly.ifc';f.write(str(path));result=verify(path,spec,lengths)
    result.update(inputs=before,inputs_unchanged=all(digest(Path(p))==h for p,h in before.items()),ifc_sha256=digest(path),
                  scope='Synthetic butt-ended tee plus three pipes; no socket/weld/manufacturer, hydraulic or installation acceptance')
    result['assembly_checks_pass'] &= result['inputs_unchanged']
    (out/'assembly-checks.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('tee-spec','assembly-spec','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=run(a.tee_spec,a.assembly_spec,a.out);print(json.dumps(r,indent=2));raise SystemExit(0 if r['assembly_checks_pass'] else 2)
