"""Bind EPANET water graphs to saved hollow IFC pipes and explicit connected GUIDs."""
import argparse
import copy
import csv
import json
import math
from pathlib import Path
import re
import shutil
from .cli import digest
from .engine import ProjectError

IDEALIZATION='coincident node ports form a zero-loss hydraulic node; withdrawals and boundary heads are separately sourced'
TOLERANCE_M=1e-8


def validate_contract(project,binding):
    fields={'version','source','project_guid','system_guid','node_idealization','nodes','pipes','pumps'}
    if not isinstance(binding,dict) or set(binding)!=fields or type(binding['version']) is not int or binding['version']!=1 or binding['node_idealization']!=IDEALIZATION:
        raise ProjectError('versioned GUID binding and explicit zero-loss node idealization required')
    if not isinstance(binding['source'],str) or not binding['source'].strip():raise ProjectError('water binding source required')
    def guid(value):
        if not isinstance(value,str) or not re.fullmatch(r'[0-3][0-9A-Za-z_$]{21}',value):raise ProjectError('explicit compressed IFC GUID required')
    for key in ('project_guid','system_guid'):guid(binding[key])
    if not isinstance(project,dict):raise ProjectError('water template required')
    collections={}
    for kind in ('reservoirs','junctions','pipes','pumps'):
        rows=project.get(kind)
        if not isinstance(rows,list) or any(not isinstance(r,dict) or not isinstance(r.get('id'),str) for r in rows):raise ProjectError('identified water template rows required')
        collections[kind]={r['id']:r for r in rows}
        if len(collections[kind])!=len(rows):raise ProjectError('unique template IDs required')
    nodes={**collections['reservoirs'],**collections['junctions']}
    if len(nodes)!=len(collections['reservoirs'])+len(collections['junctions']):raise ProjectError('unique node IDs required')
    for kind,ids in (('nodes',nodes),('pipes',collections['pipes']),('pumps',collections['pumps'])):
        if not isinstance(binding[kind],dict) or set(binding[kind])!=set(ids):raise ProjectError('exact node/pipe/pump binding coverage required')
    for r in project['reservoirs']+project['junctions']:
        if 'elevation_m' in r or 'connection_elevation_m' in r:raise ProjectError('template must not repeat bound elevation')
    for r in project['pipes']:
        if 'length_m' in r or 'diameter_m' in r:raise ProjectError('template must not repeat bound pipe length/diameter')
    used=set()
    def piece(row,fields):
        if not isinstance(row,dict) or set(row)!=fields:raise ProjectError('exact GUID binding fields required')
        guid(row['element_guid'])
        if row['element_guid'] in used:raise ProjectError('each physical element must have one hydraulic role')
        used.add(row['element_guid'])
    for row in binding['nodes'].values():
        piece(row,{'element_guid','port_guids'})
        if not isinstance(row['port_guids'],list) or not row['port_guids']:raise ProjectError('nonempty node ports required')
        for value in row['port_guids']:guid(value)
        if len(set(row['port_guids']))!=len(row['port_guids']):raise ProjectError('unique node ports required')
    for rows in list(binding['pipes'].values())+[[r] for r in binding['pumps'].values()]:
        if not isinstance(rows,list) or not rows:raise ProjectError('nonempty ordered physical pipe chain required')
        for row in rows:
            piece(row,{'element_guid','start_port_guid','end_port_guid'})
            guid(row['start_port_guid']);guid(row['end_port_guid'])
            if row['start_port_guid']==row['end_port_guid']:raise ProjectError('distinct route end ports required')
    return binding


