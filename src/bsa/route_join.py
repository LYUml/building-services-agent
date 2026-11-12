"""Preserve source geometry while joining a verified port-guided route in one IFC."""
import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.element as element
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.unit as unit
import ifcopenshell.validate
import numpy as np

from .cli import digest
from .duct_fitting_chain import shape_hash, properties
from .engine import ProjectError
from .module_contract import read_json
from .route_model import endpoint_frames
from .workspace import allowed


def snapshot(model):
    objects = {o.GlobalId: dict(ifc_class=o.is_a(), name=o.Name,
        shape_sha256=shape_hash(o), properties=properties(o),
        frame=placement.get_local_placement(o.ObjectPlacement).tolist(),
        container=element.get_container(o).GlobalId if element.get_container(o) else None)
        for o in model.by_type('IfcElement')}
    ports = {}
    for p in model.by_type('IfcDistributionPort'):
        owner = system.get_port_element(p)
        if owner is None or owner.GlobalId not in objects:
            raise ProjectError('Every source port needs an owned element')
        ports[p.GlobalId] = dict(owner=owner.GlobalId, name=p.Name, direction=p.FlowDirection,
            predefined_type=p.PredefinedType, system_type=p.SystemType,
            frame=placement.get_local_placement(p.ObjectPlacement).tolist())
    systems = {s.GlobalId: dict(predefined_type=s.PredefinedType,
        members=sorted(o.GlobalId for o in system.get_system_elements(s)))
        for s in model.by_type('IfcDistributionSystem')}
    links = sorted([r.RelatingPort.GlobalId, r.RelatedPort.GlobalId] for r in model.by_type('IfcRelConnectsPorts'))
    roots = [r.GlobalId for r in model.by_type('IfcRoot')]
    if len(roots) != len(set(roots)) or len(objects) != len(model.by_type('IfcElement')) or len(ports) != len(model.by_type('IfcDistributionPort')):
        raise ProjectError('Unique source IFC element/port/root identities required')
    return dict(objects=objects, ports=ports, systems=systems, links=links, roots=roots)


def inspect(target, expected):
    model = ifcopenshell.open(str(target))
    actual = snapshot(model)
    for section in ('objects', 'ports'):
        if set(actual[section]) != set(expected[section]):
            raise ProjectError('Saved merged element/port inventory differs')
        for guid, row in expected[section].items():
            record = actual[section][guid]
            if any(record[k] != v for k, v in row.items() if k != 'frame') or not np.allclose(record['frame'], row['frame'], atol=1e-9, rtol=0):
                raise ProjectError('Saved source shape, properties, placement or port ownership differs')
    if actual['systems'] != expected['systems'] or actual['links'] != expected['links'] or not set(expected['roots']).issubset(actual['roots']):
        raise ProjectError('Saved merged system, links or original roots differ')
    degree = Counter(p for pair in actual['links'] for p in pair)
    if any(n != 1 for n in degree.values()):
        raise ProjectError('Connected port must have exactly one peer')
    for a, b in actual['links']:
        first, second = (actual['ports'][p] for p in (a, b))
        fa, fb = (np.asarray(r['frame']) for r in (first, second))
        if first['direction'] != 'SOURCE' or second['direction'] != 'SINK' or not np.allclose(fa[:3, 3], fb[:3, 3], atol=1e-8, rtol=0) or not np.allclose(fa[:3, 2], -fb[:3, 2], atol=1e-8, rtol=0):
            raise ProjectError('Saved directed interface requires coincident caps and opposed normals')
    nodes = set(expected['local_chain_owners'])
    neighbours = {n: set() for n in nodes}
    local_edges = []
    for a, b in actual['links']:
        first, second = (actual['ports'][p]['owner'] for p in (a, b))
        if first in nodes and second in nodes:
            neighbours[first].add(second); neighbours[second].add(first); local_edges.append((first, second))
    pending = [next(iter(nodes))]; seen = set()
    while pending:
        node = pending.pop()
        if node not in seen:
            seen.add(node); pending.extend(neighbours[node]-seen)
    if seen != nodes or len(local_edges) != len(nodes)-1:
        raise ProjectError('Selected source owners and every route body must form one local chain')
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, logger, express_rules=True)
    if logger.statements:
        raise ProjectError('Saved joined IFC schema/EXPRESS validation failed')
    return dict(source_geometry_properties_frames_preserved=True, exact_element_port_inventory=True,
                exact_directed_links=True, shared_source_system=True, local_chain_connected=True,
                schema_valid=True, local_chain_body_count=len(nodes), connection_count=len(actual['links']))


