"""Compile declared source unequal tees into existing native tee-transition studies."""
import argparse
from itertools import combinations
import json
import importlib.metadata
import math
from pathlib import Path
import tempfile
import uuid
import numpy as np
from . import rectangular_tee as tee,rectangular_transition as transition,rectangular_tee_transitions as composition,duct_fitting_fit as fit_tool,elbow_radius_selection
from .cli import digest
from .workspace import allowed


def compile_node(junction,basis,name,row):
    fields={'core_section_m','main_half_length_m','branch_length_m','start_length_m','end_length_m','upstream_angle_degrees','classification','source','transition_method'}
    if set(row)!=fields or row['classification'] not in ('assumed','given','secondary_transcription') or not isinstance(row['source'],str) or not row['source'].strip():raise ValueError('Explicit classified core and transition study policy required')
    if row['transition_method'] not in ('upstream_mep_shape','explicit_station_brep'):raise ValueError('Explicit transition authoring method required')
    values=row['core_section_m']+[row[k] for k in ('main_half_length_m','branch_length_m','start_length_m','end_length_m','upstream_angle_degrees')]
    if len(row['core_section_m'])!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values) or row['upstream_angle_degrees']>=90:raise ValueError('Finite positive declared geometry required')
    node=next(n for n in junction['nodes'] if n['node']==name)
    if node['connection_requirement']!='unequal_section_tee_required' or len(node['incidents'])!=3:raise ValueError('Original unequal three-arm source node required')
    incidents=sorted(node['incidents'],key=lambda r:r['section']);pairs=[(a,b) for a,b in combinations(incidents,2) if np.allclose(a['outward_unit_vector'],-np.array(b['outward_unit_vector']),atol=1e-8,rtol=0)]
    if len(pairs)!=1:raise ValueError('Exactly one opposed source main-axis pair required')
    first,last=pairs[0];branch=next(r for r in incidents if r['section'] not in (first['section'],last['section']))
    x=np.array(branch['outward_unit_vector']);z=np.array(last['outward_unit_vector']);y=np.cross(z,x)
    if not np.allclose([np.linalg.norm(x),np.linalg.norm(y),np.linalg.norm(z)],[1,1,1],atol=1e-8,rtol=0) or abs(x[2])+abs(z[2])>1e-8:raise ValueError('Planar perpendicular source tee axes required')
    mapping={'main-a':first,'main-b':last,'branch':branch};source='Source node '+name+'; '+row['source']+'; classified construction '+json.dumps(basis,sort_keys=True)
    spec=dict(project_uuid=str(uuid.uuid5(uuid.UUID(basis['project_uuid']),'SOURCE-TEE:'+name)),source=source,classification=row['classification'],internal_width_m=row['core_section_m'][0],internal_height_m=row['core_section_m'][1],wall_thickness_m=basis['wall_thickness_m']['value'],main_half_length_m=row['main_half_length_m'],branch_length_m=row['branch_length_m'],port_directions={n:'SINK' if r['role']=='incoming' else 'SOURCE' for n,r in mapping.items()},placement=dict(source='Original source rays/XY and explicit study elevation',origin_m=node['point_m'][:2]+[basis['elevation_m']['value']],rotation=np.column_stack((x,y,z)).tolist()))
    tee.validate(spec);arms={}
    for arm,incident in mapping.items():
        end=[incident['width_m'],incident['height_m']]
        if end==row['core_section_m']:arms[arm]={'kind':'bare'}
        else:
            taper=max(abs(a-b) for a,b in zip(end,row['core_section_m']))/(2*math.tan(math.radians(row['upstream_angle_degrees']/2)))
            arms[arm]=dict(kind='transition',geometry_method=row['transition_method'],end_section_m=end,**{k:row[k] for k in ('start_length_m','end_length_m','upstream_angle_degrees')},transition_length_m=taper)
    return spec,dict(source=source,classification=row['classification'],tee='tee.json',arms=arms),dict(source=source,node=name,arms={n:r['section'] for n,r in mapping.items()})


