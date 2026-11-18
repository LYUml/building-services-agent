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
    if positions and len(model.by_type('IfcProject')) != 1:
        raise ValueError('Exactly one IfcProject is required to resolve port position units')

    products = [item for item in model.by_type('IfcDistributionElement') if not item.is_a('IfcPort')]
    ports = sorted(model.by_type('IfcDistributionPort'), key=lambda port: port.GlobalId)
    if len({port.GlobalId for port in ports}) != len(ports):
        raise ValueError('Duplicate IFC distribution port GlobalId')
    owners = {port.GlobalId: set() for port in ports}
    owner_evidence = {port.GlobalId: [] for port in ports}
    product_ids = {product.id() for product in products}
    for kind in ('IfcRelNests', 'IfcRelConnectsPortToElement'):
        for attachment in model.by_type(kind):
            if kind == 'IfcRelNests':
                owner, candidates = attachment.RelatingObject, attachment.RelatedObjects
            else:
                owner, candidates = attachment.RelatedElement, [attachment.RelatingPort]
            for candidate in candidates:
                if candidate is not None and candidate.is_a('IfcDistributionPort'):
                    owner_evidence[candidate.GlobalId].append(dict(
                        relation_guid=attachment.GlobalId, relation_type=kind,
                        owner_guid=owner.GlobalId if owner is not None else None,
                        scoped_owner=owner is not None and owner.id() in product_ids))
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
                              owner_guids=sorted(owners[port.GlobalId]),
                              owner_evidence=sorted(owner_evidence[port.GlobalId],
                                                    key=lambda row: row['relation_guid'])) for port in ports],
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
        changed_pairs=[dict(port_guids=list(pair), before=old_pairs[pair], after=new_pairs[pair])
                       for pair in sorted(old_pairs.keys() | new_pairs.keys()) if old_pairs[pair] != new_pairs[pair]],
        scope='Saved export differences by exact port GUID; physical continuity and GUID remapping unresolved',
    )


def compare_positions(previous, current, tolerance, *, alignment=None):
    before = {row['guid']: row['origin_m'] for row in previous['ports']}
    after = {row['guid']: row['origin_m'] for row in current['ports']}
    moved, unavailable = [], []
    shared = sorted(before.keys() & after.keys())
    if alignment is not None:
        angle = math.radians(alignment.get('current_to_baseline_yaw_deg', 0))
        cosine, sine = math.cos(angle), math.sin(angle)
        tx, ty, tz = alignment['current_to_baseline_m']
    for guid in shared:
        a, b = before[guid], after[guid]
        if a is None or b is None:
            unavailable.append(guid)
            continue
        aligned = b
        if alignment is not None:
            x, y, z = b
            aligned = [cosine*x-sine*y+tx, sine*x+cosine*y+ty, z+tz]
        displacement = math.dist(a, aligned)
        if not math.isfinite(displacement):
            raise ValueError('Nonfinite IFC port displacement')
        if displacement > tolerance:
            record = dict(guid=guid, before_m=a, after_m=b, displacement_m=displacement)
            if alignment is not None:
                record['aligned_after_m'] = aligned
            moved.append(record)
    basis = 'Assumed common IFC model frame; georeferencing not reconciled'
    if alignment is not None:
        basis = ('Declared Z rotation and translation into baseline frame'
                 if 'current_to_baseline_yaw_deg' in alignment else 'Declared translation into baseline frame')
    return dict(tolerance_m=tolerance, comparable_ports=len(shared)-len(unavailable),
                unavailable_ports=unavailable, moved_ports=moved, coordinate_basis=basis)


