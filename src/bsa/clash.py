"""Read-only IFC triangle-geometry intersection/clearance checks with scoped contacts."""
from collections import Counter
import argparse
import html
import json
import math
import re
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .circular_geometry import configure,LINEAR_DEFLECTION_M,ANGULAR_DEFLECTION

SCOPE='all represented non-feature non-virtual IfcElements'


def validate_policy(policy):
    fields={'scope','sources','source','minimum_clearance_m','intersection_tolerance_m','contact_tolerance_m','overlap_volume_tolerance_m3','maximum_boolean_pairs','allowed_contacts'}
    optional={'contact_clearance_mode','contact_region_segments'}
    if not isinstance(policy,dict) or not fields<=set(policy) or set(policy)-fields-optional or policy['scope']!=SCOPE:raise ProjectError('explicit IFC clash policy/scope required')
    mode=policy.get('contact_clearance_mode','minimum_witness_only')
    if mode not in ('minimum_witness_only','outside_regions'):raise ProjectError('unknown contact clearance mode')
    if mode=='outside_regions':
        segments=policy.get('contact_region_segments')
        if type(segments) is not int or not 16<=segments<=256 or segments%4:raise ProjectError('explicit contact mask segments: multiple of four from 16 to 256 required')
    elif 'contact_region_segments' in policy:raise ProjectError('contact mask settings require outside_regions mode')
    sources=policy['sources']
    if not isinstance(sources,dict) or not sources or any(not isinstance(k,str) or not k or not isinstance(v,str) or not v.strip() for k,v in sources.items()):
        raise ProjectError('clash policy provenance required')
    def sourced(row):
        if not isinstance(row.get('source'),str) or row['source'] not in sources:raise ProjectError('known policy source required')
    sourced(policy)
    for key in ('minimum_clearance_m','intersection_tolerance_m','contact_tolerance_m','overlap_volume_tolerance_m3'):
        value=policy[key]
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ProjectError('positive finite clash distances required')
    if not 2*LINEAR_DEFLECTION_M<=policy['contact_tolerance_m']<=policy['intersection_tolerance_m']<=policy['minimum_clearance_m']:
        raise ProjectError('twice mesh deflection <= contact <= intersection <= clearance tolerances required')
    if type(policy['maximum_boolean_pairs']) is not int or not 1<=policy['maximum_boolean_pairs']<=100000:raise ProjectError('explicit Boolean candidate budget from 1 to 100000 required')
    rows=policy['allowed_contacts']
    if not isinstance(rows,list):raise ProjectError('explicit allowed contact list required')
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'from_port_guid','to_port_guid','region_radius_m','source'}:raise ProjectError('contacts require exact source/sink port GUIDs, a sourced witness region and provenance')
        sourced(row)
        radius=row['region_radius_m']
        if type(radius) not in (int,float) or not math.isfinite(radius) or radius<=0:raise ProjectError('positive finite contact region radius required')
        if mode=='outside_regions' and radius<=4*LINEAR_DEFLECTION_M:raise ProjectError('contact region is too small for the declared mesh resolution')
        a,b=row['from_port_guid'],row['to_port_guid']
        if not isinstance(a,str) or not a or not isinstance(b,str) or not b or a==b:raise ProjectError('distinct port GUIDs required')
        pair=tuple(sorted((a,b)))
        if pair in seen:raise ProjectError('duplicate allowed contact')
        seen.add(pair)
    return policy


