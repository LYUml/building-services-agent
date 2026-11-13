"""Bind every original four-arm source node to explicit cross/transition candidates."""
import argparse
from itertools import combinations
import json
import math
from pathlib import Path
import tempfile
import uuid
import numpy as np
from . import rectangular_cross as cross,rectangular_cross_transitions as composition
from . import rectangular_transition as transition,source_tee_network as network
from .cli import digest
from .workspace import allowed


def compile_node(node,basis,row):
    fields={'core_section_m','main_half_length_m','branch_length_m','start_length_m','end_length_m','upstream_angle_degrees','classification','source','transition_method'}
    if not isinstance(row,dict) or set(row)!=fields or row['classification'] not in ('given','assumed','secondary_transcription') or not isinstance(row['source'],str) or not row['source'].strip():raise ValueError('Explicit classified cross policy required')
    if not isinstance(row['core_section_m'],list) or len(row['core_section_m'])!=2:raise ValueError('Explicit core width and height required')
    values=row['core_section_m']+[row[k] for k in ('main_half_length_m','branch_length_m','start_length_m','end_length_m','upstream_angle_degrees')]
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values) or row['upstream_angle_degrees']>=90 or row['transition_method'] not in ('explicit_station_brep','upstream_mep_shape'):raise ValueError('Finite explicit cross geometry/method required')
    incidents=node['incidents']
    if node['connection_requirement']!='multi_branch_connection_required' or node['degree']!=4 or len(incidents)!=4 or len({i['section'] for i in incidents})!=4:raise ValueError('Original four-arm source node required')
    incoming=[r for r in incidents if r['role']=='incoming'];outgoing=[r for r in incidents if r['role']=='outgoing']
    if len(incoming)!=1 or len(outgoing)!=3:raise ValueError('One incoming and three outgoing source arms required')
    first=incoming[0];last=[r for r in outgoing if np.allclose(r['outward_unit_vector'],-np.array(first['outward_unit_vector']),atol=1e-8,rtol=0)]
    if len(last)!=1:raise ValueError('Unique opposed through-source arm required')
    last=last[0];branches=sorted([r for r in outgoing if r is not last],key=lambda r:r['section']);a,b=branches
    x=np.array(b['outward_unit_vector']);z=np.array(last['outward_unit_vector']);y=np.cross(z,x)
    if not np.allclose(a['outward_unit_vector'],-x,atol=1e-8,rtol=0) or not np.allclose([np.linalg.norm(x),np.linalg.norm(y),np.linalg.norm(z)],[1,1,1],atol=1e-8,rtol=0) or abs(x[2])+abs(z[2])>1e-8:raise ValueError('Two perpendicular opposed planar source pairs required')
    mapping=dict(zip(cross.NAMES,[first,last,a,b]));source='Source node '+node['node']+'; '+row['source']+'; construction basis '+json.dumps(basis,sort_keys=True)
    spec=dict(project_uuid=str(uuid.uuid5(uuid.UUID(basis['project_uuid']),'SOURCE-CROSS:'+node['node'])),source=source,classification=row['classification'],internal_width_m=row['core_section_m'][0],internal_height_m=row['core_section_m'][1],wall_thickness_m=basis['wall_thickness_m']['value'],main_half_length_m=row['main_half_length_m'],branch_length_m=row['branch_length_m'],port_directions={n:'SINK' if r['role']=='incoming' else 'SOURCE' for n,r in mapping.items()},placement=dict(source='Original planar source rays plus explicit elevation',origin_m=node['point_m'][:2]+[basis['elevation_m']['value']],rotation=np.column_stack((x,y,z)).tolist()))
    cross.validate(spec);arms={}
    for name,incident in mapping.items():
        end=[incident['width_m'],incident['height_m']]
        if end==row['core_section_m']:arms[name]={'kind':'bare'}
        else:arms[name]=dict(kind='transition',end_section_m=end,geometry_method=row['transition_method'],transition_length_m=max(abs(a-b) for a,b in zip(end,row['core_section_m']))/(2*math.tan(math.radians(row['upstream_angle_degrees']/2))),**{k:row[k] for k in ('start_length_m','end_length_m','upstream_angle_degrees')})
    return dict(cross=spec,arms=arms),{name:incident['section'] for name,incident in mapping.items()}


