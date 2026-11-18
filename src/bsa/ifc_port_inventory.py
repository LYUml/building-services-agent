"""Inspect saved IFC port ownership and relationships without inferring flow."""
from collections import Counter
import importlib.metadata
import json
from pathlib import Path

from . import workspace
from .source_refs import file_hash


def run(source, out):
    from ifcopenshell import open as open_ifc
    from ifcopenshell.util.system import get_ports

    source, out = (Path(p).resolve() for p in (source, out))
    if not workspace.allowed(source) or not workspace.intake_output(out):
        raise ValueError('Use a permitted IFC source and an explicit output workspace')
    if source.suffix.lower() != '.ifc' or out.exists():
        raise ValueError('Saved IFC and fresh report file required')
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
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    return {key: result[key] for key in ('source_sha256', 'schema', 'preprocessor', 'counts', 'design_accepted')}