def transition_screen(children):
    import ifcopenshell
    from ifcopenshell.util.shape_builder import ShapeBuilder
    if importlib.metadata.version('ifcopenshell')!='0.8.5':raise ValueError('Pinned IfcOpenShell required')
    builder=ShapeBuilder(ifcopenshell.file(schema='IFC4'));result={}
    for arm,child in children.items():
        lengths=[]
        for offset in (0,child['section_offset_m']):
            a=[v/2+offset for v in child['start_section_m']]+[child['start_length_m']]
            b=[v/2+offset for v in child['end_section_m']]+[child['end_length_m']]
            lengths.append(builder.mep_transition_length(np.array(a),np.array(b),child['upstream_angle_degrees'],verbose=False))
        result[arm]=dict(declared_taper_m=child['transition_length_m'],upstream_inner_outer_tapers_m=lengths,
            geometry_method=child.get('geometry_method','upstream_mep_shape'),upstream_station_match=all(v is not None and math.isclose(v,child['transition_length_m'],abs_tol=1e-9,rel_tol=0) for v in lengths),supported=child.get('geometry_method')=='explicit_station_brep' or all(v is not None and math.isclose(v,child['transition_length_m'],abs_tol=1e-9,rel_tol=0) for v in lengths))
    return result


def prepare(junction,basis,policy,folder):
    if set(policy)!={'basis','nodes'} or not isinstance(policy['basis'],str) or not policy['basis'].strip():raise ValueError('Explicit tee policy required')
    wanted=sorted(n['node'] for n in junction['nodes'] if n['connection_requirement']=='unequal_section_tee_required')
    if not wanted or set(policy['nodes'])!=set(wanted):raise ValueError('Every original unequal tee needs one explicit candidate')
    rows={}
    for index,name in enumerate(wanted,1):
        spec,data,binding=compile_node(junction,basis,name,policy['nodes'][name]);path=folder/('node-'+str(index).zfill(3));path.mkdir(parents=True)
        for filename,value in [('tee.json',spec),('project.json',data),('binding.json',binding)]: (path/filename).write_text(json.dumps(value,indent=2))
        _,_,_,_,children=composition.prepare(path/'project.json');fit=fit_tool.assess(junction,spec,children,binding)
        rows[name]=dict(directory=path.name,fit=fit,spec=spec,data=data,children=children,binding=binding,transition_screening=transition_screen(children))
    return rows


def budgets(selected,rows):
    blocked={name:['Upstream transition stations disagree on arms '+','.join(arm for arm,r in row['transition_screening'].items() if not r['supported'])] for name,row in rows.items() if any(not r['supported'] for r in row['transition_screening'].values())};result=[];minimum=selected['policy']['minimum_remainder_m']['value']
    reaches={}
    for name,row in rows.items():
        for arm in row['fit']['arms']:reaches[(name,arm['section'])]=arm['outward_reach_m']
    for base in selected['fit']['source_section_budgets']:
        tee_trims={name:reaches[(name,base['section'])] for name in rows if (name,base['section']) in reaches}
        remaining=base['remaining_after_declared_elbows_m']-math.fsum(tee_trims.values())
        row=dict(base,declared_tee_trims_m=tee_trims,remaining_after_known_fittings_m=remaining,inherited_minimum_remainder_m=minimum,all_fitting_trims_known=False)
        result.append(row)
        if tee_trims and remaining<minimum-1e-8:
            for name in tee_trims:blocked.setdefault(name,[]).append('Known both-end fitting reach exceeds source budget on '+base['section'])
    return result,blocked


def methods():
    from . import rectangular_tee_assembly,tee_geometry,workspace
    import ifcopenshell.util.shape_builder as shape_builder
    return [Path(__file__),*[Path(m.__file__) for m in (tee,transition,composition,fit_tool,elbow_radius_selection,rectangular_tee_assembly,tee_geometry,workspace,shape_builder)]]


