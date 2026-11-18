"""Write an offline BCF issue package for IFC port coordination findings."""
from collections import Counter
from dataclasses import astuple
import importlib.metadata
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, UUID, uuid5
from zipfile import BadZipFile

from . import workspace
from .ifc_port_inventory import inventory, review_status
from .source_refs import file_hash


PROJECT_NAME = 'IFC port coordination review'


def project_name(tolerance_m):
    return f'{PROJECT_NAME} (port gap tolerance {float(tolerance_m)!r} m)'


def review_project_name(report):
    name = project_name(report['connection_gaps']['tolerance_m'])
    comparison = report.get('comparison')
    if comparison is None:
        return name
    shift = comparison.get('max_port_shift_m')
    alignment = comparison.get('alignment', {}).get('sha256', 'none')
    return (f"{name} | baseline SHA-256 {comparison['baseline_sha256']}"
            f" | maximum shift in metres {float(shift) if shift is not None else 'unset'}"
            f" | alignment SHA-256 {alignment}")


def project_id(report):
    source_hash = report['source_sha256']
    return uuid5(NAMESPACE_URL, f'https://github.com/LYUml/building-services-agent/ifc/{source_hash}')


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
    for guid in comparison.get('added_ports', []):
        port = ports[guid]
        yield (f'IFC port added {guid}', f'{basis}\nPort {guid} appears only in the current export.',
               port['owner_guids'], port['origin_m'])
    for guid in comparison.get('removed_ports', []):
        yield (f'IFC port removed {guid}', f'{basis}\nPort {guid} appears only in the baseline export.',
               [], None)
    for change in comparison.get('changed_ports', []):
        guid = change['guid']
        before, after = change['before'], change['after']
        description = (f"{basis}\nPort {guid} differs from the baseline."
                       f"\nOwners: {before['owner_guids']} -> {after['owner_guids']}."
                       f"\nFlow direction: {before['flow_direction']} -> {after['flow_direction']}.")
        yield (f'IFC port attributes changed {guid}', description,
               after['owner_guids'], after['origin_m'])
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
    from bcf.v3.visinfo import VisualizationInfoHandler
    import numpy as np
    if importlib.metadata.version('bcf-client') != '0.9.0':
        raise ValueError('Pinned bcf-client 0.9.0 required')
    expected = Counter()
    project_guid = project_id(report)
    gaps = report['connection_gaps']
    tolerance_m = gaps['tolerance_m']
    before = file_hash(archive)
    for title, description, selected, point in issue_records(report):
        view_selection = tuple(selected) if point is not None else ()
        cameras = ()
        if view_selection:
            view = VisualizationInfoHandler.create_from_point_and_guids(np.asarray(point), *view_selection)
            cameras = ((astuple(view.visualization_info.perspective_camera), None),)
        expected[str(uuid5(project_guid, title)), title, description, view_selection, cameras, 'Open'] += 1
    try:
        with BcfXml.load(archive) as restored:
            if UUID(restored.project.project_id) != project_guid:
                raise ValueError('Saved BCF project identity differs from the source IFC')
            tolerance_bound = restored.project.name == review_project_name(report)
            if not tolerance_bound and (report.get('comparison') or restored.project.name != PROJECT_NAME):
                raise ValueError('Saved BCF project name does not match the supplied port gap tolerance or baseline settings')
            actual = Counter()
            for directory_guid, topic in restored.topics.items():
                if directory_guid != topic.topic.guid:
                    raise ValueError('Saved BCF topic directory differs from its markup GUID')
                views = [handler.visualization_info for handler in topic.viewpoints.values()]
                selections = [component.ifc_guid for view in views
                              for component in view.components.selection.component]
                cameras = tuple(
                    (astuple(view.perspective_camera) if view.perspective_camera is not None else None,
                     astuple(view.orthogonal_camera) if view.orthogonal_camera is not None else None)
                    for view in views
                )
                actual[topic.topic.guid, topic.topic.title, topic.topic.description, tuple(sorted(selections)),
                       cameras, topic.topic.topic_status] += 1
    except (AttributeError, BadZipFile) as exc:
        raise ValueError('Invalid IFC port coordination BCF archive') from exc
    if actual != expected or file_hash(archive) != before:
        raise ValueError('Saved BCF topics or cameras differ from the IFC coordination issues')
    status, reason = review_status(report)
    return dict(source_sha256=report['source_sha256'], bcf_sha256=before,
                tolerance_m=tolerance_m, archive_tolerance_bound=tolerance_bound,
                topics=sum(actual.values()),
                measured_relationships=gaps['measured_relationships'],
                unavailable_relationships=len(gaps['unavailable_relationships']),
                ifc_review_status=status, ifc_review_reason=reason,
                bcf_reopen_verified=True, design_accepted=False)


