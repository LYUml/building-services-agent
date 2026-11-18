"""Write an offline BCF issue package for measured IFC port gaps."""
import importlib.metadata
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from . import workspace
from .ifc_port_inventory import inventory
from .source_refs import file_hash


def run(source, out, tolerance_m):
    from bcf.v3.bcfxml import BcfXml
    from bcf.v3.visinfo import VisualizationInfoHandler
    import numpy as np

    source, out = (Path(p).resolve() for p in (source, out))
    if not workspace.intake_output(out) or out.suffix.lower() not in ('.bcf', '.bcfzip') or out.exists():
        raise ValueError('Use a fresh BCF archive path in the permitted output workspace')
    if importlib.metadata.version('bcf-client') != '0.9.0':
        raise ValueError('Pinned bcf-client 0.9.0 required')
    if tolerance_m is None:
        raise ValueError('Explicit metre tolerance required for IFC port gap issues')

    report = inventory(source, tolerance_m)
    gaps = report['connection_gaps']
    ports = {row['guid']: row for row in report['ports']}
    project = BcfXml.create_new('IFC port gap review')
    expected = {}
    for gap in gaps['separated_relationships']:
        a, b = gap['port_guids']
        title = f"IFC port gap {gap['guid']}"
        description = (f"Saved IFC SHA-256 {report['source_sha256']}\n"
                       f"{a} to {b}: {gap['separation_m']:.9g} m, tolerance {tolerance_m:.9g} m.\n"
                       "Review the exported port origins and joint geometry.")
        topic = project.add_topic(title, description, 'Building Services Agent', 'Issue', 'Open')
        selected = sorted(set(ports[a]['owner_guids'] + ports[b]['owner_guids']))
        if selected:
            midpoint = np.mean(np.asarray(gap['origins_m']), axis=0)
            viewpoint = VisualizationInfoHandler.create_from_point_and_guids(midpoint, *selected)
            topic.add_visinfo_handler(viewpoint)
        expected[topic.topic.guid] = (title, description, selected)

    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent) as temporary:
        archive = Path(temporary)/'review.bcf'
        project.save(archive)
        with BcfXml.load(archive) as restored:
            actual = {}
            for guid, topic in restored.topics.items():
                selections = [component.ifc_guid for handler in topic.viewpoints.values()
                              for component in handler.visualization_info.components.selection.component]
                actual[guid] = (topic.topic.title, topic.topic.description, sorted(selections))
            if actual != expected or any(topic.topic.topic_status != 'Open' for topic in restored.topics.values()):
                raise ValueError('Saved BCF topics differ from the IFC coordination issues')
        if file_hash(source) != report['source_sha256']:
            raise ValueError('IFC changed before BCF publication')
        with archive.open('rb') as stream, out.open('xb') as target:
            shutil.copyfileobj(stream, target)

    return dict(source_sha256=report['source_sha256'], bcf_sha256=file_hash(out),
                topics=len(expected), unavailable_relationships=len(gaps['unavailable_relationships']),
                bcf_reopen_verified=True, design_accepted=False)