def run(selection,policy,out):
    selection,policy,out=[Path(p).resolve() for p in (selection,policy,out)]
    if not all(allowed(p) for p in (selection,policy,out)) or out.exists() or out.is_relative_to(selection) or selection.is_relative_to(out) or out==policy or out in policy.parents:raise ValueError('Fresh selected workspace outside source runs required')
    elbow_radius_selection.verify(selection);selected=json.loads((selection/'selection.json').read_text());basis_path=Path(selected['source']['basis']);junction=json.loads((selection/'junction.json').read_text());basis=json.loads(basis_path.read_text());source=json.loads(policy.read_text())
    pins={str(p):digest(p) for p in [selection/'selection.json',selection/'junction.json',basis_path,policy,*methods()]}
    rows=prepare(junction,basis,source,out/'inputs');lengths,blocked=budgets(selected,rows);node_results={}
    for name,row in rows.items():
        value=dict(directory=row['directory'],fit=row['fit'],transition_screening=row['transition_screening'],status='blocked' if name in blocked else 'authored_candidate',blocking_reasons=blocked.get(name,[]),design_accepted=False)
        if name not in blocked:
            native=composition.run(out/'inputs'/row['directory']/'project.json',out/'models'/row['directory']);value['native_checks']=native['checks']
        node_results[name]=value
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Source or method changed during tee authoring')
    result=dict(source=dict(selection=str(selection),policy=str(policy)),inputs=pins,nodes=node_results,known_fitting_budgets=lengths,
        not_authored_source_nodes=[n for n in selected['fit']['remaining_source_connection_nodes'] if n['requirement']!='unequal_section_tee_required'],
        original_requirement_ids=[r['id'] for r in json.loads((selection/'native/elbow-backbone.json').read_text())['original_requirements']],
        original_backbone_modified=False,complete_network=False,design_accepted=False,scope='Source-matched isolated tee/centred-transition candidates and known both-end budgets only; no insertion into original backbone, physical joints, full clearance or pressure approval')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()};(out/'tee-candidates.json').write_text(json.dumps(result,indent=2));return result


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected workspace required')
    result=json.loads((out/'tee-candidates.json').read_text());selection=Path(result['source']['selection']);policy=Path(result['source']['policy']);elbow_radius_selection.verify(selection)
    if result['design_accepted'] is not False or result['original_backbone_modified'] is not False or result['complete_network'] is not False or any(digest(Path(p))!=sha for p,sha in result['inputs'].items()):raise ValueError('Tee source or method changed')
    for name,sha in result['artifacts'].items():
        p=(out/name).resolve()
        if not p.is_relative_to(out) or digest(p)!=sha:raise ValueError('Tee artifact changed')
    selected=json.loads((selection/'selection.json').read_text());junction=json.loads((selection/'junction.json').read_text());basis_path=Path(selected['source']['basis']);basis=json.loads(basis_path.read_text())
    expected={str(p):digest(p) for p in [selection/'selection.json',selection/'junction.json',basis_path,policy,*methods()]}
    if result['inputs']!=expected:raise ValueError('Tee input inventory differs')
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='tee-audit-') as folder:
        rows=prepare(junction,basis,json.loads(policy.read_text()),Path(folder)/'inputs');lengths,blocked=budgets(selected,rows)
        if lengths!=result['known_fitting_budgets'] or set(rows)!=set(result['nodes']):raise ValueError('Tee source budgets or coverage differ')
        for name,row in rows.items():
            record=result['nodes'][name];path=out/'models'/row['directory']
            if record['transition_screening']!=row['transition_screening'] or record['fit']!=row['fit'] or record['directory']!=row['directory'] or record['blocking_reasons']!=blocked.get(name,[]) or record['status']!=('blocked' if name in blocked else 'authored_candidate'):raise ValueError('Tee fit or authored state differs')
            if name in blocked:
                if path.exists():raise ValueError('Blocked tee cannot author native geometry')
            elif record['native_checks']!=composition.inspect(path/'assembly.ifc',row['spec'],row['data'],row['children']):raise ValueError('Native tee checks differ')
    return dict(integrity_pass=True,source_tees=len(rows),authored=sum(n not in blocked for n in rows),blocked=len(blocked),original_backbone_modified=False,design_accepted=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('selection');a.add_argument('policy');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');args=p.parse_args()
    r=run(args.selection,args.policy,args.out) if args.command=='run' else verify(args.out)
    print(json.dumps(r if args.command=='verify' else dict(source_tees=len(r['nodes']),authored=sum(n['status']=='authored_candidate' for n in r['nodes'].values()),complete_network=False,design_accepted=False),indent=2));return 2

if __name__=='__main__':raise SystemExit(main())
