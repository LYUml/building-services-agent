"""Group verified native clashes by original unresolved source connections; no waivers."""
import argparse
from collections import defaultdict,Counter
import json
from pathlib import Path
from . import elbow_radius_selection,clash
from .cli import digest
from .workspace import allowed


def pair_signature(result):
    """Semantic pair inventory; engine witnesses are recomputed, not accepted from file."""
    def quantity(row,key,digits):
        value=row.get(key)
        return None if value is None else round(value,digits)
    def rows(name):
        return sorted((tuple(sorted(r['pair'])),r.get('type'),quantity(r,'overlap_volume_m3',12),quantity(r,'engine_distance_m',9)) for r in result[name])
    return {k:rows(k) for k in ('intersections','clearance_violations')}|dict(checks=result['checks'],coverage=[result[k] for k in ('physical_element_count','represented_element_count','loaded_geometry_count','valid_geometry_count')])


def calculate(junction,fit,report,names,links):
    if len(set(names.values()))!=len(names):raise ValueError('Unique native element names required')
    nodes={r['node']:r for r in junction['nodes']}
    pending={r['node']:r['requirement'] for r in fit['remaining_source_connection_nodes']}
    if any(n not in nodes or nodes[n]['connection_requirement']!=v for n,v in pending.items()):raise ValueError('Pending source connections differ from original junctions')
    incidents={n:{i['section'] for i in row['incidents']} for n,row in nodes.items()}
    def grouping(records,kind):
        grouped=defaultdict(list)
        for record in records:
            pair=tuple(sorted(record['pair']))
            if len(pair)!=2 or pair[0]==pair[1] or any(g not in names for g in pair) or set(record['names'])!={names[g] for g in pair}:raise ValueError('Clash pair differs from actual native identity')
            grouped[pair].append(record)
        result=[]
        for pair,rows in sorted(grouped.items()):
            body_names=sorted(names[g] for g in pair);common=sorted(n for n,sections in incidents.items() if set(body_names)<=sections);unresolved=[n for n in common if n in pending]
            linked=pair in links
            association=('linked_interface_'+kind if linked else 'unresolved_source_connection' if unresolved else 'source_adjacent_interference' if common else 'nonadjacent_interference')
            result.append(dict(pair=list(pair),elements=body_names,association=association,source_nodes=common,unresolved_source_nodes=unresolved,record_count=len(rows),record_types=dict(Counter(r.get('type','unspecified') for r in rows)),reported_overlap_volume_m3=[r['overlap_volume_m3'] for r in rows if 'overlap_volume_m3' in r],waived=False,engineering_accepted=False))
        return result
    intersections=grouping(report['intersections'],'intersection');clearance=grouping(report['clearance_violations'],'clearance')
    actions=[]
    for name,requirement in sorted(pending.items()):
        row=nodes[name]
        actions.append(dict(source_node=name,connection_requirement=requirement,incidents=row['incidents'],
            intersection_pairs=[r['elements'] for r in intersections if name in r['unresolved_source_nodes']],
            clearance_pairs=[r['elements'] for r in clearance if name in r['unresolved_source_nodes']],
            requested='Author and verify the source connection and both-end trim budgets while retaining original section IDs, dimensions and flows; rerun complete native coordination.',
            candidate_building_block='rectangular_tee_transitions' if requirement=='unequal_section_tee_required' else None,
            node_specific_authoring_executed=False,status='pending'))
    return dict(status='coordination_failed' if not report['calculated_checks_pass'] else 'review_required',
        raw_checks=report['checks'],raw_intersection_records=len(report['intersections']),unique_intersection_pairs=len(intersections),
        raw_clearance_records=len(report['clearance_violations']),unique_clearance_pairs=len(clearance),
        intersection_associations=dict(Counter(r['association'] for r in intersections)),
        clearance_associations=dict(Counter(r['association'] for r in clearance)),
        intersections=intersections,clearance=clearance,engineering_actions=actions,
        remaining_source_connections=len(actions),design_accepted=False,
        scope='Source-incidence association of independently replayed native clash pairs; not causal proof, a contact exemption, connection authoring or installation/pressure approval')


def run(selection,raw_clash,out):
    selection,raw_clash,out=[Path(p).resolve() for p in (selection,raw_clash,out)]
    if not all(allowed(p) for p in (selection,raw_clash,out)) or out.exists() or out==raw_clash or out in raw_clash.parents or out.is_relative_to(selection) or selection.is_relative_to(out) or out.is_relative_to(raw_clash.parent) or raw_clash.parent.is_relative_to(out):raise ValueError('Fresh selected workspace outside source runs required')
    elbow_radius_selection.verify(selection)
    selected=json.loads((selection/'selection.json').read_text());ifc=selection/'native/Supply Backbone.ifc';saved=json.loads(raw_clash.read_text())
    if selected['status']!='candidate_selected' or saved['inputs'].get(str(ifc))!=digest(ifc):raise ValueError('Raw clash must reference the exact selected native IFC')
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in saved['inputs'].items()):raise ValueError('Raw clash source or policy changed')
    policy_paths=[Path(p) for p in saved['inputs'] if Path(p)!=ifc]
    if len(policy_paths)!=1 or json.loads(policy_paths[0].read_text())!=saved['policy']:raise ValueError('Raw clash policy differs from source')
    files=[selection/'selection.json',selection/'junction.json',ifc,raw_clash,*policy_paths,Path(__file__),Path(clash.__file__),Path(elbow_radius_selection.__file__)]
    pins={str(p):digest(p) for p in files}
    policy=clash.validate_policy(saved['policy']);fresh=clash.inspect(ifc,policy)
    if pair_signature(saved)!=pair_signature(fresh):raise ValueError('Recorded clash pair inventory differs from native replay')
    import ifcopenshell
    import ifcopenshell.util.system as system
    model=ifcopenshell.open(str(ifc));names={e.GlobalId:e.Name for e in model.by_type('IfcDistributionElement')}
    links={tuple(sorted([system.get_port_element(r.RelatingPort).GlobalId,system.get_port_element(r.RelatedPort).GlobalId])) for r in model.by_type('IfcRelConnectsPorts')}
    result=calculate(json.loads((selection/'junction.json').read_text()),selected['fit'],fresh,names,links)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Coordination source changed during native replay')
    result.update(inputs=pins,original_requirement_ids=[r['id'] for r in json.loads((selection/'native/elbow-backbone.json').read_text())['original_requirements']],
        coordinate_scope='Interpreted source CAD metres and classified study elevation; not surveyed installation',policy_unchanged=True,source_unchanged=True)
    out.mkdir(parents=True);(out/'native-clash-replay.json').write_text(json.dumps(fresh,indent=2));(out/'diagnosis.json').write_text(json.dumps(result,indent=2))
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Coordination source changed during diagnosis')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('selection');p.add_argument('clash');p.add_argument('--out',required=True);a=p.parse_args();r=run(a.selection,a.clash,a.out)
    print(json.dumps({k:r[k] for k in ('status','unique_intersection_pairs','intersection_associations','remaining_source_connections','design_accepted')},indent=2));return 2

if __name__=='__main__':raise SystemExit(main())
