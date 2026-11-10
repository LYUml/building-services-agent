"""Merge a fresh source-bound span and its endpoint fittings into one directed IFC tree."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import re

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.element as element
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.unit as unit
import ifcopenshell.validate
import manifold3d as m
import numpy as np

from . import duct_fitting_span as span_tool
from .cli import digest
from .solid_clash import from_mesh
from .cad_ifc import mesh_properties
from .rectangular_tee_transitions import relative_placement
from .tee_geometry import stable_guid

ROOT = Path(__file__).resolve().parents[2]
KEY = 'SOURCE-BOUND-DUCT-CHAIN'
FRAME_TOLERANCE = 1e-9


def source_files(project):
    """Discover the actual immutable source chain for unified-workflow pinning."""
    from .workflow import verify
    from . import rectangular_tee_transitions as composition
    project, _, plan, workflow, ends = span_tool.prepare(project)
    if not verify(workflow)['integrity_pass']: raise ValueError('Source native workflow changed')
    report = json.loads((workflow/'workflow.json').read_text(encoding='utf-8'))
    files = {project, plan, workflow/'workflow.json'}
    files.update(Path(p).resolve() for section in ('inputs', 'runtime_inputs') for p in report.get(section, {}))
    for name in report['artifact_hashes']:
        path = (workflow/name).resolve()
        if not path.is_relative_to(workflow): raise ValueError('Source artifact escaped native workflow')
        files.add(path)
    for end in ends:
        cp, _, tee_source, _, _ = composition.prepare(end['project'])
        files.update((cp, tee_source, end['binding'], end['model']/'assembly.json', end['model']/'assembly.ifc'))
        bundle = json.loads((end['model']/'assembly.json').read_text(encoding='utf-8'))
        for name in bundle['source_artifacts']:
            path = (end['model']/name).resolve()
            if not path.is_relative_to(end['model']): raise ValueError('Source component artifact escaped model')
            files.add(path)
        files.update(Path(p).resolve() for p in bundle['inputs'])
    if any(not p.is_file() for p in files): raise ValueError('Complete source chain files required')
    return files


def value(item):
    """Forward native geometry attributes, with no STEP entity identifiers."""
    if isinstance(item, ifcopenshell.entity_instance):
        return [item.is_a(), [(item.attribute_name(i), value(v)) for i, v in enumerate(item) if item.attribute_name(i) != 'ContextOfItems']]
    if isinstance(item, (tuple, list)): return [value(v) for v in item]
    return item


def shape_hash(obj):
    return hashlib.sha256(json.dumps(value(obj.Representation), ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def properties(obj):
    return {name: {k: v for k, v in props.items() if k != 'id'} for name, props in element.get_psets(obj).items()}


def native_port_frames(obj):
    """Read actual cap stations from the three supported native source bodies."""
    body = obj.Representation.Representations[0].Items[0]
    def frame(point, normal=(0., 0., 1.), width=(1., 0., 0.)):
        matrix = np.eye(4); matrix[:3, :3] = np.column_stack((width, np.cross(normal, width), normal)); matrix[:3, 3] = point
        return matrix
    if obj.is_a('IfcDuctSegment') and body.is_a('IfcExtrudedAreaSolid'):
        if not np.allclose(placement.get_axis2placement(body.Position), np.eye(4), atol=1e-10, rtol=0) or tuple(body.ExtrudedDirection.DirectionRatios) != (0., 0., 1.): raise ValueError('Canonical source straight extrusion required')
        return {'near': frame((0, 0, 0), (0, 0, -1)), 'far': frame((0, 0, body.Depth))}
    if obj.is_a('IfcDuctFitting') and obj.PredefinedType == 'JUNCTION':
        main = body.FirstOperand.FirstOperand; branch = body.FirstOperand.SecondOperand
        z0 = main.Position.Location.Coordinates[2]
        return {'main-a': frame((0, 0, z0), (0, 0, -1)), 'main-b': frame((0, 0, z0+main.Depth)),
            'branch': frame((branch.Depth, 0, 0), (1, 0, 0), (0, 0, -1))}
    if obj.is_a('IfcDuctFitting') and obj.PredefinedType == 'TRANSITION':
        points = [p.Coordinates for face in body.FirstOperand.Outer.CfsFaces for bound in face.Bounds for p in bound.Bound.Polygon]
        return {'start': frame((0, 0, min(p[2] for p in points)), (0, 0, -1)), 'end': frame((0, 0, max(p[2] for p in points)))}
    raise ValueError('Unsupported source body for native end-face reconstruction')


def snapshot(paths):
    objects = {}; ports = {}; links = set(); libraries = []
    settings = ifcopenshell.geom.settings(); settings.set(settings.USE_WORLD_COORDS, False)
    for path in paths:
        library = ifcopenshell.open(str(path)); libraries.append((Path(path), library))
        if library.schema != 'IFC4' or len(library.by_type('IfcProject')) != 1 or not math.isclose(unit.calculate_unit_scale(library), 1, rel_tol=0, abs_tol=1e-12): raise ValueError('Source IFC4 metre projects required; units are not silently mixed')
        for obj in library.by_type('IfcElement'):
            if not obj.is_a('IfcDistributionElement') or obj.GlobalId in objects: raise ValueError('Unique source distribution bodies required')
            shape = ifcopenshell.geom.create_shape(settings, obj)
            mass = mesh_properties(np.asarray(shape.geometry.verts).reshape(-1, 3), np.asarray(shape.geometry.faces).reshape(-1, 3))
            objects[obj.GlobalId] = dict(ifc_class=obj.is_a(), name=obj.Name, predefined_type=obj.PredefinedType,
                frame=placement.get_local_placement(obj.ObjectPlacement).tolist(), shape_sha256=shape_hash(obj), properties=properties(obj),
                native_volume_m3=float(mass['volume']), source_ifc=str(path))
            canonical = native_port_frames(obj)
            if {p.Name for p in system.get_ports(obj)} != set(canonical): raise ValueError('Supported native body end-port coverage required')
            for port in system.get_ports(obj):
                if port.GlobalId in ports or port.FlowDirection not in ('SOURCE', 'SINK'): raise ValueError('Unique directed source ports required')
                frame = placement.get_local_placement(port.ObjectPlacement)
                local = placement.get_axis2placement(port.ObjectPlacement.RelativePlacement) if port.ObjectPlacement.PlacementRelTo == obj.ObjectPlacement else np.linalg.inv(placement.get_local_placement(obj.ObjectPlacement)) @ frame
                if not np.allclose(local, canonical[port.Name], atol=FRAME_TOLERANCE, rtol=0): raise ValueError('Source port does not match its actual native cap')
                ports[port.GlobalId] = dict(owner=obj.GlobalId, name=port.Name, direction=port.FlowDirection,
                    predefined_type=port.PredefinedType, system_type=port.SystemType, frame=frame.tolist(), local_frame=canonical[port.Name].tolist(),
                    source_cap_port_numeric_difference=float(np.max(np.abs(local-canonical[port.Name]))))
        links.update((r.RelatingPort.GlobalId, r.RelatedPort.GlobalId) for r in library.by_type('IfcRelConnectsPorts'))
    if not objects or not ports: raise ValueError('Nonempty source geometry/port coverage required')
    return dict(objects=objects, ports=ports, links=sorted(links)), libraries


def solve_frames(expected):
    objects, ports = expected['objects'], expected['ports']; incoming = {}; outgoing = {}
    for a, b in expected['links']:
        if a not in ports or b not in ports or ports[a]['direction'] != 'SOURCE' or ports[b]['direction'] != 'SINK': raise ValueError('Source-to-sink owned connection required')
        source, target = ports[a]['owner'], ports[b]['owner']
        if source == target or target in incoming: raise ValueError('Directed tree product parent required')
        incoming[target] = (a, b); outgoing.setdefault(source, []).append((a, b))
    roots = set(objects)-set(incoming)
    if len(roots) != 1 or len(expected['links']) != len(objects)-1: raise ValueError('One connected directed product tree required')
    root = next(iter(roots)); matrices = {root: np.asarray(objects[root]['frame'])}; parents = {}; local = {}; order = []; queue = [root]
    for owner in queue:
        order.append(owner)
        for a, b in outgoing.get(owner, []):
            other = ports[b]['owner']
            if other in matrices: raise ValueError('Cycle in directed product tree')
            first, second = (np.asarray(ports[p]['frame']) for p in (a, b))
            if not np.allclose(first[:3, 3], second[:3, 3], atol=FRAME_TOLERANCE, rtol=0) or not np.allclose(first[:3, 2], -second[:3, 2], atol=FRAME_TOLERANCE, rtol=0): raise ValueError('Source interface end planes differ')
            width = float(np.dot(first[:3, 0], second[:3, 0])); height = float(np.dot(first[:3, 1], second[:3, 1]))
            if not math.isclose(abs(width), 1, abs_tol=FRAME_TOLERANCE, rel_tol=0) or not math.isclose(height, -width, abs_tol=FRAME_TOLERANCE, rel_tol=0): raise ValueError('Matching rectangular interface rolls required')
            sign = 1. if width > 0 else -1.
            flip = np.diag([sign, -sign, -1., 1.])
            relative = np.asarray(ports[a]['local_frame']) @ flip @ np.linalg.inv(np.asarray(ports[b]['local_frame']))
            local[other] = relative; parents[other] = owner; matrices[other] = matrices[owner] @ relative; queue.append(other)
    if set(matrices) != set(objects): raise ValueError('Disconnected product graph')
    for guid, matrix in matrices.items():
        if not np.allclose(matrix, objects[guid]['frame'], atol=FRAME_TOLERANCE, rtol=0): raise ValueError('Frame-solved product differs from saved source placement')
    return root, order, matrices, parents, local


def inspect(path, data, expected):
    model = ifcopenshell.open(str(path)); logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, logger, express_rules=True)
    if logger.statements: raise ValueError('Saved chain schema/EXPRESS issues')
    roots = model.by_type('IfcRoot'); guids = [r.GlobalId for r in roots]
    if len(set(guids)) != len(guids) or any(not isinstance(g, str) or re.fullmatch(r'[0-3][0-9A-Za-z_$]{21}', g) is None for g in guids): raise ValueError('Unique valid root GUIDs required')
    products = {o.GlobalId: o for o in model.by_type('IfcElement')}; ports = {p.GlobalId: p for p in model.by_type('IfcDistributionPort')}
    if set(products) != set(expected['objects']) or len(model.by_type('IfcElement')) != len(products) or set(ports) != set(expected['ports']): raise ValueError('Exact saved component/port inventory required')
    root, order, matrices, parents, local = solve_frames(expected)
    settings = ifcopenshell.geom.settings(); settings.set(settings.USE_WORLD_COORDS, False)
    solids = {}; pose_errors = []
    root_relative = {root: np.eye(4)}
    for guid in order:
        obj = products[guid]; source = expected['objects'][guid]
        if obj.is_a() != source['ifc_class'] or obj.Name != source['name'] or obj.PredefinedType != source['predefined_type'] or shape_hash(obj) != source['shape_sha256'] or properties(obj) != source['properties']: raise ValueError('Imported component native shape/type/source properties differ')
        matrix = placement.get_local_placement(obj.ObjectPlacement)
        if not np.allclose(matrix, source['frame'], atol=FRAME_TOLERANCE, rtol=0): raise ValueError('Saved source product placement differs')
        pose_errors.append(float(np.max(np.abs(matrix-np.asarray(source['frame'])))))
        if guid in parents:
            if obj.ObjectPlacement.PlacementRelTo != products[parents[guid]].ObjectPlacement or not np.allclose(placement.get_axis2placement(obj.ObjectPlacement.RelativePlacement), local[guid], atol=1e-10, rtol=0): raise ValueError('Saved connected product-relative frame differs')
            root_relative[guid] = root_relative[parents[guid]] @ placement.get_axis2placement(obj.ObjectPlacement.RelativePlacement)
        elif obj.ObjectPlacement.PlacementRelTo is not None: raise ValueError('Declared chain root placement required')
        actual_ports = system.get_ports(obj)
        if {p.GlobalId for p in actual_ports} != {p for p, row in expected['ports'].items() if row['owner'] == guid}: raise ValueError('Saved port ownership differs')
        mesh = ifcopenshell.geom.create_shape(settings, obj); vertices = np.asarray(mesh.geometry.verts).reshape(-1, 3); faces = np.asarray(mesh.geometry.faces).reshape(-1, 3)
        matrix_local = root_relative[guid]; vertices = vertices @ matrix_local[:3, :3].T + matrix_local[:3, 3]
        solid = from_mesh((vertices, faces)); solids[guid] = solid
        if not math.isclose(solid.volume(), source['native_volume_m3'], rel_tol=1e-9, abs_tol=1e-10): raise ValueError('Saved component mass differs from source native geometry')
    for guid, source in expected['ports'].items():
        port = ports[guid]
        if port.Name != source['name'] or port.FlowDirection != source['direction'] or port.PredefinedType != source['predefined_type'] or port.SystemType != source['system_type'] or not np.allclose(placement.get_local_placement(port.ObjectPlacement), source['frame'], atol=FRAME_TOLERANCE, rtol=0): raise ValueError('Saved source port identity/type/direction/frame differs')
        if port.ObjectPlacement.PlacementRelTo != products[source['owner']].ObjectPlacement or not np.allclose(placement.get_axis2placement(port.ObjectPlacement.RelativePlacement), source['local_frame'], atol=1e-10, rtol=0): raise ValueError('Saved owned port-relative frame differs')
    links = [(r.RelatingPort.GlobalId, r.RelatedPort.GlobalId) for r in model.by_type('IfcRelConnectsPorts')]
    if len(links) != len(expected['links']) or set(links) != set(map(tuple, expected['links'])): raise ValueError('Exact saved directed connection set required')
    degree = Counter(p for pair in links for p in pair)
    if any(v != 1 for v in degree.values()): raise ValueError('Each connected port must have one peer')
    for a, b in links:
        first, second = [placement.get_local_placement(ports[p].ObjectPlacement) for p in (a, b)]
        if not np.allclose(first[:3, 3], second[:3, 3], atol=FRAME_TOLERANCE, rtol=0) or not np.allclose(first[:3, 2], -second[:3, 2], atol=FRAME_TOLERANCE, rtol=0): raise ValueError('Saved interface coincidence/opposed normals differ')
    systems = model.by_type('IfcDistributionSystem')
    if len(systems) != 1 or systems[0].GlobalId != stable_guid(data, 'IfcDistributionSystem', KEY) or systems[0].PredefinedType != 'VENTILATION' or {o.GlobalId for r in systems[0].IsGroupedBy for o in r.RelatedObjects} != set(products): raise ValueError('One exact connected ventilation system required')
    props = element.get_psets(systems[0]).get('BSA_ChainSource', {})
    if props.get('Source') != data['source'] or props.get('SourceSection') != data['section']: raise ValueError('Saved chain source metadata differs')
    overlaps = []
    for a, b in itertools.combinations(solids, 2):
        common = solids[a] ^ solids[b]
        if common.status() != m.Error.NoError or abs(common.volume()) > 1e-12: raise ValueError('Saved chain material interpenetrates')
        overlaps.append(common.volume())
    union = m.Manifold.batch_boolean(list(solids.values()), m.OpType.Add)
    if union.status() != m.Error.NoError or len(union.decompose()) != 1 or not math.isclose(union.volume(), expected['independent_volume_m3'], rel_tol=1e-9, abs_tol=1e-10): raise ValueError('Connected material union/independent source volume differs')
    mesh = union.to_mesh64(); faces = np.asarray(mesh.tri_verts); vertices = np.asarray(mesh.vert_properties)[:, :3]
    edges = Counter(tuple(sorted((int(a), int(b)))) for face in faces for a, b in zip(face, [face[1], face[2], face[0]]))
    boundary_count = len(ports)-len(degree); euler = len(vertices)-len(edges)+len(faces)
    if any(n != 2 for n in edges.values()) or euler != 4-2*boundary_count: raise ValueError('Saved chain boundary-bore topology differs')
    return dict(schema_express_issue_count=0, components=len(products), ports=len(ports), directed_interfaces=len(links), boundary_ports=boundary_count,
        one_connected_product_tree=True, one_connected_material=True, material_volume_m3=union.volume(), independent_material_volume_m3=expected['independent_volume_m3'],
        euler_characteristic=euler, material_pair_count=len(overlaps), material_overlap_m3=overlaps,
        maximum_source_frame_numeric_difference=max(pose_errors), source_shape_and_property_hashes_pass=True,
        maximum_source_cap_port_numeric_difference=max(p['source_cap_port_numeric_difference'] for p in expected['ports'].values()),
        saved_same_file_connections=True, design_accepted=False)


def merge(paths, target, data, span, independent_volume):
    expected, libraries = snapshot(paths)
    near = stable_guid(data, 'IfcDistributionPort', span_tool.KEY, data['section'], 'near')
    far = stable_guid(data, 'IfcDistributionPort', span_tool.KEY, data['section'], 'far')
    expected['links'] = sorted(set(map(tuple, expected['links'])) | {(span['upstream_port_guid'], near), (far, span['downstream_port_guid'])})
    expected['independent_volume_m3'] = independent_volume
    root, order, matrices, parents, local = solve_frames(expected)
    model = api.run('project.create_file', version='IFC4'); api.run('root.create_entity', model, ifc_class='IfcProject', name='Source-bound local duct chain')
    length_unit = api.run('unit.add_si_unit', model, unit_type='LENGTHUNIT'); api.run('unit.assign_unit', model, units=[length_unit])
    products = {}
    for _, library in libraries:
        identities = {}
        for obj in library.by_type('IfcElement'):
            added = api.run('project.append_asset', model, library=library, element=obj, reuse_identities=identities, assume_asset_uniqueness_by_name=False)
            products[added.GlobalId] = added
    if model.by_type('IfcRelConnectsPorts') or model.by_type('IfcDistributionSystem'): raise ValueError('Unexpected imported connection/system; source connectivity is explicitly rebuilt')
    ports = {p.GlobalId: p for p in model.by_type('IfcDistributionPort')}
    if set(products) != set(expected['objects']) or set(ports) != set(expected['ports']): raise ValueError('Upstream asset append lost/added bodies or owned ports')
    for guid in order:
        obj = products[guid]
        obj.ObjectPlacement = relative_placement(model, local[guid] if guid in parents else matrices[guid], products[parents[guid]].ObjectPlacement if guid in parents else None)
        for port in system.get_ports(obj): port.ObjectPlacement = relative_placement(model, np.asarray(expected['ports'][port.GlobalId]['local_frame']), obj.ObjectPlacement)
    for a, b in expected['links']: api.run('system.connect_port', model, port1=ports[a], port2=ports[b], direction='SOURCE')
    distribution = api.run('root.create_entity', model, ifc_class='IfcDistributionSystem', name='Local directed ventilation chain', predefined_type='VENTILATION')
    distribution.GlobalId = stable_guid(data, 'IfcDistributionSystem', KEY)
    api.run('system.assign_system', model, products=list(products.values()), system=distribution)
    pset = api.run('pset.add_pset', model, product=distribution, name='BSA_ChainSource')
    api.run('pset.edit_pset', model, pset=pset, properties=dict(Source=data['source'], SourceSection=data['section'], Scope='Local source-bound model only; construction, installation, product, pressure and regulation acceptance pending'))
    model.write(str(target)); return inspect(target, data, expected), expected


def run(project, out):
    from .workflow import verify
    project, data, plan, workflow, ends = span_tool.prepare(project); out = Path(out).resolve()
    protected = [project, plan]+[e[k] for e in ends for k in ('project', 'binding')]
    if out.exists() or not out.is_relative_to(ROOT) or any(out == p or out in p.parents for p in protected) or any(out.is_relative_to(p) or p.is_relative_to(out) for p in [workflow]+[e['model'] for e in ends]): raise ValueError('New repository-local chain output outside immutable sources required')
    inputs = {str(project): digest(project), str(Path(__file__)): digest(Path(__file__))}
    span = span_tool.run(project, out/'span')
    for name, sha in span['inputs'].items():
        if name in inputs and inputs[name] != sha: raise ValueError('Source context changed during span preparation')
        inputs[name] = sha
    if span['status'] == 'fail' or not span['straight_available']:
        result = dict(inputs=inputs, status='fail', chain_checks_pass=False, design_accepted=False, reason='Source span did not pass; merge not executed')
        (out/'chain.json').write_text(json.dumps(result, indent=2), encoding='utf-8'); return result
    component_artifacts = {p.relative_to(out).as_posix(): digest(p) for p in (out/'span').rglob('*') if p.is_file()}
    paths = [e['model']/'assembly.ifc' for e in ends]+[out/'span/span.ifc']
    independent_volume = span['checks']['independent_wall_volume_m3']
    for i in (1, 2): independent_volume += json.loads((out/'span'/('endpoint-'+str(i))/'fit-review.json').read_text(encoding='utf-8'))['assembly_checks']['independent_material_volume_m3']
    target = out/'chain.ifc'; checks, expected = merge(paths, target, data, span, independent_volume)
    if any(digest(Path(p)) != sha for p, sha in inputs.items()) or any(digest(out/p) != sha for p, sha in component_artifacts.items()) or not verify(workflow)['integrity_pass']: raise ValueError('Source or component artifacts changed during chain authoring')
    (out/'source-snapshot.json').write_text(json.dumps(expected, indent=2), encoding='utf-8')
    result = dict(inputs=inputs, component_artifacts=component_artifacts, ifc_sha256=digest(target), snapshot_sha256=digest(out/'source-snapshot.json'),
        checks=checks, status='review_required', chain_checks_pass=True, design_accepted=False,
        scope='One directed saved-IFC local chain only; inherited construction/elevation assumptions, product joints, full-network pressure, installation and jurisdiction acceptance remain pending')
    (out/'chain.json').write_text(json.dumps(result, indent=2), encoding='utf-8'); return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('project'); parser.add_argument('--out', required=True)
    args = parser.parse_args(); result = run(args.project, args.out); print(result['status'], result.get('checks', {})); raise SystemExit(2 if result['chain_checks_pass'] else 1)