def derive(ifc,project,binding):
    import ifcopenshell
    import ifcopenshell.util.system as system
    import ifcopenshell.util.placement as placement
    from .ifc_drawing import extract
    from .epanet import validate
    validate_contract(project,binding)
    ifc=Path(ifc);sha=digest(ifc);extracted=extract(ifc);factor=extracted['source_length_unit_to_m']
    model=ifcopenshell.open(str(ifc));objects={o.GlobalId:o for o in model.by_type('IfcRoot')}
    if len(model.by_type('IfcProject'))!=1 or model.by_type('IfcProject')[0].GlobalId!=binding['project_guid']:raise ProjectError('bound IFC project differs')
    selected=objects.get(binding['system_guid'])
    if not selected or not selected.is_a('IfcDistributionSystem'):raise ProjectError('bound distribution system missing')
    scope={o.GlobalId:o for o in model.by_type('IfcDistributionElement') if selected in system.get_element_systems(o)}
    claims={row['element_guid'] for row in binding['nodes'].values()}|{row['element_guid'] for rows in binding['pipes'].values() for row in rows}|{row['element_guid'] for row in binding['pumps'].values()}
    if set(scope)!=claims:raise ProjectError('every selected-system distribution element must have exactly one explicit hydraulic role')
    for obj in scope.values():
        if {s.GlobalId for s in system.get_element_systems(obj)}!={binding['system_guid']}:raise ProjectError('bound element has ambiguous multiple-system membership')
    bad=[r for r in extracted['unsupported_segments'] if r['guid'] in claims]
    if bad:raise ProjectError('unsupported selected-system pipe geometry: '+json.dumps(bad))
    profiles={r['guid']:r for r in extracted['segments']}
    ports={};owners={}
    for obj in scope.values():
        for port in system.get_ports(obj):
            if not port.ObjectPlacement:raise ProjectError('explicit placed water ports required')
            xyz=(placement.get_local_placement(port.ObjectPlacement)[:3,3]*factor).tolist()
            if not all(math.isfinite(v) for v in xyz):raise ProjectError('finite water port positions required')
            ports[port.GlobalId]=(port,xyz);owners[port.GlobalId]=obj.GlobalId
    def point(g):
        if g not in ports:raise ProjectError('bound port missing from selected system')
        return ports[g][1]
    def coincident(a,b):return math.dist(point(a),point(b))<=TOLERANCE_M
    def owned(row,ids):
        actual={g for g,o in owners.items() if o==row['element_guid']}
        if actual!=set(ids):raise ProjectError('binding must cover exactly the actual element ports')
    actual_links=set();directed_links=set();neighbours={g:set() for g in ports}
    for relation in model.by_type('IfcRelConnectsPorts'):
        a,b=relation.RelatingPort.GlobalId,relation.RelatedPort.GlobalId
        if a not in ports and b not in ports:continue
        if a not in ports or b not in ports or a==b:raise ProjectError('water connection crosses selected-system scope')
        directions=(ports[a][0].FlowDirection,ports[b][0].FlowDirection)
        if directions not in (('SOURCE','SINK'),('SOURCEANDSINK','SOURCEANDSINK')):raise ProjectError('IFC connection direction contradicts declared water ports')
        if relation.RealizingElement is not None:raise ProjectError('implicit realizing-element links require explicit hydraulic decomposition')
        if (a,b) in directed_links:raise ProjectError('duplicate native water port relationship')
        directed_links.add((a,b))
        actual_links.add(frozenset((a,b)));neighbours[a].add(b);neighbours[b].add(a)
    for a,b in directed_links:
        if ports[a][0].FlowDirection=='SOURCEANDSINK' and (b,a) not in directed_links:
            raise ProjectError('reversible water connection requires both native relationship directions')
    if any(len(peers)!=1 for peers in neighbours.values()):raise ProjectError('each selected water port needs exactly one connected peer')
    expected=set();node_points={};evidence=dict(ifc_sha256=sha,project_guid=binding['project_guid'],system_guid=binding['system_guid'],length_unit_to_m=factor,nodes={},pipes={},pumps={})
    for id,row in binding['nodes'].items():
        obj=scope[row['element_guid']]
        if obj.is_a('IfcPipeSegment') or obj.is_a('IfcPump'):raise ProjectError('hydraulic node must be a separate declared junction/boundary element')
        owned(row,row['port_guids']);first=row['port_guids'][0]
        if any(not coincident(first,g) for g in row['port_guids']):raise ProjectError('ideal node ports must be coincident; finite fittings require their own hydraulic model')
        node_points[id]=point(first)
        evidence['nodes'][id]=dict(element_guid=row['element_guid'],port_guids=row['port_guids'],world_m=point(first))
    def connect(a,b):
        pair=frozenset((a,b))
        if pair not in actual_links or not coincident(a,b):raise ProjectError('route requires an actual coincident IFC port connection')
        expected.add(pair)
    def attach(node,route_port):
        candidates=[g for g in binding['nodes'][node]['port_guids'] if frozenset((g,route_port)) in actual_links]
        if len(candidates)!=1:raise ProjectError('route end must connect to the explicitly bound node element')
        connect(candidates[0],route_port)
    derived=copy.deepcopy(project)
    def sourced(row,kind):
        key='IFC:'+kind+':'+row['id']
        if key in derived['sources'] or row.get('source') not in derived['sources']:raise ProjectError('known hydraulic source and unused IFC source key required')
        derived['sources'][key]=derived['sources'][row['source']]+'; geometry from IFC SHA256 '+sha+'; '+binding['source']
        row['source']=key
    for row in derived['reservoirs']+derived['junctions']:
        row['connection_elevation_m' if row in derived['reservoirs'] else 'elevation_m']=node_points[row['id']][2]
        sourced(row,'node')
    for row in derived['pipes']:
        chain=binding['pipes'][row['id']];length=0;diameters=[];previous=None;records=[]
        for piece in chain:
            g=piece['element_guid'];obj=scope[g];profile=profiles.get(g)
            if not obj.is_a('IfcPipeSegment') or not profile:raise ProjectError('actual direct hollow pipe profile required')
            a,b=piece['start_port_guid'],piece['end_port_guid'];owned(piece,(a,b))
            if any(ports[p][0].FlowDirection!='SOURCEANDSINK' for p in (a,b)):raise ProjectError('free-flow water pipes require explicit bidirectional IFC ports')
            if previous:connect(previous,a)
            previous=b;length+=profile['length_m'];diameters.append(profile['inner_diameter_m'])
            records.append(dict(**piece,length_m=profile['length_m'],diameter_m=profile['inner_diameter_m'],start_world_m=point(a),end_world_m=point(b)))
        if any(not math.isclose(d,diameters[0],abs_tol=1e-10,rel_tol=0) for d in diameters):raise ProjectError('split hydraulic links where profile diameter changes')
        attach(row['from'],chain[0]['start_port_guid']);attach(row['to'],chain[-1]['end_port_guid'])
        row.update(length_m=length,diameter_m=diameters[0]);sourced(row,'pipe');evidence['pipes'][row['id']]=records
    for row in derived['pumps']:
        piece=binding['pumps'][row['id']];g=piece['element_guid'];a,b=piece['start_port_guid'],piece['end_port_guid'];owned(piece,(a,b))
        if not scope[g].is_a('IfcPump') or ports[a][0].FlowDirection!='SINK' or ports[b][0].FlowDirection!='SOURCE':raise ProjectError('bound pump requires actual sink/source ports in curve direction')
        attach(row['from'],a);attach(row['to'],b);sourced(row,'pump');evidence['pumps'][row['id']]=dict(**piece,start_world_m=point(a),end_world_m=point(b))
    if expected!=actual_links:raise ProjectError('unmodelled or unexpected selected-system IFC connections remain')
    validate(derived)
    evidence.update(selected_element_count=len(scope),connection_pair_count=len(actual_links),excluded_other_system_elements=[o.GlobalId for o in model.by_type('IfcDistributionElement') if o.GlobalId not in claims])
    return derived,evidence


