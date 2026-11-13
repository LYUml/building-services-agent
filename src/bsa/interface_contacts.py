"""Inspect actual rectangular cap material and bounded outside-interface clearance."""
import argparse
from collections import Counter,defaultdict
import copy
import json
import math
from pathlib import Path
import numpy as np
from . import source_compound_network as producer,clash,contact_clearance
from .duct_coordination_diagnosis import pair_signature
from .cli import digest
from .workspace import allowed


def cap(vertices,faces,frame):
    """Recover one centred rectangular annulus from actual coplanar mesh triangles."""
    vertices=np.array(vertices);faces=np.array(faces);frame=np.array(frame);local=(vertices-frame[:3,3])@frame[:3,:3]
    selected=[list(map(int,f)) for f in faces if np.max(abs(local[f,2]))<1e-8]
    if not selected:raise ValueError('Native port plane has no material cap triangles')
    owners=defaultdict(set)
    for i,f in enumerate(selected):
        for v in f:owners[v].add(i)
    remaining=set(range(len(selected)));components=[]
    while remaining:
        seed=remaining.pop();queue=[seed];group=[]
        for i in queue:
            group.append(selected[i])
            for v in selected[i]:
                for n in owners[v]&remaining:remaining.remove(n);queue.append(n)
        components.append(group)
    candidates=[]
    for group in components:
        points=local[sorted({i for f in group for i in f}),:2]
        if np.allclose(points.min(axis=0),-points.max(axis=0),atol=1e-8,rtol=0):candidates.append(group)
    if len(candidates)!=1:raise ValueError('Unique native annulus centred on the actual port required')
    group=candidates[0];edges=Counter(tuple(sorted((a,b))) for f in group for a,b in zip(f,[f[1],f[2],f[0]]));boundary=[e for e,n in edges.items() if n==1]
    if any(n not in (1,2) for n in edges.values()):raise ValueError('Invalid native cap triangle topology')
    adjacent=defaultdict(set)
    for a,b in boundary:adjacent[a].add(b);adjacent[b].add(a)
    if any(len(n)!=2 for n in adjacent.values()):raise ValueError('Native cap boundary loops must be closed')
    pending=set(adjacent);loops=[]
    while pending:
        start=next(iter(pending));loop=[start];previous=None;current=start
        while True:
            choices=adjacent[current]-({previous} if previous is not None else set());n=next(iter(choices))
            if n==start:break
            if n in loop:raise ValueError('Native cap boundary self-cycle')
            loop.append(n);previous,current=current,n
        pending-=set(loop);xy=local[loop,:2];lo=xy.min(axis=0);hi=xy.max(axis=0)
        area=abs(np.dot(xy[:,0],np.roll(xy[:,1],-1))-np.dot(xy[:,1],np.roll(xy[:,0],-1)))/2
        if not np.allclose(lo,-hi,atol=1e-8,rtol=0) or np.any(hi<=0) or not math.isclose(area,float(np.prod(hi-lo)),rel_tol=1e-8,abs_tol=1e-12) or any(min(abs(a-b))>1e-8 for a,b in zip(xy,np.roll(xy,-1,axis=0))):raise ValueError('Native cap loop is not a centred axis-aligned rectangle')
        loops.append((area,hi))
    if len(loops)!=2:raise ValueError('Native material cap requires one outer and one inner rectangle')
    loops.sort(key=lambda x:x[0]);inner,outer=loops[0][1],loops[1][1]
    if np.any(inner>=outer):raise ValueError('Native cap annulus dimensions invalid')
    area=0.
    for f in group:
        a,b,c=local[f,:2];area+=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
    if not math.isclose(area,loops[1][0]-loops[0][0],rel_tol=1e-8,abs_tol=1e-12):raise ValueError('Native cap material area differs from independent annulus area')
    def corners(half):return [(frame[:3,3]+frame[:3,:2]@np.array([x*half[0],y*half[1]])).tolist() for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    return dict(inner_corners=corners(inner),outer_corners=corners(outer),material_area_m2=area,outer_half_diagonal_m=float(np.linalg.norm(outer)),inner_section_m=(2*inner).tolist(),outer_section_m=(2*outer).tolist())


def matching(first,last):
    for key in ('inner_corners','outer_corners'):
        a,b=np.array(first[key]),np.array(last[key])
        if any(np.min(np.linalg.norm(b-p,axis=1))>1e-8 for p in a):raise ValueError('Connected native cap material boundaries differ')
    if not math.isclose(first['material_area_m2'],last['material_area_m2'],rel_tol=1e-8,abs_tol=1e-12):raise ValueError('Connected native material cap areas differ')


def native_contacts(ifc,policy):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.system as system
    import ifcopenshell.util.placement as placement
    from .circular_geometry import configure
    if not isinstance(policy,dict) or set(policy)!={'source','classification','radius_factor','radial_allowance_m','sphere_segments'} or not isinstance(policy['source'],str) or not policy['source'].strip() or policy['classification']!='assumed':raise ValueError('Explicit assumed numerical contact study policy required')
    if type(policy['radius_factor']) not in (int,float) or not 1<policy['radius_factor']<=2 or type(policy['radial_allowance_m']) not in (int,float) or not 0<=policy['radial_allowance_m']<=.01 or type(policy['sphere_segments']) is not int or not 16<=policy['sphere_segments']<=256 or policy['sphere_segments']%4:raise ValueError('Explicit bounded numerical mask parameters required')
    file=ifcopenshell.open(str(ifc));settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);configure(settings);meshes={};caps={};records=[]
    for r in file.by_type('IfcRelConnectsPorts'):
        ports=[r.RelatingPort,r.RelatedPort];objects=[system.get_port_element(p) for p in ports]
        if any(o is None for o in objects) or ports[0].FlowDirection!='SOURCE' or ports[1].FlowDirection!='SINK':raise ValueError('Actual owned source-to-sink interface required')
        frames=[placement.get_local_placement(p.ObjectPlacement) for p in ports]
        if not np.allclose(frames[0][:3,3],frames[1][:3,3],atol=1e-8,rtol=0) or not np.allclose(frames[0][:3,2],-frames[1][:3,2],atol=1e-8,rtol=0):raise ValueError('Actual interface planes differ')
        for o,p,frame in zip(objects,ports,frames):
            if o.GlobalId not in meshes:
                shape=ifcopenshell.geom.create_shape(settings,o);meshes[o.GlobalId]=(np.array(shape.geometry.verts).reshape(-1,3),np.array(shape.geometry.faces).reshape(-1,3))
            if p.GlobalId not in caps:caps[p.GlobalId]=cap(*meshes[o.GlobalId],frame)
        first,last=[caps[p.GlobalId] for p in ports];matching(first,last)
        radius=max(first['outer_half_diagonal_m'],last['outer_half_diagonal_m'])*policy['radius_factor']+policy['radial_allowance_m']
        records.append(dict(pair=sorted(o.GlobalId for o in objects),port_guids=[p.GlobalId for p in ports],names=[o.Name for o in objects],native_material_caps_match=True,material_area_m2=first['material_area_m2'],region_radius_m=radius))
    if len({tuple(r['pair']) for r in records})!=len(records):raise ValueError('Study requires one interface per physical body pair')
    return records