def inspect(ifc_path,policy):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.unit as unit
    import ifcopenshell.util.system as system
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.element as element_util
    validate_policy(policy);model=ifcopenshell.open(str(ifc_path))
    roots=model.by_type('IfcRoot');guids=[r.GlobalId for r in roots]
    if any(not isinstance(g,str) or re.fullmatch(r'[0-3][0-9A-Za-z_$]{21}',g) is None for g in guids):raise ProjectError('valid IFC GlobalIds required')
    if len(set(guids))!=len(guids):raise ProjectError('duplicate IFC GlobalIds prevent reliable clash identity')
    projects=model.by_type('IfcProject')
    if len(projects)!=1 or not projects[0].UnitsInContext or len([u for u in projects[0].UnitsInContext.Units if getattr(u,'UnitType',None)=='LENGTHUNIT'])!=1:
        raise ProjectError('one project with one explicit length unit required')
    base=next(u for u in projects[0].UnitsInContext.Units if getattr(u,'UnitType',None)=='LENGTHUNIT');seen_units=set()
    while base.is_a('IfcConversionBasedUnit'):
        if base.id() in seen_units:raise ProjectError('cyclic IFC length conversion')
        seen_units.add(base.id())
        value=base.ConversionFactor.ValueComponent.wrappedValue
        if not math.isfinite(value) or value<=0 or (base.is_a('IfcConversionBasedUnitWithOffset') and base.ConversionOffset!=0):raise ProjectError('unsupported IFC length conversion')
        base=base.ConversionFactor.UnitComponent
    if not base.is_a('IfcSIUnit') or base.Name!='METRE':raise ProjectError('length unit must resolve to explicit SI metres')
    factor=unit.calculate_unit_scale(model)
    if not math.isfinite(factor) or factor<=0:raise ProjectError('known positive IFC length scale required')
    physical=[e for e in model.by_type('IfcElement') if not e.is_a('IfcFeatureElement') and not e.is_a('IfcVirtualElement')]
    elements=[e for e in physical if e.Representation and any(r.Items for r in e.Representation.Representations)]
    if len(elements)<2:raise ProjectError('at least two represented physical elements required')
    selected={e.GlobalId:e for e in elements};allowed={};links={frozenset((r.RelatingPort.GlobalId,r.RelatedPort.GlobalId)) for r in model.by_type('IfcRelConnectsPorts')}
    for row in policy['allowed_contacts']:
        try:a=model.by_guid(row['from_port_guid']);b=model.by_guid(row['to_port_guid'])
        except RuntimeError:raise ProjectError('unknown allowed-contact port GUID')
        if not a.is_a('IfcDistributionPort') or not b.is_a('IfcDistributionPort') or a.FlowDirection!='SOURCE' or b.FlowDirection!='SINK' or frozenset((a.GlobalId,b.GlobalId)) not in links:
            raise ProjectError('contact waiver must reference an actual source-to-sink IFC port connection')
        ea,eb=system.get_port_element(a),system.get_port_element(b)
        if ea is None or eb is None or ea==eb or ea.GlobalId not in selected or eb.GlobalId not in selected:raise ProjectError('contact elements must belong to checked scope')
        if not a.ObjectPlacement or not b.ObjectPlacement:raise ProjectError('contact port placements required')
        pa=placement.get_local_placement(a.ObjectPlacement)[:3,3]*factor;pb=placement.get_local_placement(b.ObjectPlacement)[:3,3]*factor
        if math.dist(pa,pb)>policy['contact_tolerance_m']:raise ProjectError('declared contact ports are not coincident within supplied tolerance')
        key=tuple(sorted((ea.GlobalId,eb.GlobalId)))
        allowed.setdefault(key,[]).append(dict(**row,port_separation_m=math.dist(pa,pb),centre_world_m=pa.tolist()))
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
    tree=ifcopenshell.geom.tree();iterator=ifcopenshell.geom.iterator(settings,model,1,include=elements)
    loaded=set();valid=set();invalid=[];meshes={}
    if iterator.initialize():
        while True:
            shape=iterator.get();obj=model.by_id(shape.id);loaded.add(obj.GlobalId)
            verts=shape.geometry.verts;faces=shape.geometry.faces
            edges=Counter();directions=Counter()
            for i in range(0,len(faces),3):
                a,b,c=faces[i:i+3]
                for x,y in ((a,b),(b,c),(c,a)):edges[tuple(sorted((x,y)))]+=1;directions[(x,y)]+=1
            if not verts or not faces or any(not math.isfinite(v) for v in verts) or any(v!=2 for v in edges.values()) or any(directions[(a,b)]!=1 or directions[(b,a)]!=1 for a,b in edges):
                invalid.append(dict(guid=obj.GlobalId,name=obj.Name,reason='geometry is empty/nonfinite or lacks closed consistently oriented triangle edges'))
            else:tree.add_element(shape);valid.add(obj.GlobalId);meshes[obj.GlobalId]=(list(verts),list(faces))
            if not iterator.next():break
    missing=sorted(set(selected)-loaded)
    def record(clash):
        a,b=clash.a.get_argument(0),clash.b.get_argument(0)
        p1,p2=list(clash.p1),list(clash.p2)
        if a>b:a,b=b,a;p1,p2=p2,p1
        return dict(pair=[a,b],names=[selected[a].Name,selected[b].Name],type=ifcopenshell.geom.CLASH_TYPE_ITEMS[clash.clash_type],
                    engine_distance_m=float(clash.distance),p1_world_m=p1,p2_world_m=p2)
    checked=[e for e in elements if e.GlobalId in valid]
    hard=[record(r) for r in tree.clash_intersection_many(checked,checked,tolerance=policy['intersection_tolerance_m'],check_all=True)] if len(checked)>1 else []
    near=[record(r) for r in tree.clash_clearance_many(checked,checked,clearance=policy['minimum_clearance_m'],check_all=True)] if len(checked)>1 else []
    from .solid_clash import overlaps
    solid_hits,unverified,boolean_count,solid_checks=overlaps(checked,meshes,policy['intersection_tolerance_m'],policy['overlap_volume_tolerance_m3'],policy['maximum_boolean_pairs'])
    hard.extend(solid_hits)
    hard_pairs={tuple(r['pair']) for r in hard};unverified_pairs={tuple(r['pair']) for r in unverified if 'pair' in r}
    unverified_guids={r['guid'] for r in unverified if 'guid' in r};violations=[];accepted=[];region_checks=[]
    mode=policy.get('contact_clearance_mode','minimum_witness_only')
    if mode=='outside_regions' and len(allowed)+boolean_count>policy['maximum_boolean_pairs']:raise ProjectError('solid/contact pair checks exceed explicit budget')
    for row in near:
        pair=tuple(row['pair'])
        scoped=[contact for contact in allowed.get(pair,[]) if all(math.dist(point,contact['centre_world_m'])<=contact['region_radius_m'] for point in (row['p1_world_m'],row['p2_world_m']))]
        if scoped and pair not in hard_pairs and pair not in unverified_pairs and not set(pair)&unverified_guids and row['engine_distance_m']<=policy['contact_tolerance_m']:
            if mode=='outside_regions':
                from .contact_clearance import prove
                proof=prove(pair,meshes,allowed[pair],policy['minimum_clearance_m'],policy['contact_region_segments']);region_checks.append(proof)
                if proof['pass_check']:
                    accepted.append(dict(**row,allowed_contacts=allowed[pair],outside_region_check=proof,
                                         waiver_scope='sourced spherical joint regions only; both conservative outside-to-full clearance checks passed'))
                else:violations.append(dict(**row,outside_region_check=proof,reason='outside-region clearance not proven'))
            else:accepted.append(dict(**row,allowed_contacts=scoped,waiver_scope='pair minimum-clearance exception with witness in sourced region; other pair zones not exhaustively measured'))
        else:violations.append(row)
    coverage=not missing and not invalid and not unverified and len(elements)==len(physical)
    checks=dict(geometry_coverage=coverage,no_intersections=not hard,clearance=not violations)
    import importlib.metadata
    import numpy as np
    element_records=[]
    for e in elements:
        declarations=element_util.get_psets(e).get('BSA_DesignInputs',{})
        element_records.append(dict(guid=e.GlobalId,name=e.Name,ifc_class=e.is_a(),declared_body_shape=declarations.get('BodyShape','unspecified')))
    return dict(ifcopenshell_version=ifcopenshell.version,manifold3d_version=importlib.metadata.version('manifold3d'),numpy_version=np.__version__,scope=policy['scope'],source_length_unit_to_m=factor,
        elements=element_records,
        physical_element_count=len(physical),represented_element_count=len(elements),loaded_geometry_count=len(loaded),valid_geometry_count=len(valid),
        potential_pair_count=len(elements)*(len(elements)-1)//2,missing_geometry_guids=missing,invalid_geometry=invalid,
        unrepresented_elements=[dict(guid=e.GlobalId,name=e.Name) for e in physical if e.GlobalId not in selected],
        intersections=hard,clearance_findings=near,clearance_violations=violations,accepted_contacts=accepted,
        intersection_pair_count=len(hard_pairs),clearance_violation_pair_count=len({tuple(row['pair']) for row in violations}),
        boolean_candidate_count=boolean_count,solid_pair_checks=solid_checks,unverified_solid_pairs=unverified,
        contact_clearance_mode=mode,outside_region_checks=region_checks,
        checks=checks,calculated_checks_pass=all(checks.values()),design_accepted=False,
        mesh_settings=dict(linear_deflection_m=LINEAR_DEFLECTION_M,angular_deflection=ANGULAR_DEFLECTION),
        pending=['triangle approximation and supplied tolerance applicability']+(['non-interface clearances on contact-exempt pairs'] if mode=='minimum_witness_only' and accepted else [])+
                ['envelope versus actual product/insulation fidelity','clearance policy/source review','BIM viewer and complete engineering acceptance'])