def merge(source, route, target, endpoints, frames):
    """Append existing assets unchanged; add explicit logical cap connections only."""
    model, library = (ifcopenshell.open(str(p)) for p in (source, route))
    for f in (model, library):
        if f.schema != 'IFC4' or len(f.by_type('IfcProject')) != 1 or not np.isclose(unit.calculate_unit_scale(f), 1., atol=1e-12, rtol=0):
            raise ProjectError('One IFC4 metre project required in both source files')
    before, added = snapshot(model), snapshot(library)
    if set(before['roots']) & set(added['roots']):
        raise ProjectError('Source and route identities overlap')
    selected = [model.by_guid(endpoints[r]['owner_guid']) for r in ('start', 'end')]
    memberships = [system.get_element_systems(o) for o in selected]
    containers = [element.get_container(o) for o in selected]
    if any(len(m) != 1 for m in memberships) or memberships[0][0] != memberships[1][0] or containers[0] is None or containers[0] != containers[1]:
        raise ProjectError('Source endpoint owners must share exact system and spatial container')
    distribution, container = memberships[0][0], containers[0]
    pairs = [(endpoints['start']['port_guid'], frames['start']['port_guid']),
             (frames['end']['port_guid'], endpoints['end']['port_guid'])]
    for role in ('start', 'end'):
        p = model.by_guid(endpoints[role]['port_guid'])
        if p.ConnectedTo or p.ConnectedFrom:
            raise ProjectError('Selected source port became occupied')
    identities = {}
    for obj in library.by_type('IfcElement'):
        imported = api.run('project.append_asset', model, library=library, element=obj,
                           reuse_identities=identities, assume_asset_uniqueness_by_name=False)
        api.run('spatial.assign_container', model, products=[imported], relating_structure=container)
        api.run('system.assign_system', model, products=[imported], system=distribution)
    if sorted([r.RelatingPort.GlobalId, r.RelatedPort.GlobalId] for r in model.by_type('IfcRelConnectsPorts')) != before['links']:
        raise ProjectError('Unexpected upstream asset connection import')
    for a, b in added['links'] + [list(p) for p in pairs]:
        api.run('system.connect_port', model, port1=model.by_guid(a), port2=model.by_guid(b), direction='SOURCE')
    expected = dict(objects={**before['objects'], **added['objects']}, ports={**before['ports'], **added['ports']},
                    systems=before['systems'], roots=before['roots'], links=sorted(before['links'] + added['links'] + [list(p) for p in pairs]),
                    local_chain_owners=sorted(set(added['objects']) | {o.GlobalId for o in selected}))
    for guid in added['objects']:
        expected['objects'][guid]['container'] = container.GlobalId
    expected['systems'][distribution.GlobalId]['members'] = sorted(set(expected['systems'][distribution.GlobalId]['members']) | set(added['objects']))
    model.write(str(target))
    return inspect(target, expected), expected


