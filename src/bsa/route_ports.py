"""Derive planar routing endpoints from saved, open circular-wall IFC ports."""
import argparse
import copy
import importlib.metadata
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.unit as unit
import numpy as np

from .cli import digest
from .engine import ProjectError
from .module_contract import read_json
from .product_alignment import aligned_placement
from .route_model import plane
from .route_optimize import run as optimize
from .route_search import search
from .workspace import allowed


def prepare(ifc, basis, routing, settings):
    """Read actual cap positions/normals; no copied endpoint coordinates accepted."""
    if set(basis) != {'source', 'start', 'end'} or not isinstance(basis['source'], str) or not basis['source'].strip():
        raise ProjectError('Exact sourced start/end port selection required')
    if any(k in routing for k in ('start_m', 'end_m', 'endpoint_directions')):
        raise ProjectError('Port-bound routing must not duplicate endpoints or directions')
    if routing.get('coordinate_plane') != 'declared-local-frame':
        raise ProjectError('Port-bound routing requires an explicit local world frame')
    origin, u, v, normal = [np.asarray(x, dtype=float) for x in plane(settings)]
    model = ifcopenshell.open(str(ifc))
    if model.schema != 'IFC4' or len(model.by_type('IfcProject')) != 1 or not math.isclose(unit.calculate_unit_scale(model), 1., abs_tol=1e-12, rel_tol=0):
        raise ProjectError('One IFC4 project with metre length units required')
    roots = [r.GlobalId for r in model.by_type('IfcRoot')]
    if len(roots) != len(set(roots)):
        raise ProjectError('Unique source IFC root GUIDs required')
    result = copy.deepcopy(routing)
    result['endpoint_directions'] = {}
    records = {}
    selected = set()
    selected_system = None
    expected_class = 'IfcDuctSegment' if settings.get('element_family') == 'duct' else 'IfcPipeSegment'
    for role, flow, sign in [('start', 'SOURCE', 1), ('end', 'SINK', -1)]:
        row = basis[role]
        if not isinstance(row, dict) or set(row) != {'owner_guid', 'port_guid'} or any(not isinstance(x, str) or not x for x in row.values()):
            raise ProjectError('Explicit owner and port GUIDs required')
        try:
            owner, port = [model.by_guid(row[k]) for k in ('owner_guid', 'port_guid')]
        except RuntimeError as exc:
            raise ProjectError('Selected source owner/port GUID missing') from exc
        if owner is None or port is None or owner.is_a() != expected_class or not port.is_a('IfcDistributionPort') or port not in system.get_ports(owner) or system.get_port_element(port) != owner:
            raise ProjectError('Selected port must belong to the supported source wall')
        if owner.GlobalId in selected:
            raise ProjectError('Distinct endpoint owners required')
        selected.add(owner.GlobalId)
        if port.FlowDirection != flow or port.ConnectedTo or port.ConnectedFrom:
            raise ProjectError('Open directed source SOURCE and receiving SINK ports required')
        memberships = system.get_element_systems(owner)
        if len(memberships) != 1 or memberships[0].PredefinedType != settings['system']['predefined_type']:
            raise ProjectError('Exact compatible source distribution system required')
        if selected_system is not None and memberships[0].GlobalId != selected_system:
            raise ProjectError('Both source endpoints must share one declared distribution system')
        selected_system = memberships[0].GlobalId
        bodies = [r for r in owner.Representation.Representations if r.RepresentationIdentifier == 'Body'] if owner.Representation else []
        if len(bodies) != 1 or len(bodies[0].Items) != 1:
            raise ProjectError('One native straight hollow swept wall required')
        solid = bodies[0].Items[0]
        if not solid.is_a('IfcExtrudedAreaSolid') or not solid.SweptArea.is_a('IfcCircleHollowProfileDef') or solid.SweptArea.Position is not None:
            raise ProjectError('Centred native circular hollow profile required')
        profile = solid.SweptArea
        bore, outer = 2 * (profile.Radius - profile.WallThickness), 2 * profile.Radius
        if not all(math.isfinite(x) for x in (bore, outer)) or not 0 < bore < outer or not math.isclose(bore, settings['inside_diameter_m'], abs_tol=1e-9, rel_tol=0) or not math.isclose(outer, routing['outside_diameter_m'], abs_tol=1e-9, rel_tol=0):
            raise ProjectError('Native source bore/OD must match route; no automatic reducer inferred')
        frame = placement.get_local_placement(owner.ObjectPlacement) @ placement.get_axis2placement(solid.Position)
        port_frame = placement.get_local_placement(port.ObjectPlacement)
        for matrix in (frame, port_frame):
            aligned_placement(matrix, np.eye(4), 0)  # Existing proper-rigid-frame guard.
        direction = np.asarray(solid.ExtrudedDirection.DirectionRatios, dtype=float)
        if not np.isfinite(direction).all() or not math.isclose(float(np.linalg.norm(direction)), 1., abs_tol=1e-9, rel_tol=0) or not math.isfinite(solid.Depth) or solid.Depth <= 0:
            raise ProjectError('Positive native depth and unit extrusion axis required')
        axis = frame[:3, :3] @ direction
        caps = [(frame[:3, 3], -axis), (frame[:3, 3] + solid.Depth * axis, axis)]
        if not any(np.allclose(port_frame[:3, 3], point, atol=1e-8, rtol=0) and np.allclose(port_frame[:3, 2], outward, atol=1e-8, rtol=0) for point, outward in caps):
            raise ProjectError('Source port must match actual native wall cap and outward normal')
        point, travel = port_frame[:3, 3], sign * port_frame[:3, 2]
        local_point = [float(np.dot(point - origin, a)) for a in (u, v)]
        local_axis = [float(np.dot(travel, a)) for a in (u, v)]
        if abs(float(np.dot(point - origin, normal))) > 1e-8 or abs(float(np.dot(travel, normal))) > 1e-8 or not any(np.allclose(local_axis, a, atol=1e-8, rtol=0) for a in ([1, 0], [-1, 0], [0, 1], [0, -1])):
            raise ProjectError('Source cap and cardinal travel axis must lie in declared routing plane')
        local_axis = [int(round(x)) for x in local_axis]
        source = basis['source'] + '; saved IFC owner ' + owner.GlobalId + ' port ' + port.GlobalId
        result[role + '_m'] = local_point
        result['endpoint_directions'][role] = dict(axis=local_axis, source=source, classification='geometry-derived')
        records[role] = dict(**row, point_m=point.tolist(), outward_axis=port_frame[:3, 2].tolist(), travel_direction=travel.tolist(), bore_m=bore, outside_diameter_m=outer, native_wall_cap_match=True)
    search(result)  # Validate grid and source-derived constraints before output.
    return result, records


