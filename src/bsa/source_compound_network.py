"""Integrate an explicit source compound revision, retaining all source obligations."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import numpy as np
from . import source_compound_junction as candidate,source_cross_network as previous
from . import source_tee_network as network,compound_junction as junction,bim,duct_elbow_backbone as backbone
from . import rectangular_geometry as straight
from .tee_geometry import stable_guid
from .rectangular_tee_transitions import relative_placement
from .cli import digest
from .workspace import allowed


def compile_model(original,fit):
    model=copy.deepcopy(original);absorbed=set(fit['absorbed_straight_sections']);devices={d['id']:d for d in model['devices']}
    if len(absorbed)!=2 or any(s not in devices or devices[s]['ifc_class']!='IfcDuctSegment' for s in absorbed):raise ValueError('Exactly declared source straight bodies must be absorbed')
    model['devices']=[d for d in model['devices'] if d['id'] not in absorbed]
    removed=[r for r in model['connections'] if r['from'].split('.')[0] in absorbed or r['to'].split('.')[0] in absorbed]
    if len(removed)!=1 or removed[0]['from']!=fit['direct_inlet_source_port']:raise ValueError('Only the declared direct inlet connection may be replaced')
    model['connections']=[r for r in model['connections'] if r not in removed];budgets=[]
    for row in fit['external_interfaces']:
        if row['port']!='in' or row['section'] in absorbed:raise ValueError('Retained source inlet endpoint required')
        d=devices[row['section']];origin=np.array(d['origin_m']);points={p['id']:origin+p['offset_m'] for p in d['ports']};vector=points['out']-points['in'];length=float(np.linalg.norm(vector));remaining=length-row['reach_m']
        if remaining<fit['inherited_minimum_remainder_m']-1e-8 or not np.isclose(remaining,row['remaining_straight_m'],atol=1e-8,rtol=0):raise ValueError('Retained compound endpoint budget differs')
        points['in']+=row['reach_m']*vector/length;axis=int(np.argmax(abs(vector)));origin[axis]=min(points['in'][axis],points['out'][axis]);d['origin_m']=origin.tolist();d['size_m'][axis]=remaining
        for p in d['ports']:p['offset_m']=(points[p['id']]-origin).tolist()
        d['properties'].update(AppliedCompoundFromTrim_m=row['reach_m'],StudyStraightLength_m=remaining,AllFittingTrimsKnown=True)
        straight.specification(d);budgets.append(dict(section=d['id'],before_compound_length_m=length,compound_from_trim_m=row['reach_m'],remaining_m=remaining,minimum_remainder_m=fit['inherited_minimum_remainder_m']))
    model['name']='Source Network - Declared Compound Junction Revision';bim.validate(model);return model,budgets


def compound_links(expected,spec,fit):
    owner=stable_guid(spec,'IfcDuctFitting',junction.KEY);result=[];bindings=[dict(compound_port='upper',source_port=fit['direct_inlet_source_port'],source_to_compound=True)]
    bindings += [dict(compound_port=r['compound_port'],source_port=r['section']+'.'+r['port'],source_to_compound=False) for r in fit['external_interfaces']]
    frames=junction.port_frames(spec)
    for binding in bindings:
        name,port=binding['source_port'].rsplit('.',1);objs=[g for g,o in expected['objects'].items() if o['name']==name];other=[g for g,p in expected['ports'].items() if p['owner']==owner and p['name']==binding['compound_port']]
        if len(objs)!=1 or len(other)!=1:raise ValueError('Unique compound/native source body required')
        source=[g for g,p in expected['ports'].items() if p['owner']==objs[0] and p['name']==port]
        if len(source)!=1:raise ValueError('Unique compound interface source port required')
        a,b=(source[0],other[0]) if binding['source_to_compound'] else (other[0],source[0]);p,q=[expected['ports'][g] for g in (a,b)];x,y=[np.array(r['frame']) for r in (p,q)]
        if p['direction']!='SOURCE' or q['direction']!='SINK' or not np.allclose(x[:3,3],y[:3,3],atol=1e-8,rtol=0) or not np.allclose(x[:3,2],-y[:3,2],atol=1e-8,rtol=0):raise ValueError('Compound directed native interface planes differ')
        # Source straight width axes come from the native body; bend width from its face frame.
        source_obj=expected['objects'][objs[0]];source_frame=np.array(source_obj['frame'])
        if source_obj['ifc_class']=='IfcDuctSegment':
            cap=frames[binding['compound_port']]
            if any(not np.isclose(abs(np.dot(source_frame[:3,i],cap[:3,i])),1,atol=1e-8,rtol=0) for i in (0,1)):raise ValueError('Compound retained rectangular section roll differs')
        result.append((a,b))
    return result


def prepare(source,folder):
    report=json.loads((source/'compound.json').read_text());old=Path(report['source']);old_record=json.loads((old/'network.json').read_text());cross_source=Path(old_record['source']);data=previous.prepare(cross_source,folder/'parent');old_model=data['model']
    if old_model!=json.loads((old/'model-input.json').read_text()):raise ValueError('Original source model replay differs')
    _,spec,fit=candidate.prepare(old,json.loads(Path(report['policy']).read_text()),folder/'compound')
    model,budgets=compile_model(old_model,fit)
    return dict(report=report,spec=spec,fit=fit,model=model,budgets=budgets,previous=data,cross_source=cross_source)


def paths(source,out,data):return previous.source_paths(data['cross_source'],out,data['previous'])+[source/'native/junction.ifc']


def expected_model(sources,data):
    expected,libraries=network.snapshot(sources);old=data['previous'];links=network.external_links(expected,old['tee_interfaces'],old['tee_rows'])+previous.cross_links(expected,old['interfaces'],old['rows'])+compound_links(expected,data['spec'],data['fit'])
    expected['links']=sorted(set(map(tuple,expected['links']))|set(links));return expected,libraries


def inspect(path,expected):
    check=network.inspect(path,expected);incoming={};outgoing={}
    for a,b in expected['links']:
        first,last=[expected['ports'][g]['owner'] for g in (a,b)]
        if first==last or last in incoming:raise ValueError('Compound source product graph is not a directed tree')
        incoming[last]=first;outgoing.setdefault(first,[]).append(last)
    roots=set(expected['objects'])-set(incoming)
    if len(roots)!=1 or len(expected['links'])!=len(expected['objects'])-1:raise ValueError('Exactly one complete represented source product tree required')
    queue=list(roots);seen=set()
    for owner in queue:
        if owner in seen:raise ValueError('Cycle in compound source network')
        seen.add(owner);queue.extend(outgoing.get(owner,[]))
    if seen!=set(expected['objects']):raise ValueError('Compound source product graph disconnected')
    check['one_connected_directed_product_tree']=True;check['source_connection_coverage_complete']=True
    return check


def merge(sources,target,data):
    import ifcopenshell.api as api
    import ifcopenshell.util.system as system
    expected,libraries=expected_model(sources,data);file=libraries[0];storey=file.by_type('IfcBuildingStorey')[0];group=file.by_type('IfcDistributionSystem')[0];count=len(file.by_type('IfcRelConnectsPorts'));groups=len(file.by_type('IfcDistributionSystem'))
    for library in libraries[1:]:
        reuse={}
        for obj in library.by_type('IfcDistributionElement'):
            added=api.run('project.append_asset',file,library=library,element=obj,reuse_identities=reuse,assume_asset_uniqueness_by_name=False);world=np.array(expected['objects'][obj.GlobalId]['frame']);added.ObjectPlacement=relative_placement(file,world,None)
            for p in system.get_ports(added):p.ObjectPlacement=relative_placement(file,np.linalg.inv(world)@np.array(expected['ports'][p.GlobalId]['frame']),added.ObjectPlacement)
            api.run('spatial.assign_container',file,products=[added],relating_structure=storey);api.run('system.assign_system',file,products=[added],system=group)
    if len(file.by_type('IfcRelConnectsPorts'))!=count or len(file.by_type('IfcDistributionSystem'))!=groups:raise ValueError('Unexpected imported connection/system')
    ports={p.GlobalId:p for p in file.by_type('IfcDistributionPort')};present={(r.RelatingPort.GlobalId,r.RelatedPort.GlobalId) for r in file.by_type('IfcRelConnectsPorts')}
    for a,b in expected['links']:
        if (a,b) not in present:api.run('system.connect_port',file,port1=ports[a],port2=ports[b],direction='SOURCE')
    file.write(str(target));return inspect(target,expected)


def methods():return [Path(__file__),Path(candidate.__file__),Path(previous.__file__),Path(network.__file__)]


def run(source,out):
    source,out=[Path(p).resolve() for p in (source,out)]
    if not all(allowed(p) for p in (source,out)) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out):raise ValueError('Fresh selected workspace outside source required')
    candidate.verify(source);pins={str(p):digest(p) for p in [source/'compound.json',*methods()]};data=prepare(source,out/'inputs');path=out/'model-input.json';path.write_text(json.dumps(data['model'],indent=2));bim.run(path,out/'bim')
    import ifcopenshell
    import ifcopenshell.api as api
    file=ifcopenshell.open(str(out/'bim/model.ifc'));api.run('spatial.assign_container',file,products=file.by_type('IfcDuctFitting'),relating_structure=file.by_type('IfcBuildingStorey')[0]);file.write(str(out/'recontained.ifc'));backbone.export_storey(out/'recontained.ifc',out/'Trimmed Backbone.ifc');trimmed=backbone.inspect_saved(out/'Trimmed Backbone.ifc',data['model']);checks=merge(paths(source,out,data),out/'Supply Network.ifc',data)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Compound network source/method changed')
    report=dict(source=str(source),inputs=pins,checks=checks,trimmed_checks=trimmed,fit=data['fit'],budgets=data['budgets'],original_requirement_ids=data['report']['original_requirement_ids'],original_network_modified=False,complete_network=False,design_accepted=False,scope='Connected represented rigid source network with explicit compound revision; original separate-core failures preserved, raw clashes, pressure/loss, products, architecture/equipment and full engineering acceptance remain pending')
    report['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()};(out/'network.json').write_text(json.dumps(report,indent=2));return report


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected workspace required')
    report=json.loads((out/'network.json').read_text());source=Path(report['source']);candidate.verify(source)
    if report['inputs']!={str(p):digest(p) for p in [source/'compound.json',*methods()]} or any(report[k] is not False for k in ('original_network_modified','complete_network','design_accepted')):raise ValueError('Compound network input/method/status differs')
    for name,sha in report['artifacts'].items():
        p=(out/name).resolve()
        if not p.is_relative_to(out) or digest(p)!=sha:raise ValueError('Compound network artifact changed')
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='compound-network-audit-') as folder:
        data=prepare(source,Path(folder))
        if data['model']!=json.loads((out/'model-input.json').read_text()) or report['fit']!=data['fit'] or report['budgets']!=data['budgets'] or report['original_requirement_ids']!=data['report']['original_requirement_ids']:raise ValueError('Compound network source replay differs')
        if backbone.inspect_saved(out/'Trimmed Backbone.ifc',data['model'])!=report['trimmed_checks']:raise ValueError('Compound trimmed native backbone differs')
        expected,_=expected_model(paths(source,out,data),data);check=inspect(out/'Supply Network.ifc',expected)
        if check!=report['checks']:raise ValueError('Compound merged native replay differs')
    return dict(integrity_pass=True,**check)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('source');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args();r=run(a.source,a.out)['checks'] if a.command=='run' else verify(a.out);print(json.dumps(r,indent=2));raise SystemExit(2)