def prepare(source,policy,folder):
    parent=json.loads((source/'network.json').read_text());tees=json.loads((Path(parent['source'])/'tee-candidates.json').read_text());selection=Path(tees['source']['selection']);selected=json.loads((selection/'selection.json').read_text());junction=json.loads((selection/'junction.json').read_text());basis=json.loads(Path(selected['source']['basis']).read_text());nodes={n['node']:n for n in junction['nodes'] if n['connection_requirement']=='multi_branch_connection_required'}
    if not nodes or not isinstance(policy,dict) or set(policy)!={'source','nodes'} or not isinstance(policy['source'],str) or not policy['source'].strip() or set(policy['nodes'])!=set(nodes):raise ValueError('Every original multi-branch node must be explicitly covered')
    rows={};reaches={}
    from .source_tee_candidates import transition_screen
    for index,name in enumerate(sorted(nodes),1):
        data,mapping=compile_node(nodes[name],basis,policy['nodes'][name]);child_specs=composition.children(data['cross'],data['arms']);frames=cross.port_frames(data['cross']);fit=[]
        for arm,sid in mapping.items():
            incident=next(i for i in nodes[name]['incidents'] if i['section']==sid);frame=transition.port_frames(child_specs[arm])['end'] if arm in child_specs else frames[arm];ray=np.array(incident['outward_unit_vector']);delta=frame[:3,3]-np.array(data['cross']['placement']['origin_m']);reach=float(np.dot(delta,ray))
            if reach<=0 or not np.allclose(delta,reach*ray,atol=1e-8,rtol=0) or not np.allclose(frame[:3,2],ray,atol=1e-8,rtol=0):raise ValueError('Cross cap differs from original source ray')
            fit.append(dict(arm=arm,section=sid,outward_reach_m=reach,width_m=incident['width_m'],height_m=incident['height_m']));reaches[(name,sid)]=reach
        directory='node-'+str(index).zfill(3);path=folder/directory;path.mkdir(parents=True);(path/'project.json').write_text(json.dumps(data,indent=2));rows[name]=dict(directory=directory,data=data,binding=mapping,fit=fit,screening=transition_screen(child_specs))
    budgets=[];blocked={}
    for row in parent['budgets']:
        trims={name:reaches[(name,row['section'])] for name in nodes if (name,row['section']) in reaches};remaining=row['remaining_m']-math.fsum(trims.values());budgets.append(dict(section=row['section'],before_cross_length_m=row['remaining_m'],declared_cross_trims_m=trims,remaining_m=remaining,minimum_remainder_m=row['minimum_remainder_m']))
        if remaining<row['minimum_remainder_m']-1e-8:
            for name in trims:blocked.setdefault(name,[]).append('Combined source cross reach exceeds inherited budget on '+row['section'])
    for name,row in rows.items():
        if any(not r['supported'] for r in row['screening'].values()):blocked.setdefault(name,[]).append('Declared upstream transition stations unsupported')
    return parent,rows,budgets,blocked


def methods():
    from . import source_tee_candidates
    return [Path(m.__file__) for m in (cross,composition,transition,source_tee_candidates)]+[Path(__file__)]


def run(source,policy,out):
    source,policy,out=[Path(p).resolve() for p in (source,policy,out)]
    if not all(allowed(p) for p in (source,policy,out)) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out) or out==policy or out in policy.parents:raise ValueError('Fresh selected workspace output outside source required')
    network.verify(source);pins={str(p):digest(p) for p in [source/'network.json',policy,*methods()]};parent,rows,budgets,blocked=prepare(source,json.loads(policy.read_text()),out/'inputs');records={}
    for name,row in rows.items():
        record={k:v for k,v in row.items() if k!='data'};record.update(status='blocked' if name in blocked else 'authored_candidate',blocking_reasons=blocked.get(name,[]))
        if name not in blocked:record['native_checks']=composition.run(out/'inputs'/row['directory']/'project.json',out/'models'/row['directory'])['checks']
        records[name]=record
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Cross source/method changed')
    result=dict(source=str(source),policy=str(policy),inputs=pins,nodes=records,budgets=budgets,inherited_blocked_nodes=parent['blocked_nodes'],original_requirement_ids=parent['original_requirement_ids'],complete_network=False,design_accepted=False,original_network_modified=False,scope='Isolated source cross candidates only; no merge, full coordination, pressure, product or installation acceptance')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()};(out/'cross-candidates.json').write_text(json.dumps(result,indent=2));return result


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected workspace required')
    result=json.loads((out/'cross-candidates.json').read_text());source=Path(result['source']);policy=Path(result['policy']);network.verify(source)
    if result['inputs']!={str(p):digest(p) for p in [source/'network.json',policy,*methods()]} or any(result[k] is not False for k in ('complete_network','design_accepted','original_network_modified')):raise ValueError('Cross input/method/status differs')
    for name,sha in result['artifacts'].items():
        path=(out/name).resolve()
        if not path.is_relative_to(out) or digest(path)!=sha:raise ValueError('Cross artifact changed')
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='cross-audit-') as folder:
        parent,rows,budgets,blocked=prepare(source,json.loads(policy.read_text()),Path(folder))
        if result['budgets']!=budgets or result['inherited_blocked_nodes']!=parent['blocked_nodes'] or result['original_requirement_ids']!=parent['original_requirement_ids'] or set(rows)!=set(result['nodes']):raise ValueError('Cross source coverage/budgets differ')
        for name,row in rows.items():
            record=result['nodes'][name];expected={k:v for k,v in row.items() if k!='data'};expected.update(status='blocked' if name in blocked else 'authored_candidate',blocking_reasons=blocked.get(name,[]));path=out/'models'/row['directory']
            if name in blocked:
                if path.exists():raise ValueError('Blocked cross cannot author native model')
            else:expected['native_checks']=composition.inspect(path/'assembly.ifc',row['data']['cross'],row['data']['arms'])
            if expected!=record:raise ValueError('Cross native/fit state differs')
    return dict(integrity_pass=True,source_nodes=len(rows),authored=len(rows)-len(blocked),blocked=len(blocked),complete_network=False,design_accepted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('source');a.add_argument('policy');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args();r=run(a.source,a.policy,a.out) if a.command=='run' else verify(a.out);print(json.dumps(r if a.command=='verify' else {name:row['status'] for name,row in r['nodes'].items()},indent=2));raise SystemExit(2)
