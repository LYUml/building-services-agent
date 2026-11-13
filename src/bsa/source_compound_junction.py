"""Source-bound adjacent tee/cross compound candidate; original route remains immutable."""
import argparse
import json
import math
from pathlib import Path
import tempfile
import uuid
import numpy as np
from . import source_cross_network as parent,compound_junction as native
from .tee_geometry import stable_guid
from .cli import digest
from .workspace import allowed


def compile_model(junction,basis,model,policy,minimum):
    fields={'upper_node','lower_node','shared_section','inlet_section','outlet_section','branch_reaches_m','outlet_reach_m','maximum_included_trunk_angle_degrees','classification','source'}
    if not isinstance(policy,dict) or set(policy)!=fields or policy['classification'] not in ('given','assumed','secondary_transcription') or not isinstance(policy['source'],str) or not policy['source'].strip():raise ValueError('Explicit classified compound scenario policy required')
    if type(policy['outlet_reach_m']) not in (int,float) or not math.isfinite(policy['outlet_reach_m']) or policy['outlet_reach_m']<=0 or type(policy['maximum_included_trunk_angle_degrees']) not in (int,float) or not 0<policy['maximum_included_trunk_angle_degrees']<90:raise ValueError('Explicit positive outlet reach and trunk angle bound required')
    nodes={n['node']:n for n in junction['nodes']};upper=nodes[policy['upper_node']];lower=nodes[policy['lower_node']]
    if upper['connection_requirement']!='unequal_section_tee_required' or lower['connection_requirement']!='multi_branch_connection_required' or upper['degree']!=3 or lower['degree']!=4:raise ValueError('Original adjacent three/four-arm source nodes required')
    u={r['section']:r for r in upper['incidents']};l={r['section']:r for r in lower['incidents']};shared=policy['shared_section'];inlet=policy['inlet_section'];outlet=policy['outlet_section']
    if set(u)&set(l)!={shared} or inlet not in u or outlet not in l or u[inlet]['role']!='incoming' or u[shared]['role']!='outgoing' or l[shared]['role']!='incoming' or l[outlet]['role']!='outgoing':raise ValueError('Directed adjacent source inlet/shared/outlet binding required')
    if not np.allclose(u[inlet]['outward_unit_vector'],[0,1,0],atol=1e-8,rtol=0) or not np.allclose(l[outlet]['outward_unit_vector'],[0,-1,0],atol=1e-8,rtol=0) or not math.isclose(upper['point_m'][0],lower['point_m'][0],abs_tol=1e-8,rel_tol=0) or upper['point_m'][1]<=lower['point_m'][1]:raise ValueError('Supported vertical-plan source trunk with opposed through arms required')
    branches=[(upper,sid,r) for sid,r in u.items() if sid not in (shared,inlet)]+[(lower,sid,r) for sid,r in l.items() if sid not in (shared,outlet)]
    if not isinstance(policy['branch_reaches_m'],dict) or set(policy['branch_reaches_m'])!={sid for _,sid,_ in branches}:raise ValueError('Every source branch needs explicit compound reach')
    devices={d['id']:d for d in model['devices']};incoming=devices[inlet];outgoing=devices[outlet];origin=np.array(lower['point_m'][:2]+[basis['elevation_m']['value']]);points={p['id']:np.array(incoming['origin_m'])+p['offset_m'] for p in incoming['ports']};upper_y=float(points['in'][1]-origin[1]);node_y=float(upper['point_m'][1]-origin[1])
    # The inlet short straight is deliberately absorbed up to its already verified elbow cap.
    inlet_link=[r for r in model['connections'] if r['to']==inlet+'.in']
    if len(inlet_link)!=1 or not inlet_link[0]['from'].startswith('BEND-'):raise ValueError('One existing native elbow-to-inlet cap required for direct compound connection')
    if not upper_y>node_y>0 or not np.allclose(points['out'],np.array(upper['point_m'][:2]+[origin[2]]),atol=1e-8,rtol=0):raise ValueError('Current inlet endpoints differ from original source node')
    shared_dims=[u[shared]['width_m'],u[shared]['height_m']]
    if not np.allclose(shared_dims,[l[shared]['width_m'],l[shared]['height_m']],atol=1e-10,rtol=0):raise ValueError('Shared source profile differs')
    rows=[(-policy['outlet_reach_m'],l[outlet]['width_m'],l[outlet]['height_m']),(0,*shared_dims),(node_y,*shared_dims),(upper_y,u[inlet]['width_m'],u[inlet]['height_m'])]
    stations=[dict(y_m=y,width_m=w,height_m=h) for y,w,h in rows];branch_specs=[];fits=[]
    for node,sid,incident in branches:
        ray=np.array(incident['outward_unit_vector']);reach=policy['branch_reaches_m'][sid]
        if incident['role']!='outgoing' or not np.allclose(abs(ray),[1,0,0],atol=1e-8,rtol=0) or type(reach) not in (int,float) or not math.isfinite(reach) or reach<=0:raise ValueError('Explicit outgoing lateral takeoff and reach required')
        branch_specs.append(dict(id=sid,y_m=float(node['point_m'][1]-origin[1]),side=int(ray[0]),width_m=incident['width_m'],height_m=incident['height_m'],reach_m=reach));device=devices[sid];length=math.dist(*[np.array(device['origin_m'])+p['offset_m'] for p in device['ports']]);remaining=length-reach
        if remaining<minimum-1e-8:raise ValueError('Compound branch exceeds inherited straight budget on '+sid)
        fits.append(dict(section=sid,port='in',compound_port=sid,reach_m=reach,remaining_straight_m=remaining))
    length=math.dist(*[np.array(outgoing['origin_m'])+p['offset_m'] for p in outgoing['ports']]);remaining=length-policy['outlet_reach_m']
    if remaining<minimum-1e-8:raise ValueError('Compound outlet exceeds inherited straight budget')
    fits.append(dict(section=outlet,port='in',compound_port='lower',reach_m=policy['outlet_reach_m'],remaining_straight_m=remaining))
    angles=[math.degrees(2*math.atan(max(abs(b['width_m']-a['width_m']),abs(b['height_m']-a['height_m']))/(2*(b['y_m']-a['y_m'])))) for a,b in zip(stations,stations[1:])]
    if max(angles)>policy['maximum_included_trunk_angle_degrees']+1e-8:raise ValueError('Explicit compound trunk angle bound exceeded')
    source='Original adjacent nodes '+upper['node']+'/'+lower['node']+'; '+policy['source']+'; classified construction '+json.dumps(basis,sort_keys=True)
    spec=dict(project_uuid=str(uuid.uuid5(uuid.UUID(basis['project_uuid']),'SOURCE-COMPOUND:'+upper['node']+':'+lower['node'])),source=source,classification=policy['classification'],placement=dict(source='Original source XY and explicit study elevation',origin_m=origin.tolist(),rotation=np.eye(3).tolist()),wall_thickness_m=basis['wall_thickness_m']['value'],stations=stations,branches=branch_specs,port_directions=dict(lower='SOURCE',upper='SINK',**{b['id']:'SOURCE' for b in branch_specs}))
    native.validate(spec);frames=native.port_frames(spec)
    if not np.allclose(frames['upper'][:3,3],points['in'],atol=1e-8,rtol=0):raise ValueError('Compound direct inlet differs from saved elbow-side cap')
    for fit in fits:
        sid=fit['section'];node,incident=next(((node,r) for node in (upper,lower) for r in node['incidents'] if r['section']==sid));point=np.array(node['point_m'][:2]+[origin[2]])+fit['reach_m']*np.array(incident['outward_unit_vector'])
        if not np.allclose(frames[fit['compound_port']][:3,3],point,atol=1e-8,rtol=0):raise ValueError('Compound external end differs from original source ray')
    return spec,dict(absorbed_straight_sections=[inlet,shared],direct_inlet_source_port=inlet_link[0]['from'],external_interfaces=fits,inherited_minimum_remainder_m=minimum,trunk_included_angles_degrees=angles,
        source_nodes=[upper['node'],lower['node']],source_routes_preserved=True,source_profiles_at_external_caps_preserved=True,
        internal_profile_change='Original short inlet straight replaced by explicit taper; shared source section profile retained inside compound body',complete_network=False,design_accepted=False)