def run(ifc_path,policy_path,out):
    ifc_path,policy_path,out=[Path(p).resolve() for p in (ifc_path,policy_path,out)]
    if any(out==p or out in p.parents for p in (ifc_path,policy_path)):raise ProjectError('output must not contain source inputs')
    before={str(p):digest(p) for p in (ifc_path,policy_path)}
    policy=validate_policy(json.loads(policy_path.read_text(encoding='utf-8-sig')));result=inspect(ifc_path,policy)
    out.mkdir(parents=True,exist_ok=False)
    result.update(inputs=before,policy=policy,inputs_unchanged=all(digest(Path(p))==h for p,h in before.items()))
    if not result['inputs_unchanged']:raise ProjectError('source changed during IFC clash analysis')
    rows=''.join('<tr>'+''.join('<td>'+html.escape(str(row.get(key,'')))+'</td>' for key in ('names','type','engine_distance_m','overlap_volume_m3','p1_world_m','p2_world_m'))+'</tr>' for row in result['intersections']+result['clearance_violations'])
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>IFC clash evidence</title><h1>IFC clash evidence</h1><p>'+html.escape(str(result['checks']))+'</p><p>Supplied policy and triangle geometry only; full design acceptance pending.</p><table border="1"><tr><th>Elements</th><th>Type</th><th>Engine distance m</th><th>Mesh overlap m3</th><th>P1 m</th><th>P2 m</th></tr>'+rows+'</table><h2>Accepted contact exceptions</h2><pre>'+html.escape(json.dumps(result['accepted_contacts'],indent=2))+'</pre><h2>Outside-region checks</h2><pre>'+html.escape(json.dumps(result['outside_region_checks'],indent=2))+'</pre><h2>Coverage issues</h2><pre>'+html.escape(json.dumps({k:result[k] for k in ('missing_geometry_guids','invalid_geometry','unrepresented_elements','unverified_solid_pairs')},indent=2))+'</pre><h2>Policy</h2><pre>'+html.escape(json.dumps(policy,indent=2))+'</pre><h2>Pending</h2><ul>'+''.join('<li>'+html.escape(s)+'</li>' for s in result['pending'])+'</ul>',encoding='utf-8')
    result['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
    (out/'clash.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('ifc',type=Path)
    parser.add_argument('--policy',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=run(args.ifc,args.policy,args.out)
    print(json.dumps({k:result[k] for k in ('checks','calculated_checks_pass','design_accepted')}))
    return 0 if result['calculated_checks_pass'] else 2

if __name__=='__main__':raise SystemExit(main())
