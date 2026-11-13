"""Integrate verified source crosses with the existing partial tee/elbow network."""
import argparse
import json
from pathlib import Path
import tempfile
import numpy as np
from . import source_cross_candidates as candidates,source_tee_network as network
from . import rectangular_cross as cross,rectangular_cross_transitions as composition
from . import rectangular_transition as transition,bim,duct_elbow_backbone as backbone
from .rectangular_tee_transitions import relative_placement
from .tee_geometry import stable_guid
from .cli import digest
from .workspace import allowed


def compile_model(original,junction,selected,rows,blocked):
    adapted={name:dict(fit=dict(arms=row['fit'])) for name,row in rows.items()}
    model,interfaces,budgets=network.compile_model(original,junction,selected,adapted,blocked)
    originals={d['id']:d for d in original['devices']}
    for d in model['devices']:
        if d['ifc_class']!='IfcDuctSegment':continue
        props=d['properties'];before=originals[d['id']]['properties']
        for end in ('From','To'):
            key='AppliedTee'+end+'Trim_m';props['AppliedCross'+end+'Trim_m']=props.pop(key)
            if key in before:props[key]=before[key]
    for row in budgets:
        row['before_cross_length_m']=row.pop('before_tee_length_m')
        row['from_cross_trim_m']=row.pop('from_tee_trim_m');row['to_cross_trim_m']=row.pop('to_tee_trim_m')
    model['name']='Partial Source Network - Tee and Cross Integration'
    return model,interfaces,budgets


def cross_links(expected,interfaces,rows):
    result=[]
    for r in interfaces:
        row=rows[r['node']];spec=row['data']['cross'];children=composition.children(spec,row['data']['arms']);arm=r['arm']
        owner=stable_guid(children[arm],'IfcDuctFitting',transition.KEY) if arm in children else stable_guid(spec,'IfcDuctFitting',cross.KEY)
        name='end' if arm in children else arm
        segment=[g for g,o in expected['objects'].items() if o['name']==r['section'] and o['ifc_class']=='IfcDuctSegment']
        fitting=[g for g,p in expected['ports'].items() if p['owner']==owner and p['name']==name]
        if len(segment)!=1 or len(fitting)!=1:raise ValueError('Unique cross/source body identity required')
        section_ports=[g for g,p in expected['ports'].items() if p['owner']==segment[0] and p['name']==r['port']]
        if len(section_ports)!=1:raise ValueError('Unique source endpoint required')
        a,b=(section_ports[0],fitting[0]) if r['port']=='out' else (fitting[0],section_ports[0]);first,last=[expected['ports'][g] for g in (a,b)];x,y=[np.array(p['frame']) for p in (first,last)]
        if first['direction']!='SOURCE' or last['direction']!='SINK' or not np.allclose(x[:3,3],y[:3,3],atol=1e-8,rtol=0) or not np.allclose(x[:3,2],-y[:3,2],atol=1e-8,rtol=0):raise ValueError('Cross/source cap correspondence differs')
        s=np.array(expected['objects'][segment[0]]['frame']);f=np.array(expected['ports'][fitting[0]]['frame'])
        if any(not np.isclose(abs(np.dot(s[:3,i],f[:3,i])),1,atol=1e-8,rtol=0) for i in (0,1)):raise ValueError('Cross/source rectangular roll differs')
        result.append((a,b))
    return result


def prepare(source,folder):
    result=json.loads((source/'cross-candidates.json').read_text());parent=Path(result['source']);parent_record=json.loads((parent/'network.json').read_text());tee_source=Path(parent_record['source'])
    _,selection,tee_rows,tee_blocked,original,tee_interfaces,_=network.prepare(tee_source,folder/'tee')
    if original!=json.loads((parent/'model-input.json').read_text()):raise ValueError('Reconstructed parent native input differs')
    _,rows,_,blocked=candidates.prepare(parent,json.loads(Path(result['policy']).read_text()),folder/'cross')
    junction=json.loads((selection/'junction.json').read_text());selected=json.loads((selection/'selection.json').read_text())
    model,interfaces,budgets=compile_model(original,junction,selected,rows,blocked)
    remaining=dict(parent_record['blocked_nodes']);remaining.update(blocked)
    return dict(result=result,parent=parent,tee_source=tee_source,tee_rows=tee_rows,tee_blocked=tee_blocked,tee_interfaces=tee_interfaces,
        rows=rows,blocked=blocked,model=model,interfaces=interfaces,budgets=budgets,remaining=remaining)


def source_paths(source,out,data):
    return [out/'Trimmed Backbone.ifc']+[data['tee_source']/'models'/r['directory']/'assembly.ifc' for name,r in data['tee_rows'].items() if name not in data['tee_blocked']]+[source/'models'/r['directory']/'assembly.ifc' for name,r in data['rows'].items() if name not in data['blocked']]


def expected_model(paths,data):
    expected,libraries=network.snapshot(paths)
    links=network.external_links(expected,data['tee_interfaces'],data['tee_rows'])+cross_links(expected,data['interfaces'],data['rows'])
    expected['links']=sorted(set(map(tuple,expected['links']))|set(links));return expected,libraries