def prepare(source,policy,folder):
    record=json.loads((source/'network.json').read_text());cross_source=Path(record['source']);data=parent.prepare(cross_source,folder/'parent');cross_result=data['result'];tee_record=json.loads((data['tee_source']/'tee-candidates.json').read_text());selection=Path(tee_record['source']['selection']);selected=json.loads((selection/'selection.json').read_text());junction=json.loads((selection/'junction.json').read_text());basis=json.loads(Path(selected['source']['basis']).read_text())
    if data['model']!=json.loads((source/'model-input.json').read_text()):raise ValueError('Parent source model replay differs')
    spec,fit=compile_model(junction,basis,data['model'],policy,selected['policy']['minimum_remainder_m']['value'])
    if set(fit['source_nodes'])!=set(record['unresolved_nodes']):raise ValueError('Compound scenario must preserve exact remaining source-node coverage')
    return record,spec,fit


def methods():return [Path(__file__),Path(native.__file__),Path(parent.__file__)]


def run(source,policy,out):
    source,policy,out=[Path(p).resolve() for p in (source,policy,out)]
    if not all(allowed(p) for p in (source,policy,out)) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out) or out==policy or out in policy.parents:raise ValueError('Fresh selected workspace output outside sources required')
    parent.verify(source);pins={str(p):digest(p) for p in [source/'network.json',policy,*methods()]};record,spec,fit=prepare(source,json.loads(policy.read_text()),out/'inputs');path=out/'junction-spec.json';path.write_text(json.dumps(spec,indent=2));result=native.run(path,out/'native')
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Compound source/method changed')
    report=dict(source=str(source),policy=str(policy),inputs=pins,fit=fit,native_checks=result['checks'],original_requirement_ids=record['original_requirement_ids'],original_network_modified=False,complete_network=False,design_accepted=False,scope='Source-bound isolated compound junction candidate; absorbed short sections explicitly identified, no network merge or physical/product/pressure approval')
    report['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()};(out/'compound.json').write_text(json.dumps(report,indent=2));return report


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected workspace required')
    report=json.loads((out/'compound.json').read_text());source=Path(report['source']);policy=Path(report['policy']);parent.verify(source)
    if report['inputs']!={str(p):digest(p) for p in [source/'network.json',policy,*methods()]} or any(report[k] is not False for k in ('original_network_modified','complete_network','design_accepted')):raise ValueError('Compound input/method/status differs')
    for name,sha in report['artifacts'].items():
        path=(out/name).resolve()
        if not path.is_relative_to(out) or digest(path)!=sha:raise ValueError('Compound artifact changed')
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='compound-audit-') as folder:
        record,spec,fit=prepare(source,json.loads(policy.read_text()),Path(folder))
        if spec!=json.loads((out/'junction-spec.json').read_text()) or fit!=report['fit'] or record['original_requirement_ids']!=report['original_requirement_ids'] or native.inspect(out/'native/junction.ifc',spec)!=report['native_checks']:raise ValueError('Compound source/native replay differs')
    return dict(integrity_pass=True,ports=report['native_checks']['ports'],absorbed_sections=report['fit']['absorbed_straight_sections'],complete_network=False,design_accepted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('source');a.add_argument('policy');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args();r=run(a.source,a.policy,a.out)['native_checks'] if a.command=='run' else verify(a.out);print(json.dumps(r,indent=2));raise SystemExit(2)
