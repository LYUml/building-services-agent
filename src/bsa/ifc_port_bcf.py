"""Write an offline BCF issue package for IFC port coordination findings."""
from collections import Counter
import importlib.metadata
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from . import workspace
from .ifc_port_inventory import inventory
from .source_refs import file_hash


def issue_records(report):
    ports = {row['guid']: row for row in report['ports']}
    gaps = report['connection_gaps']
    source = f"Saved IFC SHA-256 {report['source_sha256']}"
    for gap in gaps['separated_relationships']:
        a, b = gap['port_guids']
        selected = sorted(set(ports[a]['owner_guids'] + ports[b]['owner_guids']))
        midpoint = [x/2 + y/2 for x, y in zip(*gap['origins_m'], strict=True)]
        description = (f"{source}\n{a} to {b}: {gap['separation_m']:.9g} m, "
                       f"tolerance {gaps['tolerance_m']:.9g} m.\n"
                       "Review the exported port origins and joint geometry.")
        yield f"IFC port gap {gap['guid']}", description, selected, midpoint
    for guid in report['connection_ownership']['conflicting_ports']:
        port = ports[guid]
        claims = [f"{row['relation_type']} {row['relation_guid']} claims {row['owner_guid']}"
                  for row in port['owner_evidence']]
        selected = sorted({row['owner_guid'] for row in port['owner_evidence'] if row['scoped_owner']})
        description = '\n'.join([source, f"Port {guid} has conflicting owners.", *claims])
        yield f"IFC port ownership conflict {guid}", description, selected, port['origin_m']

    comparison = report.get('comparison')
    if not comparison or comparison['status'] != 'shared_port_guids':
        return
    basis = f"{source}\nBaseline IFC SHA-256 {comparison['baseline_sha256']}"
    for pair in comparison['changed_pairs']:
        a, b = pair['port_guids']
        current_ports = [ports[guid] for guid in (a, b) if guid in ports]
        selected = sorted({owner for port in current_ports for owner in port['owner_guids']})
        points = [port['origin_m'] for port in current_ports if port['origin_m'] is not None]
        point = points[0] if points else None
        if len(points) == 2:
            point = [x/2 + y/2 for x, y in zip(*points, strict=True)]
        description = (f"{basis}\n{a} to {b}: {pair['before']} baseline relation(s), "
                       f"{pair['after']} current relation(s).")
        yield f'IFC peer pair changed {a} / {b}', description, selected, point
    if 'max_port_shift_m' in comparison:
        limit = comparison['max_port_shift_m']
        for movement in comparison['positions']['moved_ports']:
            guid = movement['guid']
            description = (f"{basis}\nPort {guid} moved {movement['displacement_m']:.9g} m, "
                           f"limit {limit:.9g} m.\n"
                           f"Baseline origin: {movement['before_m']} m.\n"
                           f"Current origin: {movement['after_m']} m.")
            if 'aligned_after_m' in movement:
                description += f"\nAligned current origin: {movement['aligned_after_m']} m."
            yield f'IFC port movement {guid}', description, ports[guid]['owner_guids'], movement['after_m']


def verify(report, archive):
    from bcf.v3.bcfxml import BcfXml
    if importlib.metadata.version('bcf-client') != '0.9.0':
        raise ValueError('Pinned bcf-client 0.9.0 required')
    expected = Counter()
    before = file_hash(archive)
    for title, description, selected, point in issue_records(report):
        view_selection = tuple(selected) if point is not None else ()
        expected[title, description, view_selection, int(bool(view_selection)), 'Open'] += 1
    try:
        with BcfXml.load(archive) as restored:
            actual = Counter()
            for topic in restored.topics.values():
                selections = [component.ifc_guid for handler in topic.viewpoints.values()
                              for component in handler.visualization_info.components.selection.component]
                actual[topic.topic.title, topic.topic.description, tuple(sorted(selections)),
                       len(topic.viewpoints), topic.topic.topic_status] += 1
    except (AttributeError, BadZipFile) as exc:
        raise ValueError('Invalid IFC port coordination BCF archive') from exc
    if actual != expected or file_hash(archive) != before:
        raise ValueError('Saved BCF topics differ from the IFC coordination issues')
    return dict(source_sha256=report['source_sha256'], bcf_sha256=before,
                topics=sum(actual.values()),
                unavailable_relationships=len(report['connection_gaps']['unavailable_relationships']),
                bcf_reopen_verified=True, design_accepted=False)


def write(report, source, out):
    from bcf.v3.bcfxml import BcfXml
    from bcf.v3.visinfo import VisualizationInfoHandler
    import numpy as np

    source, out = (Path(p).resolve() for p in (source, out))
    if not workspace.intake_output(out) or out.suffix.lower() not in ('.bcf', '.bcfzip') or out.exists():
        raise ValueError('Use a fresh BCF archive path in the permitted output workspace')
    if importlib.metadata.version('bcf-client') != '0.9.0':
        raise ValueError('Pinned bcf-client 0.9.0 required')
    project = BcfXml.create_new('IFC port coordination review')
    for title, description, selected, point in issue_records(report):
        topic = project.add_topic(title, description, 'Building Services Agent', 'Issue', 'Open')
        if selected and point is not None:
            viewpoint = VisualizationInfoHandler.create_from_point_and_guids(np.asarray(point), *selected)
            topic.add_visinfo_handler(viewpoint)

    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent) as temporary:
        archive = Path(temporary)/'review.bcf'
        project.save(archive)
        checked = verify(report, archive)
        if file_hash(source) != report['source_sha256']:
            raise ValueError('IFC changed before BCF publication')
        with archive.open('rb') as stream, out.open('xb') as target:
            shutil.copyfileobj(stream, target)

    if file_hash(out) != checked['bcf_sha256']:
        raise ValueError('Published BCF differs from the verified archive')
    return checked


def run(source, out, tolerance_m):
    if tolerance_m is None:
        raise ValueError('Explicit metre tolerance required for IFC port gap issues')
    return write(inventory(source, tolerance_m), source, out)
