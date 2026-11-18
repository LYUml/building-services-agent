"""Inspect saved IFC port ownership and relationships without inferring flow."""
from collections import Counter
import importlib.metadata
import json
import math
from pathlib import Path

from . import workspace
from .source_refs import file_hash


def inspect(source, *, positions=False):
    from ifcopenshell import open as open_ifc
    from ifcopenshell.util.system import get_ports

    source = Path(source).resolve()
    if not workspace.allowed(source) or source.suffix.lower() != '.ifc':
        raise ValueError('Use a permitted saved IFC source')
    if importlib.metadata.version('ifcopenshell') != '0.8.5':
        raise ValueError('Pinned IfcOpenShell 0.8.5 required')
    before = file_hash(source)
    model = open_ifc(str(source))
    if model.schema not in ('IFC2X3', 'IFC4'):
        raise ValueError('IFC2X3 or IFC4 required for this inventory')

    products = [item for item in model.by_type('IfcDistributionElement') if not item.is_a('IfcPort')]
    ports = sorted(model.by_type('IfcDistributionPort'), key=lambda port: port.GlobalId)
    if len({port.GlobalId for port in ports}) != len(ports):
        raise ValueError('Duplicate IFC distribution port GlobalId')
    owners = {port.GlobalId: set() for port in ports}
    for product in products:
        for port in get_ports(product):
            if port.GlobalId in owners:
                owners[port.GlobalId].add(product.GlobalId)
    connections = []
    referenced = set()
    for relation in model.by_type('IfcRelConnectsPorts'):
        a, b = relation.RelatingPort, relation.RelatedPort
        directions = [getattr(port, 'FlowDirection', None) for port in (a, b)]
        ends = [a.GlobalId, b.GlobalId]
        referenced.update(ends)
        source_index = directions.index('SOURCE') if set(directions) == {'SOURCE', 'SINK'} else None
        connections.append(dict(guid=relation.GlobalId, port_guids=ends, flow_directions=directions,
                                source_port=ends[source_index] if source_index is not None else None))
    directed = sum(row['source_port'] is not None for row in connections)
    counts = dict(products=len(products), ports=len(ports), relationships=len(connections),
                  explicit_source_sink_pairs=directed, relationships_without_unique_direction=len(connections)-directed,
                  ports_without_unique_owner=sum(len(value) != 1 for value in owners.values()),
                  ports_without_peer=sum(port.GlobalId not in referenced for port in ports))
    result = dict(source_sha256=before, schema=model.schema,
                  preprocessor=model.header.file_name.preprocessor_version, counts=counts,
                  product_classes=dict(sorted(Counter(item.is_a() for item in products).items())),
                  ports=[dict(guid=port.GlobalId, flow_direction=port.FlowDirection,
                              owner_guids=sorted(owners[port.GlobalId])) for port in ports],
                  connections=sorted(connections, key=lambda row: row['guid']),
                  design_accepted=False)
    if positions:
        from ifcopenshell.util.placement import get_local_placement
        from ifcopenshell.util.unit import calculate_unit_scale, get_project_unit

        scale = calculate_unit_scale(model) if get_project_unit(model, 'LENGTHUNIT') else None
        if scale is not None and (not math.isfinite(scale) or scale <= 0):
            raise ValueError('Invalid IFC length-unit scale')
        for port, row in zip(ports, result['ports'], strict=True):
            row['origin_m'] = None
            placement = port.ObjectPlacement
            if placement is None or scale is None:
                continue
            ancestor = placement
            seen = set()
            while ancestor is not None and ancestor.is_a('IfcLocalPlacement'):
                if ancestor.id() in seen:
                    raise ValueError('Cyclic IFC port placement')
                seen.add(ancestor.id())
                ancestor = ancestor.PlacementRelTo
            if ancestor is not None:
                continue
            origin = [float(value)*scale for value in get_local_placement(placement)[:3, 3]]
            if not all(map(math.isfinite, origin)):
                raise ValueError('Nonfinite IFC port position')
            row['origin_m'] = origin
    if file_hash(source) != before:
        raise ValueError('IFC changed during port inventory')
    return result


