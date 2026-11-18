"""Verify exact ZIP member bytes against an explicit delivery manifest."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from stat import S_IFLNK, S_IFMT
from zipfile import BadZipFile, ZipFile

from . import workspace
from .source_refs import file_hash


def member_name(name):
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or '\\' in name or ':' in name or '\0' in name
            or '..' in path.parts or path.as_posix() != name or name == '.'):
        raise ValueError(f'Invalid delivery member path: {name!r}')
    return name.casefold()


def verify(archive_path, manifest_path):
    archive_path, manifest_path = (Path(path).resolve() for path in (archive_path, manifest_path))
    if not all(workspace.allowed(path) for path in (archive_path, manifest_path)):
        raise ValueError('Use archive and manifest files from the permitted workspace')
    manifest = manifest_path.read_bytes()
    expected = json.loads(manifest, object_pairs_hook=unique_object)
    if (not isinstance(expected, dict) or not expected
            or any(not isinstance(pin, str) or not re.fullmatch(r'[a-f0-9]{64}', pin)
                   for pin in expected.values())):
        raise ValueError('Expected a nonempty object mapping ZIP member paths to SHA-256 hashes')
    normalized = [member_name(name) for name in expected]
    if len(set(normalized)) != len(normalized):
        raise ValueError('Manifest repeats a ZIP member path')

    before = file_hash(archive_path)
    with ZipFile(archive_path) as archive:
        entries = archive.infolist()
        names = [member_name(info.orig_filename[:-1] if info.is_dir() else info.orig_filename)
                 for info in entries]
        if any(count > 1 for count in Counter(names).values()):
            raise ValueError('Duplicate ZIP member path')
        files = {info.filename: info for info in entries if not info.is_dir()}
        if any(S_IFMT(info.external_attr >> 16) == S_IFLNK for info in entries):
            raise ValueError('ZIP links are unsupported')
        if files.keys() != expected.keys():
            raise ValueError(f'ZIP member inventory differs (missing {len(expected.keys()-files.keys())}, '
                             f'unexpected {len(files.keys()-expected.keys())})')
        for name, info in files.items():
            with archive.open(info) as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected[name]:
                    raise ValueError(f'ZIP member hash mismatch: {name}')

    if file_hash(archive_path) != before or manifest_path.read_bytes() != manifest:
        raise ValueError('Archive or manifest changed during verification')
    return dict(archive_sha256=before, manifest_sha256=hashlib.sha256(manifest).hexdigest(),
                verified_members=len(files), integrity_pass=True, design_accepted=False)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON manifest key')
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.archive, args.manifest), indent=2))
    except (OSError, ValueError, BadZipFile, RuntimeError, NotImplementedError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