def merge(paths,target,data):
    import ifcopenshell.api as api
    import ifcopenshell.util.system as system
    expected,libraries=expected_model(paths,data);file=libraries[0];storey=file.by_type('IfcBuildingStorey')[0];group=file.by_type('IfcDistributionSystem')[0]
    original_links=len(file.by_type('IfcRelConnectsPorts'));original_groups=len(file.by_type('IfcDistributionSystem'))
    for library in libraries[1:]:
        reuse={}
        for obj in library.by_type('IfcDistributionElement'):
            added=api.run('project.append_asset',file,library=library,element=obj,reuse_identities=reuse,assume_asset_uniqueness_by_name=False);world=np.array(expected['objects'][obj.GlobalId]['frame']);added.ObjectPlacement=relative_placement(file,world,None)
            for p in system.get_ports(added):p.ObjectPlacement=relative_placement(file,np.linalg.inv(world)@np.array(expected['ports'][p.GlobalId]['frame']),added.ObjectPlacement)
            api.run('spatial.assign_container',file,products=[added],relating_structure=storey);api.run('system.assign_system',file,products=[added],system=group)
    if len(file.by_type('IfcRelConnectsPorts'))!=original_links or len(file.by_type('IfcDistributionSystem'))!=original_groups:raise ValueError('Unexpected imported groups/links')
    ports={p.GlobalId:p for p in file.by_type('IfcDistributionPort')};present={(r.RelatingPort.GlobalId,r.RelatedPort.GlobalId) for r in file.by_type('IfcRelConnectsPorts')}
    for a,b in expected['links']:
        if (a,b) not in present:api.run('system.connect_port',file,port1=ports[a],port2=ports[b],direction='SOURCE')
    file.write(str(target));return network.inspect(target,expected)


def methods():
    return [Path(__file__),Path(network.__file__),Path(candidates.__file__)]


def run(source,out):
    source,out=[Path(p).resolve() for p in (source,out)]
    if not all(allowed(p) for p in (source,out)) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out):raise ValueError('Fresh selected workspace outside source required')
    candidates.verify(source);pins={str(p):digest(p) for p in [source/'cross-candidates.json',*methods()]};data=prepare(source,out/'inputs');path=out/'model-input.json';path.write_text(json.dumps(data['model'],indent=2));bim.run(path,out/'bim')
    import ifcopenshell
    import ifcopenshell.api as api
    file=ifcopenshell.open(str(out/'bim/model.ifc'));api.run('spatial.assign_container',file,products=file.by_type('IfcDuctFitting'),relating_structure=file.by_type('IfcBuildingStorey')[0]);file.write(str(out/'recontained.ifc'));backbone.export_storey(out/'recontained.ifc',out/'Trimmed Backbone.ifc');trimmed=backbone.inspect_saved(out/'Trimmed Backbone.ifc',data['model'])
    checks=merge(source_paths(source,out,data),out/'Supply Network.ifc',data)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Cross integration source/method changed')
    report=dict(source=str(source),inputs=pins,checks=checks,trimmed_checks=trimmed,interfaces=data['interfaces'],budgets=data['budgets'],unresolved_nodes=data['remaining'],original_requirement_ids=data['result']['original_requirement_ids'],original_network_modified=False,complete_network=False,design_accepted=False,scope='Partial source tee/cross integration; remaining blocked nodes, raw coordination, pressure, products and full engineering acceptance remain pending')
    report['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()};(out/'network.json').write_text(json.dumps(report,indent=2));return report


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected workspace required')
    report=json.loads((out/'network.json').read_text());source=Path(report['source']);candidates.verify(source)
    if report['inputs']!={str(p):digest(p) for p in [source/'cross-candidates.json',*methods()]} or any(report[k] is not False for k in ('original_network_modified','complete_network','design_accepted')):raise ValueError('Cross network source/method/status differs')
    for name,sha in report['artifacts'].items():
        path=(out/name).resolve()
        if not path.is_relative_to(out) or digest(path)!=sha:raise ValueError('Cross network artifact differs')
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='cross-network-audit-') as folder:
        data=prepare(source,Path(folder))
        if data['model']!=json.loads((out/'model-input.json').read_text()) or any(report[k]!=data[k] for k in ('interfaces','budgets')) or report['unresolved_nodes']!=data['remaining'] or report['original_requirement_ids']!=data['result']['original_requirement_ids']:raise ValueError('Cross network source replay differs')
        if backbone.inspect_saved(out/'Trimmed Backbone.ifc',data['model'])!=report['trimmed_checks']:raise ValueError('Native trimmed backbone differs')
        expected,_=expected_model(source_paths(source,out,data),data);check=network.inspect(out/'Supply Network.ifc',expected)
        if check!=report['checks']:raise ValueError('Merged native checks differ')
    return dict(integrity_pass=True,**check)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('source');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args();r=run(a.source,a.out)['checks'] if a.command=='run' else verify(a.out);print(json.dumps(r,indent=2));raise SystemExit(2)