def inspect_pair_gaps(inventory, tolerance):
    positions = {row['guid']: row['origin_m'] for row in inventory['ports']}
    measured, unavailable, separated = 0, [], []
    self_connections = []
    relationships_by_pair = {}
    for connection in inventory['connections']:
        pair = connection['port_guids']
        relationships_by_pair.setdefault(tuple(sorted(pair)), []).append(connection['guid'])
        a, b = (positions.get(guid) for guid in pair)
        if pair[0] == pair[1]:
            self_connections.append(connection['guid'])
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
    duplicates = [dict(port_guids=list(pair), relationship_guids=sorted(guids))
                  for pair, guids in sorted(relationships_by_pair.items()) if len(guids) > 1]
    return dict(tolerance_m=tolerance, measured_relationships=measured, duplicate_pairs=duplicates,
                self_connections=sorted(self_connections),
                unavailable_relationships=unavailable, separated_relationships=separated,
                scope='Distances between exported port origins only; physical joint and profile unresolved')


def read_alignment(path, previous, current):
    path = Path(path).resolve()
    if not workspace.allowed(path):
        raise ValueError('IFC alignment must be in the permitted workspace')
    before = file_hash(path)
    spec = json.loads(path.read_text(encoding='utf-8-sig'))
    if (not isinstance(spec, dict)
            or set(spec)-{'current_to_baseline_yaw_deg'} != {
                'source', 'baseline_sha256', 'current_sha256', 'current_to_baseline_m'}
            or not isinstance(spec['source'], str) or not spec['source'].strip()
            or spec['baseline_sha256'] != previous['source_sha256']
            or spec['current_sha256'] != current['source_sha256']):
        raise ValueError('Alignment requires a source locator and hashes of both IFC exports')
    translation = spec['current_to_baseline_m']
    if not isinstance(translation, list) or len(translation) != 3 or any(
        type(value) not in (int, float) or not math.isfinite(value) for value in translation
    ):
        raise ValueError('Alignment requires three finite metre offsets')
    yaw = spec.get('current_to_baseline_yaw_deg', 0)
    if type(yaw) not in (int, float) or not math.isfinite(yaw):
        raise ValueError('Alignment Z rotation must be a finite angle in degrees')
    if file_hash(path) != before:
        raise ValueError('IFC alignment changed during reading')
    return dict(**spec, sha256=before)


def inventory(source, position_tolerance_m=None, *, baseline=None, max_port_shift_m=None, alignment=None):
    positions = position_tolerance_m is not None
    if positions and (type(position_tolerance_m) not in (int, float)
                      or not math.isfinite(position_tolerance_m) or position_tolerance_m <= 0):
        raise ValueError('Position checks require a finite positive tolerance in metres')
    if max_port_shift_m is not None and (
        baseline is None or not positions or type(max_port_shift_m) not in (int, float)
        or not math.isfinite(max_port_shift_m) or max_port_shift_m <= 0
    ):
        raise ValueError('Port shift limit requires a baseline and positive finite metre tolerances')
    if alignment is not None and (baseline is None or not positions):
        raise ValueError('IFC coordinate alignment requires a baseline and position checks')
    result = inspect(source, positions=positions)
    if positions:
        result['connection_gaps'] = inspect_pair_gaps(result, position_tolerance_m)
        linked = {guid for row in result['connections'] for guid in row['port_guids']}
        claims = {row['guid']: {item['owner_guid'] for item in row['owner_evidence']
                               if item['owner_guid'] is not None}
                  for row in result['ports'] if row['guid'] in linked}
        result['connection_ownership'] = dict(
            conflicting_ports=sorted(guid for guid, values in claims.items() if len(values) > 1),
            unavailable_ports=sorted(row['guid'] for row in result['ports'] if row['guid'] in linked
                                     and not row['owner_guids']),
        )
    if baseline is not None:
        previous = inspect(baseline, positions=positions)
        result['comparison'] = comparison = compare(previous, result)
        if positions:
            transform = read_alignment(alignment, previous, result) if alignment is not None else None
            comparison['positions'] = compare_positions(previous, result, max_port_shift_m or position_tolerance_m,
                                                       alignment=transform)
            if transform is not None:
                comparison['alignment'] = transform
                if file_hash(alignment) != transform['sha256']:
                    raise ValueError('IFC alignment changed during comparison')
        if max_port_shift_m is not None:
            comparison['max_port_shift_m'] = max_port_shift_m
        if file_hash(baseline) != previous['source_sha256'] or file_hash(source) != result['source_sha256']:
            raise ValueError('IFC input changed during comparison')
    return result


