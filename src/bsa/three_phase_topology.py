"""Verify saved IFC cable-to-board port relationships against a numerical graph."""
import argparse
from collections import Counter
import json
from pathlib import Path

from .cli import digest
from .engine import ProjectError
from .three_phase import prepare,fields,ROOT
from .three_phase_ifc import inspect as inspect_geometry


def topology_source(topology,ifc):
    topology=Path(topology).resolve()
    t=json.loads(topology.read_text(encoding='utf-8-sig'))
    fields(t,'version ifc_sha256 internal_bus_model source buses')
    if type(t['version']) is not int or t['version']!=1 or t['ifc_sha256']!=digest(ifc):raise ProjectError('version 1 topology and exact IFC hash required')
    if t['internal_bus_model']!='ideal common electrical node':raise ProjectError('explicit ideal common electrical node model required')
    source=t['source'];fields(source,'path sha256 kind locator')
    if not isinstance(source['path'],str) or Path(source['path']).is_absolute():raise ProjectError('relative topology source required')
    source_path=(topology.parent/source['path']).resolve()
    if not source_path.is_relative_to(topology.parent) or not source_path.is_file() or digest(source_path)!=source['sha256']:raise ProjectError('topology source path/hash mismatch')
    if source['kind'] not in ('assumption','measured','manufacturer','course_given','design_target') or not isinstance(source['locator'],str) or not source['locator'].strip():raise ProjectError('explicit topology source kind/locator required')
    return t,source_path


def inputs(project,ifc,binding,topology):
    from .three_phase_ifc import inputs as geometry_inputs
    _,source_path=topology_source(topology,ifc)
    return geometry_inputs(project,ifc,binding)|{Path(topology).resolve(),source_path,Path(__file__).resolve()}


def inspect(project,ifc,binding,topology):
    import ifcopenshell
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system
    import ifcopenshell.util.unit as unit
    import numpy as np
    project,ifc,binding,topology=[Path(v).resolve() for v in (project,ifc,binding,topology)]
    geometry=inspect_geometry(project,ifc,binding)
    p,_=prepare(project)
    b=json.loads(binding.read_text(encoding='utf-8-sig'))
    t,source_path=topology_source(topology,ifc);source=t['source']
    before={**geometry['inputs'],str(topology):digest(topology),str(source_path):digest(source_path),str(Path(__file__).resolve()):digest(Path(__file__))}
    if not isinstance(t['buses'],dict) or set(t['buses'])!={bus['id'] for bus in p['buses']}:raise ProjectError('exact board/bus coverage required')
    model=ifcopenshell.open(str(ifc));selected=model.by_guid(b['system_guid']);factor=unit.calculate_unit_scale(model)
    expected=Counter();board_guids=set();port_guids=set();rows=[]
    cable_guids={line['element_guid'] for line in b['lines'].values()}
    all_ports={guid for value in b['lines'].values() for guid in (value['from_port_guid'],value['to_port_guid'])}
    expected_owners={value[key]:value['element_guid'] for value in b['lines'].values() for key in ('from_port_guid','to_port_guid')}
    for bus in p['buses']:
        name=bus['id'];role=t['buses'][name];fields(role,'element_guid ports')
        board=model.by_guid(role['element_guid'])
        if not board or not board.is_a('IfcElectricDistributionBoard') or board.PredefinedType!='DISTRIBUTIONBOARD':raise ProjectError('explicit distribution-board object required for each analysis bus')
        if board.GlobalId in board_guids or board.GlobalId in cable_guids:raise ProjectError('distinct board per analysis bus required')
        board_guids.add(board.GlobalId)
        if {s.GlobalId for s in system.get_element_systems(board)}!={selected.GlobalId}:raise ProjectError('board must belong only to selected electrical system')
        incident={line['id']:line for line in p['lines'] if name in (line['from'],line['to'])}
        if not isinstance(role['ports'],dict) or set(role['ports'])!=set(incident):raise ProjectError('exact incident-line board port coverage required')
        owned=system.get_ports(board)
        if len(owned)!=len(incident) or {port.GlobalId for port in owned}!=set(role['ports'].values()):raise ProjectError('board port ownership/count mismatch')
        for line_id,line in incident.items():
            guid=role['ports'][line_id]
            if guid in port_guids or guid in all_ports:raise ProjectError('unique board port per cable end required')
            port_guids.add(guid);port=model.by_guid(guid)
            expected_owners[guid]=board.GlobalId
            if system.get_port_element(port)!=board or port.PredefinedType!='CABLE' or port.SystemType!='ELECTRICAL' or port.FlowDirection!='SOURCEANDSINK':raise ProjectError('owned bidirectional electrical cable port required')
            if not port.ObjectPlacement:raise ProjectError('explicit placed board port required')
            point=placement.get_local_placement(port.ObjectPlacement)[:3,3]*factor
            if not np.allclose(point,b['buses'][name],atol=1e-6,rtol=0):raise ProjectError('board port differs from cable/analysis bus anchor')
            cable_port=b['lines'][line_id]['from_port_guid' if line['from']==name else 'to_port_guid']
            expected[guid,cable_port]+=1;expected[cable_port,guid]+=1
            rows.append(dict(bus=name,line=line_id,board_guid=board.GlobalId,board_port_guid=guid,cable_port_guid=cable_port))
    all_ports|=port_guids
    for guid in all_ports:
        owners=[relation.RelatingObject.GlobalId for relation in model.by_guid(guid).Nests]
        if owners!=[expected_owners[guid]]:raise ProjectError('each selected port must have exactly one declared nesting owner')
    elements={obj.GlobalId for obj in system.get_system_elements(selected)}
    if elements!=board_guids|cable_guids:raise ProjectError('selected electrical system contains unmapped elements')
    actual=Counter()
    for relation in model.by_type('IfcRelConnectsPorts'):
        a,bp=relation.RelatingPort,relation.RelatedPort
        if a.GlobalId in all_ports or bp.GlobalId in all_ports:
            if relation.RealizingElement is not None:raise ProjectError('implicit realizing elements are unsupported')
            actual[a.GlobalId,bp.GlobalId]+=1
    if actual!=expected:raise ProjectError('saved port relationships differ from exact bidirectional cable/board graph')
    if any(not Path(f).is_file() or digest(Path(f))!=sha for f,sha in before.items()):raise ProjectError('inputs changed during topology inspection')
    return dict(inputs=before,input_unchanged=True,source_basis=source,internal_bus_model=t['internal_bus_model'],
                geometry_correspondence_pass=True,native_port_relationships_pass=True,logical_graph_correspondence_pass=True,
                bus_count=len(board_guids),cable_count=len(cable_guids),directed_relationship_count=sum(actual.values()),connections=rows,
                physical_installation_verified=False,design_accepted=False,
                scope='Saved cable/board port relationships and ideal common-node numerical graph only; busbar internals, physical terminals/conductors, load devices, protection and installation acceptance remain unverified')


def run(project,ifc,binding,topology,out):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ProjectError('new repository output required')
    result=inspect(project,ifc,binding,topology)
    if any(out==Path(f) or out in Path(f).parents for f in result['inputs']):raise ProjectError('output must not contain inputs')
    out.mkdir(parents=True)
    (out/'topology.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    for name in ('ifc','binding','topology','out'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();result=run(a.project,a.ifc,a.binding,a.topology,a.out)
    print(json.dumps({k:result[k] for k in ('native_port_relationships_pass','logical_graph_correspondence_pass','design_accepted')}))