def methods():return [Path(__file__),Path(producer.__file__),Path(clash.__file__),Path(contact_clearance.__file__),Path(__file__).with_name('duct_coordination_diagnosis.py')]


def raw_inputs(ifc,saved):
    other=[Path(p) for p in saved['inputs'] if Path(p)!=ifc]
    if saved['inputs'].get(str(ifc))!=digest(ifc) or saved['policy']['allowed_contacts'] or len(other)!=1 or json.loads(other[0].read_text(encoding='utf-8-sig'))!=saved['policy'] or any(not allowed(Path(p)) or digest(Path(p))!=sha for p,sha in saved['inputs'].items()):raise ValueError('Exact unchanged raw no-waiver model/policy required')
    return dict(saved['inputs'])


def evaluate(ifc,saved,study_policy):
    fresh=clash.inspect(ifc,saved['policy'])
    if pair_signature(saved)!=pair_signature(fresh):raise ValueError('Raw clash records differ from independent native replay')
    contacts=native_contacts(ifc,study_policy);linked={tuple(c['pair']) for c in contacts};raw_pairs={tuple(sorted(r['pair'])) for r in fresh['clearance_violations']}
    derived=copy.deepcopy(saved['policy']);derived['sources']['native_cap_study']=study_policy['source']+'; numerical masks only, not product joints or installation clearances';derived['contact_clearance_mode']='outside_regions';derived['contact_region_segments']=study_policy['sphere_segments'];derived['allowed_contacts']=[dict(from_port_guid=c['port_guids'][0],to_port_guid=c['port_guids'][1],region_radius_m=c['region_radius_m'],source='native_cap_study') for c in contacts]
    study=clash.inspect(ifc,derived);proofs=study['outside_region_checks'];nonvacuous=[p for p in proofs if p['pass_check'] and all(not d['outside_empty'] for d in p['directions'])];vacuous=[p for p in proofs if p['pass_check'] and any(d['outside_empty'] for d in p['directions'])]
    metrics=dict(native_interfaces=contacts,raw_clearance_records=len(fresh['clearance_violations']),raw_unique_clearance_pairs=len(raw_pairs),raw_linked_clearance_pairs=len(raw_pairs&linked),raw_unlinked_clearance_pairs=len(raw_pairs-linked),outside_region_proofs=len(proofs),nonvacuous_passes=len(nonvacuous),vacuous_passes_retained_pending=len(vacuous),not_proven=len(proofs)-len(nonvacuous)-len(vacuous),study_checks=study['checks'])
    return metrics,fresh,derived,study