def run(producer, out):
    producer, out = Path(producer).resolve(), Path(out).resolve()
    if out.exists() or not all(allowed(p) for p in (producer, out)) or producer == out or out in producer.parents or producer in out.parents:
        raise ProjectError('Fresh output outside original source route folder required')
    if importlib.metadata.version('ifcopenshell') != '0.8.5':
        raise ProjectError('Pinned IfcOpenShell runtime required')
    receipt = producer/'port-route.json'; report = read_json(receipt)
    if report.get('saved_endpoint_correspondence') is not True or report.get('calculated_checks_pass') is not True or report.get('design_accepted') is not False:
        raise ProjectError('Passing source-port route required before joining')
    inputs = {str(receipt): digest(receipt), **report['inputs'], **report['method_inputs']}
    route_report = producer/'route/route-optimisation.json'
    if digest(route_report) != report['route_report_sha256']:
        raise ProjectError('Selected route report changed')
    inputs[str(route_report)] = digest(route_report)
    selected = producer/'route/selected'; native = read_json(selected/'route-model.json')
    inputs[str(selected/'route-model.json')] = digest(selected/'route-model.json')
    if read_json(route_report).get('selected_model') != native or native.get('saved_ifc_geometry_match') is not True or native.get('calculated_checks_pass') is not True:
        raise ProjectError('Exact passing native selected-model report required')
    inputs.update(native['inputs']); inputs.update(native['method_inputs'])
    bound = read_json(selected/'bound/network-binding.json')
    inputs.update(bound['inputs'])
    inputs[str(selected/'bound/network-binding.json')] = digest(selected/'bound/network-binding.json')
    for name, sha in bound['artifacts'].items():
        path = (selected/'bound'/name).resolve()
        if not path.is_relative_to(selected/'bound'):
            raise ProjectError('Bound artifact escapes selected route')
        inputs[str(path)] = sha
    sources = [Path(p) for p in report['inputs'] if Path(p).suffix.lower() == '.ifc']
    if len(sources) != 1:
        raise ProjectError('One exact original source IFC required')
    for path, sha in inputs.items():
        if not allowed(Path(path)) or digest(Path(path)) != sha:
            raise ProjectError('Source route input, method or artifact changed')
    methods = {str(Path(p).resolve()): digest(Path(p)) for p in (__file__, shape_hash.__code__.co_filename, endpoint_frames.__code__.co_filename)}
    source = sources[0]; route = selected/'bound/bim/model.ifc'
    settings_paths = [Path(p) for p in native['inputs'] if isinstance(read_json(Path(p)), dict) and 'plane_frame' in read_json(Path(p))]
    if len(settings_paths) != 1:
        raise ProjectError('One exact source plane settings file required')
    frames = endpoint_frames(route, read_json(selected/'binding-input.json'), read_json(selected/'network-source.json'),
                             read_json(producer/'route/selected-routing.json'), read_json(settings_paths[0]))
    for role in ('start', 'end'):
        if not np.allclose(frames[role]['point_m'], report['endpoints'][role]['point_m'], atol=1e-8, rtol=0) or not np.allclose(frames[role]['travel_direction'], report['endpoints'][role]['travel_direction'], atol=1e-8, rtol=0):
            raise ProjectError('Current route endpoints differ from original source')
    out.mkdir(parents=True)
    checks, expected = merge(source, route, out/'joined.ifc', report['endpoints'], frames)
    if any(digest(Path(p)) != sha for p, sha in {**inputs, **methods}.items()):
        raise ProjectError('Join source or method changed during execution')
    (out/'source-snapshot.json').write_text(json.dumps(expected, indent=2), encoding='utf-8')
    result = dict(inputs=inputs, method_inputs=methods, checks=checks,
                  ifc_sha256=digest(out/'joined.ifc'), snapshot_sha256=digest(out/'source-snapshot.json'),
                  calculated_checks_pass=True, design_accepted=False,
                  scope='Saved same-file local logical chain; no physical joint, whole-network pressure, clearance, manufacturer or regulatory acceptance')
    (out/'route-join.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('producer', type=Path); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(run(args.producer, args.out), indent=2))
