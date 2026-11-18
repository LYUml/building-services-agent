"""Inspect saved IFC port ownership and relationships without inferring flow."""
from collections import Counter
import importlib.metadata
import json
from pathlib import Path

from . import workspace
from .source_refs import file_hash


def inspect(source):
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
                       for guid in sorted(shared) if before[guid] != after[guid]],
        changed_pairs=[dict(port_guids=pair, before=old_pairs[pair], after=new_pairs[pair])
                       for pair in sorted(old_pairs.keys() | new_pairs.keys()) if old_pairs[pair] != new_pairs[pair]],
        scope='Saved export differences by exact port GUID; physical continuity and GUID remapping unresolved',
    )


def run(source, out, *, baseline=None):
    source, out = (Path(p).resolve() for p in (source, out))
    if not workspace.intake_output(out) or out.exists():
        raise ValueError('Fresh IFC report in the permitted output workspace required')
    result = inspect(source)
    summary = {key: result[key] for key in ('source_sha256', 'schema', 'preprocessor', 'counts', 'design_accepted')}
    if baseline is not None:
        previous = inspect(baseline)
        comparison = compare(previous, result)
        result['comparison'] = comparison
        summary['comparison'] = {key: comparison[key] for key in ('baseline_sha256', 'status', 'shared_ports')}
        for key in ('added_ports', 'removed_ports', 'changed_ports', 'changed_pairs'):
            summary['comparison'][key] = len(comparison[key])
        if file_hash(baseline) != previous['source_sha256']:
            raise ValueError('Baseline IFC changed during comparison')
    if file_hash(source) != result['source_sha256']:
        raise ValueError('Current IFC changed during comparison')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    return summary