def reconcile(ifc,derived_path,template,binding):
    actual,_=derive(ifc,template,binding)
    expected=json.loads(Path(derived_path).read_text(encoding='utf-8-sig'))
    if actual!=expected:raise ProjectError('saved IFC differs from derived water analysis input')
    return True


def run(project,ifc,binding,out):
    from .epanet import run as analyse
    paths=[Path(p).resolve() for p in (project,ifc,binding)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain sources')
    before={str(p):digest(p) for p in paths};template=json.loads(paths[0].read_text(encoding='utf-8-sig'));link=json.loads(paths[2].read_text(encoding='utf-8-sig'))
    derived,evidence=derive(paths[1],template,link);out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(paths[1],out/'model.ifc');generated=out/'network-input.json';generated.write_text(json.dumps(derived,indent=2),encoding='utf-8')
    calculation=analyse(generated,out/'analysis');saved=reconcile(out/'model.ifc',generated,template,link)
    with (out/'pipe-results.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['hydraulic_id','element_guid','start_port_guid','end_port_guid','length_m','diameter_m','signed_flow_m3_s'])
        writer.writeheader();flows={p['id']:p['flow_m3_s'] for p in calculation.get('pipes',[])}
        for id,chain in evidence['pipes'].items():
            for piece in chain:writer.writerow({**{k:piece[k] for k in writer.fieldnames if k in piece},'hydraulic_id':id,'signed_flow_m3_s':flows.get(id)})
    (out/'geometry-binding.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    unchanged=all(digest(Path(p))==sha for p,sha in before.items())
    if not unchanged:raise ProjectError('source changed during water binding')
    copy_unchanged=digest(out/'model.ifc')==before[str(paths[1])]
    result=dict(inputs=before,inputs_unchanged=True,saved_ifc_match=saved,ifc_copy_unchanged=digest(out/'model.ifc')==before[str(paths[1])],
                calculated_checks_pass=saved and copy_unchanged and calculation['calculated_checks_pass'],design_accepted=False,
                scope='Saved hollow IFC pipe/port GUID chains; derived length/internal diameter/elevation; reversible pipe flow and explicit zero-loss nodes; actual EPANET execution',
                pending=['source IFC schema/product/visual applicability','physical junctions/bends, K applicability and clash acceptance','pump product/efficiency/NPSH and full domain acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'water-binding.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--ifc',required=True,type=Path);p.add_argument('--binding',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();r=run(a.project,a.ifc,a.binding,a.out);print(json.dumps({k:r[k] for k in ('calculated_checks_pass','design_accepted')}));return 0 if r['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
