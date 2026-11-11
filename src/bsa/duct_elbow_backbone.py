"""Fit explicitly declared finite elbows to source routes;retain every blocked corner."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from . import bim,rectangular_geometry as straight,rectangular_elbow as elbow,circular_geometry
from .duct_backbone_ifc import compile_model as source_model,export_storey
from .circular_elbow import AXES
from .cli import digest


def compile_model(junction,schedule,basis,radii):
    model=source_model(junction,schedule,basis);nodes={n['node']:n for n in junction['nodes']}
    wanted={name for name,n in nodes.items() if n['connection_requirement']=='elbow_required'}
    if not isinstance(radii,dict) or set(radii)!=wanted:raise ValueError('Explicit radius/classification/source for every original equal-section elbow required')
    thickness=basis['wall_thickness_m']['value'];blocked={};budgets=[]
    for name,row in radii.items():
        if not isinstance(row,dict) or set(row)!={'radius_m','classification','source'} or row['classification'] not in ('assumed','design_target','given','measured') or not isinstance(row['source'],str) or not row['source'].strip():raise ValueError('Explicit sourced radius classification required')
        radius=row['radius_m']
        if type(radius) not in (int,float) or not math.isfinite(radius) or radius<=0:raise ValueError('Positive finite elbow radius required')
        if radius<=(nodes[name]['incidents'][0]['width_m']+2*thickness)/2:blocked.setdefault(name,[]).append('Radius does not exceed outside radial half-width')
    points={n['node']:n['point_m'] for n in junction['nodes']}
    for edge in schedule['flow_aggregation']['sections']:
        ends=[edge['from'],edge['to']];length=math.dist(points[ends[0]],points[ends[1]])
        trims={n:radii[n]['radius_m'] for n in ends if n in radii};remaining=length-math.fsum(trims.values())
        budgets.append(dict(section=edge['id'],source_centreline_m=length,declared_elbow_trims_m=trims,remaining_after_declared_elbows_m=remaining,other_fitting_trims_known=False))
        if remaining<=1e-8:
            for n in trims:blocked.setdefault(n,[]).append('Nonpositive two-end remaining length on '+edge['id'])
    active=wanted-set(blocked);by_id={d['id']:d for d in model['devices']};links=[];elevation=basis['elevation_m']['value']
    for edge in schedule['flow_aggregation']['sections']:
        device=by_id[edge['id']];a=np.array(points[edge['from']],dtype=float);b=np.array(points[edge['to']],dtype=float);a[2]=b[2]=elevation
        unit=(b-a)/np.linalg.norm(b-a);from_trim=radii[edge['from']]['radius_m'] if edge['from'] in active else 0.;to_trim=radii[edge['to']]['radius_m'] if edge['to'] in active else 0.
        a+=unit*from_trim;b-=unit*to_trim;axis=int(np.argmax(abs(unit)));origin=np.array(device['origin_m']);origin[axis]=min(a[axis],b[axis]);device['origin_m']=origin.tolist();device['size_m'][axis]=float(np.linalg.norm(b-a))
        for p,point in zip(device['ports'],(a,b)):p['offset_m']=(point-origin).tolist()
        device['properties'].update(AppliedStudyFromTrim_m=from_trim,AppliedStudyToTrim_m=to_trim,StudyStraightLength_m=device['size_m'][axis],AllFittingTrimsKnown=False)
        straight.specification(device)
    def axis_name(vector):
        for name,value in AXES.items():
            if np.allclose(vector,value,atol=1e-8,rtol=0):return name
        raise ValueError('Source elbow rays must be cardinal')
    for name in sorted(active):
        node=nodes[name];incoming=[r for r in node['incidents'] if r['role']=='incoming'];outgoing=[r for r in node['incidents'] if r['role']=='outgoing']
        if len(incoming)!=1 or len(outgoing)!=1:raise ValueError('One incoming/outgoing source arm required')
        first,last=incoming[0],outgoing[0];a=np.array(first['outward_unit_vector']);b=np.array(last['outward_unit_vector']);radius=radii[name]['radius_m']
        point=np.array(node['point_m'],dtype=float);point[2]=elevation;centre=point+radius*(a+b);u=-b;v=-a;normal=np.cross(u,v)
        width,height=first['width_m'],first['height_m'];ow=width+2*thickness;oh=height+2*thickness;extent=radius+ow/2
        lo=centre+np.minimum(0,u*extent)+np.minimum(0,v*extent)-abs(normal)*oh/2;hi=centre+np.maximum(0,u*extent)+np.maximum(0,v*extent)+abs(normal)*oh/2
        id='BEND-'+name
        device=dict(id=id,ifc_class='IfcDuctFitting',space='COORDINATION-ENVELOPE-NOT-ROOM',system='SOURCE-SUPPLY',source='native',body_shape=elbow.WALL,
            origin_m=lo.tolist(),size_m=(hi-lo).tolist(),arc_center_m=centre.tolist(),bend_axes=[axis_name(u),axis_name(v)],
            properties=dict(InternalWidth_m=width,InternalHeight_m=height,WallThickness_m=thickness,CenterlineRadius_m=radius,SourceNode=name,RadiusBasis=json.dumps(radii[name],sort_keys=True),DesignFlow_m3_s=first['flow_L_s']/1000),
            ports=[dict(id=port,direction=direction,offset_m=(p-lo).tolist(),source='native') for port,direction,p in (('in','SINK',point+radius*a),('out','SOURCE',point+radius*b))])
        elbow.specification(device);model['devices'].append(device)
        links.extend([dict(**{'from':first['section']+'.out','to':id+'.in'},source='native'),dict(**{'from':id+'.out','to':last['section']+'.in'},source='native')])
    model['connections']=links;model['geometry_scope']=elbow.SCOPE;model['name']='Partial Source Backbone - Finite Elbow Study'
    lo=[min(d['origin_m'][i] for d in model['devices']) for i in range(3)];hi=[max(d['origin_m'][i]+d['size_m'][i] for d in model['devices']) for i in range(3)]
    model['spaces'][0].update(origin_m=lo,size_m=[v-u for u,v in zip(lo,hi)]);bim.validate(model)
    return model,dict(candidate_elbow_nodes=sorted(wanted),authored_elbow_nodes=sorted(active),blocked_elbow_nodes=blocked,source_section_budgets=budgets,
        all_declared_elbows_fit=not blocked,remaining_nonelbow_junction_nodes=[n for n,node in nodes.items() if node['degree']>1 and n not in wanted],
        remaining_source_connection_nodes=[dict(node=n,requirement=node['connection_requirement']) for n,node in nodes.items() if node['degree']>1 and n not in active],
        full_fitting_trim_complete=False,design_accepted=False)


def inspect_saved(path,model):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.system as system
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.element as element
    saved=ifcopenshell.open(str(path));objects=saved.by_type('IfcDistributionElement');expected={d['id']:d for d in model['devices']}
    if len(objects)!=len(expected) or {o.Name for o in objects}!=set(expected) or saved.by_type('IfcSpace'):raise ValueError('Exact final body coverage without temporary spaces required')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);circular_geometry.configure(settings);ports={}
    for obj in objects:
        d=expected[obj.Name];module=elbow if d['body_shape']==elbow.WALL else straight;module.verify(obj,d,ifcopenshell.geom.create_shape(settings,obj))
        if obj.is_a()!=d['ifc_class']:raise ValueError('Final source element class differs')
        props=element.get_psets(obj)['BSA_DesignInputs']
        if not math.isclose(props['DesignFlow_m3_s'],d['properties']['DesignFlow_m3_s'],rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Final source flow differs')
        if {r.RelatingGroup.Name for r in obj.HasAssignments if r.is_a('IfcRelAssignsToGroup')}!={'SOURCE-SUPPLY'}:raise ValueError('Final ventilation system differs')
        container=element.get_container(obj)
        if container.Name!='COORDINATION-REFERENCE-PLANE':raise ValueError('Final source elements require reference-storey containment')
        owned={p.Name:p for p in system.get_ports(obj)}
        if set(owned)!={'in','out'}:raise ValueError('Exact owned port inventory required')
        for p in d['ports']:
            actual=owned[p['id']];frame=placement.get_local_placement(actual.ObjectPlacement);key=d['id']+'.'+p['id']
            if actual.FlowDirection!=p['direction'] or not np.allclose(frame[:3,3],np.array(d['origin_m'])+p['offset_m'],atol=1e-8,rtol=0) or not np.allclose(frame[:3,2],module.specification(d)['normals'][p['id']],atol=1e-8,rtol=0):raise ValueError('Final port direction,normal or position differs')
            ports[key]=actual
    actual_links={(system.get_port_element(r.RelatingPort).Name+'.'+r.RelatingPort.Name,system.get_port_element(r.RelatedPort).Name+'.'+r.RelatedPort.Name) for r in saved.by_type('IfcRelConnectsPorts')}
    expected_links={(r['from'],r['to']) for r in model['connections']}
    if actual_links!=expected_links or len(saved.by_type('IfcRelConnectsPorts'))!=len(expected_links) or len(saved.by_type('IfcDistributionPort'))!=len(ports):raise ValueError('Final actual IFC logical links differ')
    for a,b in expected_links:
        x=placement.get_local_placement(ports[a].ObjectPlacement);y=placement.get_local_placement(ports[b].ObjectPlacement)
        if not np.allclose(x[:3,3],y[:3,3],atol=1e-8,rtol=0) or not np.allclose(x[:3,2],-y[:3,2],atol=1e-8,rtol=0):raise ValueError('Actual linked native cap planes are not coincident and opposed')
    return dict(body_count=len(objects),owned_ports=len(ports),actual_links=len(actual_links),coincident_opposed_linked_ports=True,native_geometry_pass=True,complete_network=False)


def run(plan,workflow,native_task,basis_path,radii_path,out):
    from .delivery import context
    from .duct_junction_review import from_workflow
    from .workflow import verify
    from . import duct_backbone_ifc
    import ifcopenshell
    import ifcopenshell.api as api
    plan,workflow,basis_path,radii_path,out=[Path(p).resolve() for p in (plan,workflow,basis_path,radii_path,out)]
    root=Path(__file__).resolve().parents[2]
    if out.exists() or not out.is_relative_to(root) or out.is_relative_to(workflow) or workflow.is_relative_to(out) or any(out==p or out in p.parents for p in (plan,basis_path,radii_path)):raise ValueError('New repository output separate from all source files required')
    _,record,integrity=context(plan,workflow)
    if not integrity['integrity_pass']:raise ValueError('Current source workflow required')
    pins={str(p):digest(p) for p in (plan,workflow/'workflow.json',basis_path,radii_path)}
    for values in (record['inputs'],record.get('runtime_inputs',{}),{str(workflow/n):sha for n,sha in record['artifact_hashes'].items()}):pins.update(values)
    for module in (bim,straight,elbow,circular_geometry,duct_backbone_ifc):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    junction=from_workflow(plan,workflow,native_task,out/'junction-review.json');pins.update(junction['inputs'])
    schedule=json.loads((workflow/junction['lineage'][-1]/'results.json').read_text());basis=json.loads(basis_path.read_text());radii=json.loads(radii_path.read_text())
    model,fit=compile_model(junction,schedule,basis,radii);source=out/'model-input.json';source.write_text(json.dumps(model,indent=2))
    bim.run(source,out/'bim')
    file=ifcopenshell.open(str(out/'bim/model.ifc'));storey=file.by_type('IfcBuildingStorey')[0]
    if file.by_type('IfcDuctFitting'):api.run('spatial.assign_container',file,products=file.by_type('IfcDuctFitting'),relating_structure=storey)
    intermediate=out/'fittings-recontained.ifc';file.write(str(intermediate));target=out/'Supply Backbone.ifc';export_storey(intermediate,target)
    check=inspect_saved(target,model)
    if any(digest(Path(p))!=sha for p,sha in pins.items()) or not verify(workflow)['integrity_pass']:raise ValueError('Elbow source or method changed during authoring')
    report=dict(inputs=pins,fit=fit,saved_checks=check,ifc_sha256=digest(target),original_requirements=record['requirements'],design_accepted=False,
        scope='Partial finite elbow scenario with trimmed straight ends at supported fitting nodes only. Blocked corners and all nonelbow junctions remain;no complete physical topology,products,installed geometry,pressure or full engineering acceptance.')
    report['artifact_hashes']={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'elbow-backbone.json').write_text(json.dumps(report,indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','workflow','native_task','basis','radii'):p.add_argument(name)
    p.add_argument('--out',required=True);a=p.parse_args();r=run(a.plan,a.workflow,a.native_task,a.basis,a.radii,a.out)
    print(len(r['fit']['authored_elbow_nodes']),'finite elbows;',len(r['fit']['blocked_elbow_nodes']),'blocked;full design pending')