def run(ifc, basis, routing, settings, network, out):
    paths = [Path(p).resolve() for p in (ifc, basis, routing, settings, network)]
    out = Path(out).resolve()
    if out.exists() or not all(allowed(p) for p in [*paths, out]) or any(p == out or out in p.parents for p in paths):
        raise ProjectError('Fresh selected-workspace output separate from all source files required')
    if importlib.metadata.version('ifcopenshell') != '0.8.5':
        raise ProjectError('Pinned IfcOpenShell runtime required')
    inputs = {str(p): digest(p) for p in paths}
    methods = {str(Path(p).resolve()): digest(Path(p)) for p in (__file__, plane.__code__.co_filename, aligned_placement.__code__.co_filename, optimize.__code__.co_filename)}
    derived, endpoints = prepare(paths[0], read_json(paths[1]), read_json(paths[2]), read_json(paths[3]))
    out.mkdir(parents=True)
    route_path = out / 'routing-input.json'
    route_path.write_text(json.dumps(derived, indent=2), encoding='utf-8')
    result = optimize(route_path, paths[3], paths[4], out / 'route')
    frames = result['selected_model']['endpoint_frames']
    for role in ('start', 'end'):
        if not np.allclose(frames[role]['point_m'], endpoints[role]['point_m'], atol=1e-8, rtol=0) or not np.allclose(frames[role]['travel_direction'], endpoints[role]['travel_direction'], atol=1e-8, rtol=0):
            raise ProjectError('Saved selected route does not meet original source endpoint frame')
    if any(digest(Path(p)) != h for p, h in {**inputs, **methods}.items()):
        raise ProjectError('Port routing source or method changed during execution')
    report = dict(inputs=inputs, method_inputs=methods, endpoints=endpoints,
                  route_report_sha256=digest(out/'route/route-optimisation.json'),
                  saved_endpoint_correspondence=True, calculated_checks_pass=result['calculated_checks_pass'],
                  design_accepted=False, sources_unchanged=True,
                  scope='Source-guided separate route IFC only; no merged logical connections, physical joints, full equipment geometry, obstacle completeness or regulatory acceptance')
    (out/'port-route.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ifc', type=Path)
    for name in ('basis', 'routing', 'settings', 'network', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    report = run(args.ifc, args.basis, args.routing, args.settings, args.network, args.out)
    print(json.dumps(report, indent=2))
    return 0 if report['calculated_checks_pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
