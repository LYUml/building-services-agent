"""Read selected saved RVT metadata without launching a Revit host."""
from pathlib import Path

from . import workspace
from .source_refs import file_hash


def inspect(source):
    source = Path(source).resolve()
    if not workspace.allowed(source) or not source.is_file() or source.suffix.lower() != '.rvt':
        raise ValueError('Select an existing RVT in the permitted workspace')
    import rvt

    if rvt.__version__ != '0.25.0':
        raise ValueError('Pinned rvt 0.25.0 required')
    fingerprint = file_hash(source)
    try:
        fields = rvt.RevitFile(str(source)).metadata(redact=True)
    except (OSError, ValueError, RuntimeError) as error:
        raise ValueError('Could not read saved RVT metadata') from error
    if file_hash(source) != fingerprint:
        raise ValueError('RVT file changed during metadata inspection')
    version = fields.get('revit_version')
    if type(version) is not int or version <= 0:
        raise ValueError('Saved Revit release could not be established')
    workshared = fields.get('workshared')
    cloud = fields.get('single_user_cloud_model')
    return dict(schema='bsa.revit-file-metadata/1', source_sha256=fingerprint,
                reader_version=rvt.__version__, revit_version=version,
                workshared=workshared if type(workshared) is bool else None,
                single_user_cloud_model=cloud if type(cloud) is bool else None,
                native_revit_executed=False, design_accepted=False)