def gap_status(gaps):
    if gaps['separated_relationships']:
        return 'fail', 'Exported IFC port origins exceed the declared separation tolerance'
    if not gaps['measured_relationships'] or gaps['unavailable_relationships']:
        return 'pending', 'Exported IFC port positions do not cover all declared relationships'
    return 'pass', gaps['scope']


def review_status(report):
    gaps = report['connection_gaps']
    status, reason = gap_status(gaps)
    if gaps.get('duplicate_pairs'):
        return 'fail', 'Multiple IFC relationships connect the same port pair'
    if gaps.get('self_connections'):
        return 'fail', 'IFC relationships connect a port to itself'
    ownership = report.get('connection_ownership', {})
    if ownership.get('conflicting_ports'):
        return 'fail', 'Connected IFC ports have conflicting owner declarations'
    if status == 'pass' and ownership.get('unavailable_ports'):
        status, reason = 'pending', 'Connected IFC ports lack supported owner evidence'
    comparison = report.get('comparison')
    if status == 'fail' or comparison is None:
        return status, reason
    if comparison['status'] == 'no_shared_port_guids':
        return 'pending', 'Baseline comparison lacks shared exported port identities'
    if any(comparison[key] for key in ('added_ports', 'removed_ports', 'changed_ports', 'changed_pairs')):
        return 'fail', 'Exported port identities, owners, directions or peer pairs differ from the declared baseline'
    if 'max_port_shift_m' in comparison:
        positions = comparison['positions']
        if positions['moved_ports']:
            return 'fail', 'Exported port movement exceeds the declared baseline limit'
        if positions['unavailable_ports']:
            return 'pending', 'Baseline port positions do not cover all shared port identities'
    return status, reason


def run(source, out, *, baseline=None, position_tolerance_m=None, max_port_shift_m=None, alignment=None):
    source, out = (Path(p).resolve() for p in (source, out))
    if not workspace.intake_output(out) or out.exists():
        raise ValueError('Fresh IFC report in the permitted output workspace required')
    positions = position_tolerance_m is not None
    result = inventory(source, position_tolerance_m, baseline=baseline, max_port_shift_m=max_port_shift_m,
                       alignment=alignment)
    summary = {key: result[key] for key in ('source_sha256', 'schema', 'preprocessor', 'counts', 'design_accepted')}
    if positions:
        gaps = result['connection_gaps']
        summary['connection_gaps'] = dict(measured_relationships=gaps['measured_relationships'],
            unavailable_relationships=len(gaps['unavailable_relationships']),
            separated_relationships=len(gaps['separated_relationships']),
            duplicate_pairs=len(gaps['duplicate_pairs']), self_connections=len(gaps['self_connections']),
            status=gap_status(gaps)[0])
        summary['review_status'] = review_status(result)[0]
    if baseline is not None:
        comparison = result['comparison']
        summary['comparison'] = {key: comparison[key] for key in ('baseline_sha256', 'status', 'shared_ports')}
        for key in ('added_ports', 'removed_ports', 'changed_ports', 'changed_pairs'):
            summary['comparison'][key] = len(comparison[key])
        if positions:
            position = comparison['positions']
            summary['comparison']['positions'] = dict(comparable_ports=position['comparable_ports'],
                unavailable_ports=len(position['unavailable_ports']), moved_ports=len(position['moved_ports']))
    if file_hash(source) != result['source_sha256']:
        raise ValueError('Current IFC changed during comparison')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    return summary
