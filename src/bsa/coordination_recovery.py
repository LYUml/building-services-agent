"""Read-only recovery requests from already source-verified coordination evidence."""
from collections import defaultdict
from pathlib import Path
import ifcopenshell
import ifcopenshell.util.system as system
import ifcopenshell.util.placement as placement
import ifcopenshell.util.unit as unit
import ifcopenshell.util.element as element
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from .engine import ProjectError


def recover(run,workflow,task):
    """Called only after delivery.context verifies the whole workflow and native replay."""
    run=Path(run).resolve();relative=task+'/terminal-coordination.json'
    if relative not in workflow['artifact_hashes']:return {}
    source=run/relative;expected=workflow['artifact_hashes'][relative]
    if not allowed(source) or digest(source)!=expected:raise ProjectError('Coordination recovery evidence changed')
    report=read_json(source);pins=dict(report['inputs'])
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in pins.items()):raise ProjectError('Coordination recovery source/method changed')
    if report['summary']['status']!=workflow['tasks'][task]['status']:raise ProjectError('Coordination recovery status differs')
    producer=Path(report['terminal_ifc']).resolve();names={'terminal-ifc.json':'Terminal Envelope Study.ifc','terminal-inlets.json':'Terminal Inlet Study.ifc','terminal-stubs.json':'Terminal Stub Study.ifc'}
    if not allowed(producer) or producer.name not in names:raise ProjectError('Exact verified coordination producer required')
    target=producer.parent/names[producer.name]
    if str(target) not in pins or digest(target)!=pins[str(target)]:raise ProjectError('Coordination recovery model differs')
    model=ifcopenshell.open(str(target));scale=unit.calculate_unit_scale(model);graph=defaultdict(set);links=[]
    for relation in model.by_type('IfcRelConnectsPorts'):
        a,b=relation.RelatingPort,relation.RelatedPort;ea,eb=system.get_port_element(a),system.get_port_element(b)
        if ea is None or eb is None:continue
        graph[ea.GlobalId].add(eb.GlobalId)
        ma=placement.get_local_placement(a.ObjectPlacement) if a.ObjectPlacement else None;mb=placement.get_local_placement(b.ObjectPlacement) if b.ObjectPlacement else None
        links.append(dict(from_element_guid=ea.GlobalId,to_element_guid=eb.GlobalId,from_port_guid=a.GlobalId,to_port_guid=b.GlobalId,
            from_flow_direction=a.FlowDirection,to_flow_direction=b.FlowDirection,
            from_point_m=(ma[:3,3]*scale).tolist() if ma is not None else None,to_point_m=(mb[:3,3]*scale).tolist() if mb is not None else None,
            from_outward_axis=ma[:3,2].tolist() if ma is not None else None,to_outward_axis=mb[:3,2].tolist() if mb is not None else None))
    terminals={guid:element.get_psets(model.by_guid(guid))['BSA_SpatialTerminal']['InputID'] for guid in report['summary']['added_terminal_guids']}
    def affected(guids):
        todo=list(guids);seen=set()
        while todo:
            guid=todo.pop()
            if guid in seen:continue
            seen.add(guid);todo.extend(graph[guid]-seen)
        return sorted(terminals[g] for g in seen if g in terminals)
    policy_path=Path(report['policy']).resolve()
    if not allowed(policy_path) or str(policy_path) not in pins or digest(policy_path)!=pins[str(policy_path)]:raise ProjectError('Coordination request policy differs')
    policy=read_json(policy_path)
    calculation=report['calculation'];inventory={r['guid']:r for r in calculation['elements']};groups={}
    for category in ('intersections','clearance_violations'):
        for row in calculation[category]:
            pair=tuple(sorted(row['pair']))
            if len(pair)!=2 or any(g not in inventory for g in pair):raise ProjectError('Coordination finding lacks checked element identity')
            groups.setdefault(pair,dict(intersections=[],clearance_violations=[]))[category].append(row)
    requests=[]
    for pair,findings in sorted(groups.items()):
        direct=[row for row in links if {row['from_element_guid'],row['to_element_guid']}==set(pair)]
        requests.append(dict(id=task+':'+':'.join(pair),code='connected_interface_geometry_policy_review' if direct else 'native_interference_geometry_policy_review',status='open',
            elements=[inventory[g] for g in pair],recorded_direct_port_links=direct,logical_downstream_terminal_ids=affected(pair),
            findings=findings,minimum_clearance_m=policy['minimum_clearance_m'],
            required_evidence=['Source-backed physical connector/opening/neck and insulation geometry for the affected elements',
                'Applicable clearance/contact conditions and any permitted interface region,with source and review evidence',
                'Revised source-bound model/policy and complete native recheck;retain original findings and requirements'],
            scope='A recorded port link is not a physical-cause diagnosis,intended-contact approval or clearance waiver. Downstream IDs follow recorded IFC relations,not proven airflow continuity'))
    for field in ('missing_geometry_guids','invalid_geometry','unrepresented_elements','unverified_solid_pairs'):
        for index,row in enumerate(calculation.get(field,[]),1):
            requests.append(dict(id=task+':'+field+':'+str(index),code='native_geometry_coverage_review',status='open',coverage_field=field,evidence=row,
                required_evidence=['Restore/review source geometry and closed-solid coverage without excluding affected elements','Execute a fresh complete native coordination study'],scope='Coverage issue retained without inventing a physical cause'))
    if not requests:return {}
    pins[str(source)]=expected;pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    if digest(source)!=expected or any(digest(Path(p))!=sha for p,sha in report['inputs'].items()):raise ProjectError('Coordination recovery inputs changed while reading')
    return dict(data_requests=requests,inputs=pins,source_report=relative,source_report_sha256=expected,policy=policy,
        calculation_status=report['summary']['status'],design_accepted=False,
        scope='Retained native findings/coverage and source-acquisition requests only;no automatic repair,waiver,parameter change or design acceptance')