def compare(baseline, current):
    before = {row['guid']: row for row in baseline['ports']}
    after = {row['guid']: row for row in current['ports']}
    shared = before.keys() & after.keys()
    old_pairs = Counter(tuple(sorted(row['port_guids'])) for row in baseline['connections'])
    new_pairs = Counter(tuple(sorted(row['port_guids'])) for row in current['connections'])
    return dict(
        baseline_sha256=baseline['source_sha256'], baseline_schema=baseline['schema'],
        status='shared_port_guids' if shared else 'no_shared_port_guids',
        shared_ports=len(shared),
        added_ports=sorted(after.keys()-before.keys()), removed_ports=sorted(before.keys()-after.keys()),
        changed_ports=[dict(guid=guid, before=before[guid], after=after[guid])
                       for guid in sorted(shared)
                       if any(before[guid][key] != after[guid][key] for key in ('owner_guids', 'flow_direction'))],
        changed_pairs=[dict(port_guids=pair, before=old_pairs[pair], after=new_pairs[pair])
                       for pair in sorted(old_pairs.keys() | new_pairs.keys()) if old_pairs[pair] != new_pairs[pair]],
        scope='Saved export differences by exact port GUID; physical continuity and GUID remapping unresolved',
    )


def compare_positions(previous, current, tolerance):
    before = {row['guid']: row['origin_m'] for row in previous['ports']}
    after = {row['guid']: row['origin_m'] for row in current['ports']}
    moved, unavailable = [], []
    shared = sorted(before.keys() & after.keys())
    for guid in shared:
        a, b = before[guid], after[guid]
        if a is None or b is None:
            unavailable.append(guid)
            continue
        displacement = math.dist(a, b)
        if not math.isfinite(displacement):
            raise ValueError('Nonfinite IFC port displacement')
        if displacement > tolerance:
            moved.append(dict(guid=guid, before_m=a, after_m=b, displacement_m=displacement))
    return dict(tolerance_m=tolerance, comparable_ports=len(shared)-len(unavailable),
                unavailable_ports=unavailable, moved_ports=moved,
                coordinate_basis='Assumed common IFC model frame; georeferencing not reconciled')


def inspect_pair_gaps(inventory, tolerance):
    positions = {row['guid']: row['origin_m'] for row in inventory['ports']}
    measured, unavailable, separated = 0, [], []
    for connection in inventory['connections']:
        pair = connection['port_guids']
        a, b = (positions.get(guid) for guid in pair)
        if a is None or b is None or pair[0] == pair[1]:
            unavailable.append(connection['guid'])
            continue
        measured += 1
        separation = math.dist(a, b)
        if not math.isfinite(separation):
            raise ValueError('Nonfinite IFC port separation')
        if separation > tolerance:
            separated.append(dict(guid=connection['guid'], port_guids=pair,
                                  origins_m=[a, b], separation_m=separation))
    return dict(tolerance_m=tolerance, measured_relationships=measured,
                unavailable_relationships=unavailable, separated_relationships=separated,
                scope='Distances between exported port origins only; physical joint and profile unresolved')


def run(source, out, *, baseline=None, position_tolerance_m=None):
    source, out = (Path(p).resolve() for p in (source, out))
    if not workspace.intake_output(out) or out.exists():
        raise ValueError('Fresh IFC report in the permitted output workspace required')
    positions = position_tolerance_m is not None
    if positions and (type(position_tolerance_m) not in (int, float)
                      or not math.isfinite(position_tolerance_m) or position_tolerance_m <= 0):
        raise ValueError('Position checks require a finite positive tolerance in metres')
    result = inspect(source, positions=positions)
    summary = {key: result[key] for key in ('source_sha256', 'schema', 'preprocessor', 'counts', 'design_accepted')}
    if positions:
        gaps = inspect_pair_gaps(result, position_tolerance_m)
        result['connection_gaps'] = gaps
        summary['connection_gaps'] = dict(measured_relationships=gaps['measured_relationships'],
            unavailable_relationships=len(gaps['unavailable_relationships']),
            separated_relationships=len(gaps['separated_relationships']))
    if baseline is not None:
        previous = inspect(baseline, positions=positions)
        comparison = compare(previous, result)
        result['comparison'] = comparison
        summary['comparison'] = {key: comparison[key] for key in ('baseline_sha256', 'status', 'shared_ports')}
        for key in ('added_ports', 'removed_ports', 'changed_ports', 'changed_pairs'):
            summary['comparison'][key] = len(comparison[key])
        if positions:
            position = compare_positions(previous, result, position_tolerance_m)
            comparison['positions'] = position
            summary['comparison']['positions'] = dict(comparable_ports=position['comparable_ports'],
                unavailable_ports=len(position['unavailable_ports']), moved_ports=len(position['moved_ports']))
        if file_hash(baseline) != previous['source_sha256']:
            raise ValueError('Baseline IFC changed during comparison')
    if file_hash(source) != result['source_sha256']:
        raise ValueError('Current IFC changed during comparison')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    return summary