def run(source,raw,policy,out):
    source,raw,policy,out=[Path(p).resolve() for p in (source,raw,policy,out)]
    if not all(allowed(p) for p in (source,raw,policy,out)) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out) or any(out==p or out in p.parents for p in (raw,policy)):raise ValueError('Fresh selected workspace outside all sources required')
    producer.verify(source);ifc=source/'Supply Network.ifc';saved=json.loads(raw.read_text());study_policy=json.loads(policy.read_text());pins={str(p):digest(p) for p in [source/'network.json',ifc,raw,policy,*methods()]}
    pins.update(raw_inputs(ifc,saved));metrics,fresh,derived,study=evaluate(ifc,saved,study_policy)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Interface study source/method changed')
    report=dict(source=str(source),raw=str(raw),policy=str(policy),inputs=pins,**metrics,study_policy_is_assumed=True,original_raw_result_unchanged=True,original_requirement_ids=json.loads((source/'network.json').read_text())['original_requirement_ids'],complete_network=False,design_accepted=False,scope='Native matching material cap and assumed bounded-region numerical study; raw failures remain, empty outside-body results stay pending, no physical joint/product/installation or code acceptance')
    out.mkdir(parents=True)
    for name,value in [('raw-replay.json',fresh),('derived-policy.json',derived),('contact-study.json',study)]: (out/name).write_text(json.dumps(value,indent=2))
    report['artifacts']={p.name:digest(p) for p in out.iterdir()};(out/'interfaces.json').write_text(json.dumps(report,indent=2));return report


def proof_signature(study):
    return sorted((tuple(p['pair']),p['pass_check'],p['status'],p.get('reason',''),tuple((d['outside_guid'],d['full_guid'],d['outside_empty'],None if d['conservative_gap_lower_bound_m'] is None else round(d['conservative_gap_lower_bound_m'],10),d['pass_check']) for d in p.get('directions',[]))) for p in study['outside_region_checks'])


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected workspace required')
    report=json.loads((out/'interfaces.json').read_text());source=Path(report['source']);raw=Path(report['raw']);policy=Path(report['policy'])
    if not all(allowed(p) for p in (source,raw,policy)):raise ValueError('Selected contact sources required')
    producer.verify(source);ifc=source/'Supply Network.ifc';saved=json.loads(raw.read_text())
    pins={str(p):digest(p) for p in [source/'network.json',ifc,raw,policy,*methods()]}|raw_inputs(ifc,saved)
    if report['inputs']!=pins or report['complete_network'] is not False or report['design_accepted'] is not False or report['study_policy_is_assumed'] is not True or report['original_raw_result_unchanged'] is not True:raise ValueError('Contact source/method/status differs')
    if set(report['artifacts'])!={'raw-replay.json','derived-policy.json','contact-study.json'} or any(digest(out/name)!=sha for name,sha in report['artifacts'].items()):raise ValueError('Contact artifact inventory changed')
    metrics,fresh,derived,study=evaluate(ifc,saved,json.loads(policy.read_text()))
    if any(report[k]!=v for k,v in metrics.items()) or report['original_requirement_ids']!=json.loads((source/'network.json').read_text())['original_requirement_ids'] or json.loads((out/'derived-policy.json').read_text())!=derived or pair_signature(json.loads((out/'raw-replay.json').read_text()))!=pair_signature(fresh):raise ValueError('Contact source/cap/raw replay differs')
    recorded=json.loads((out/'contact-study.json').read_text())
    if pair_signature(recorded)!=pair_signature(study) or proof_signature(recorded)!=proof_signature(study) or sorted(tuple(r['pair']) for r in recorded['accepted_contacts'])!=sorted(tuple(r['pair']) for r in study['accepted_contacts']):raise ValueError('Outside-region proof replay differs')
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Contact source changed during replay')
    return dict(integrity_pass=True,raw_unique_clearance_pairs=metrics['raw_unique_clearance_pairs'],nonvacuous_passes=metrics['nonvacuous_passes'],vacuous_passes_retained_pending=metrics['vacuous_passes_retained_pending'],not_proven=metrics['not_proven'],design_accepted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('source');a.add_argument('raw');a.add_argument('policy');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args();r=run(a.source,a.raw,a.policy,a.out) if a.command=='run' else verify(a.out);print(json.dumps({k:r[k] for k in (('raw_unique_clearance_pairs','nonvacuous_passes','vacuous_passes_retained_pending','not_proven','design_accepted') if a.command=='run' else r)},indent=2));raise SystemExit(2)