def check_inputs(report, source, baseline, alignment):
    expected = [(source, report['source_sha256'])]
    if baseline is not None:
        expected.append((baseline, report['comparison']['baseline_sha256']))
    if alignment is not None:
        expected.append((alignment, report['comparison']['alignment']['sha256']))
    if any(file_hash(Path(path)) != sha256 for path, sha256 in expected):
        raise ValueError('IFC or alignment input changed during BCF processing')


def write(report, source, out, *, baseline=None, alignment=None):
    from bcf.v3.bcfxml import BcfXml
    from bcf.v3.topic import TopicHandler
    from bcf.v3.visinfo import VisualizationInfoHandler
    import numpy as np

    source, out = (Path(p).resolve() for p in (source, out))
    if not workspace.intake_output(out) or out.suffix.lower() not in ('.bcf', '.bcfzip') or out.exists():
        raise ValueError('Use a fresh BCF archive path in the permitted output workspace')
    if importlib.metadata.version('bcf-client') != '0.9.0':
        raise ValueError('Pinned bcf-client 0.9.0 required')
    project = BcfXml.create_new(review_project_name(report))
    project_guid = project_id(report)
    project.project.project_id = str(project_guid)
    for title, description, selected, point in issue_records(report):
        guid = str(uuid5(project_guid, title))
        if guid in project.topics:
            raise ValueError('Duplicate IFC coordination issue identity')
        provisional = TopicHandler.create_new(title, description, 'Building Services Agent', 'Issue', 'Open')
        provisional.topic.guid = guid
        topic = TopicHandler(topic_dir=Path(guid))
        topic.markup = provisional.markup
        project.topics[guid] = topic
        if selected and point is not None:
            viewpoint = VisualizationInfoHandler.create_from_point_and_guids(np.asarray(point), *selected)
            topic.add_visinfo_handler(viewpoint)

    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent) as temporary:
        archive = Path(temporary)/'review.bcf'
        project.save(archive)
        checked = verify(report, archive)
        check_inputs(report, source, baseline, alignment)
        with archive.open('rb') as stream, out.open('xb') as target:
            shutil.copyfileobj(stream, target)

    if file_hash(out) != checked['bcf_sha256']:
        raise ValueError('Published BCF differs from the verified archive')
    return checked


def run(source, out, tolerance_m, *, baseline=None, max_port_shift_m=None, alignment=None):
    if tolerance_m is None:
        raise ValueError('Explicit metre tolerance required for IFC port gap issues')
    report = inventory(source, tolerance_m, baseline=baseline, max_port_shift_m=max_port_shift_m,
                       alignment=alignment)
    return write(report, source, out, baseline=baseline, alignment=alignment)


def verify_export(source, archive, tolerance_m, *, baseline=None, max_port_shift_m=None, alignment=None):
    if tolerance_m is None:
        raise ValueError('Explicit metre tolerance required for IFC port gap issues')
    archive = Path(archive).resolve()
    if not workspace.allowed(archive) or archive.suffix.lower() not in ('.bcf', '.bcfzip'):
        raise ValueError('BCF archive in the permitted workspace required')
    report = inventory(source, tolerance_m, baseline=baseline, max_port_shift_m=max_port_shift_m,
                       alignment=alignment)
    result = verify(report, archive)
    check_inputs(report, source, baseline, alignment)
    return result
