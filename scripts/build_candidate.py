"""Build a repeatable committed-source candidate; never publish a release."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import tomllib
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def verify_committed_bytes(saved, commit, release_manifest):
    tree = subprocess.check_output(['git', 'ls-tree', '-rz', commit], cwd=ROOT)
    expected = {}
    for row in tree.split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        if kind != b'blob' or mode not in (b'100644', b'100755'):
            raise ValueError('Candidate requires regular files in the committed source tree')
        expected[name.decode('utf-8')] = oid.decode('ascii')
    paths = b''.join(name.encode('utf-8') + b'\0' for name in expected)
    attributes = subprocess.check_output(
        ['git', 'check-attr', '--source=' + commit, '-z', '--stdin', 'export-ignore'],
        cwd=ROOT, input=paths).split(b'\0')[:-1]
    if len(attributes) != 3 * len(expected):
        raise ValueError('Candidate could not verify committed archive exclusions')
    for name, attribute, value in zip(attributes[::3], attributes[1::3], attributes[2::3]):
        if attribute != b'export-ignore':
            raise ValueError('Unexpected candidate archive attribute')
        if value == b'set':
            del expected[name.decode('utf-8')]
    files = [item for item in saved.infolist() if not item.is_dir()]
    manifests = [item for item in files if item.filename == '.bsa-release.json']
    if ('.bsa-release.json' in expected or len(manifests) != 1
            or saved.read(manifests[0]) != release_manifest):
        raise ValueError('Candidate release manifest differs from the selected commit')
    files.remove(manifests[0])
    if len(files) != len(expected) or {item.filename for item in files} != expected.keys():
        raise ValueError('Candidate file inventory differs from the committed archive scope')
    algorithm = subprocess.check_output(['git', 'rev-parse', '--show-object-format'], cwd=ROOT, text=True).strip()
    for item in files:
        digest = hashlib.new(algorithm, f'blob {item.file_size}\0'.encode('ascii'))
        with saved.open(item) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != expected[item.filename]:
            raise ValueError('Candidate member differs from the committed blob: ' + item.filename)
    return len(files)


def build(out):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():
        raise ValueError('Fresh repository runs output required')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    # Archive the committed tree without checkout-dependent newline conversion.
    out.mkdir(parents=True)
    archive=out/'building-services-agent-source.zip'
    project = subprocess.check_output(['git','show',commit+':pyproject.toml'],cwd=ROOT,text=True)
    version = tomllib.loads(project)['project']['version']
    release_manifest = (json.dumps(dict(schema='bsa.release-source/1', commit=commit, version=version),
                                   sort_keys=True) + '\n').encode('ascii')
    with TemporaryDirectory(dir=out) as temporary:
        manifest = Path(temporary) / '.bsa-release.json'
        manifest.write_bytes(release_manifest)
        subprocess.run(['git','-c','core.autocrlf=false','-c','core.eol=lf',
                        'archive','--format=zip','--output',str(archive),
                        '--add-file='+str(manifest),commit],cwd=ROOT,check=True)
    with zipfile.ZipFile(archive) as saved:
        entries=saved.infolist()
        forbidden={'runs','tools','.git','.codex','.venv','.bsa','build','dist','__pycache__'}
        for item in entries:
            p=Path(item.filename)
            if p.is_absolute() or '..' in p.parts or forbidden.intersection(p.parts) or p.name=='.env':
                raise ValueError('Candidate contains excluded runtime/private path: '+item.filename)
        verified_members=verify_committed_bytes(saved,commit,release_manifest)
        required={'pyproject.toml','src/bsa/workspace.py','scripts/setup_radiance.py',
                  'docs/START_USING.md','examples/office-electrical/project.json'}
        if not required.issubset(saved.namelist()):raise ValueError('Candidate source resources missing')
        uncompressed=sum(x.file_size for x in entries)
    with archive.open('rb') as stream:
        archive_hash=hashlib.file_digest(stream,'sha256').hexdigest()
    receipt=dict(schema='bsa.source-candidate/1',commit=commit,version=version,
        archive=archive.name,sha256=archive_hash,
        bytes=archive.stat().st_size,uncompressed_bytes=uncompressed,entries=len(entries),
        verified_committed_members=verified_members,
        git_version=subprocess.check_output(['git','--version'],text=True).strip(),
        format='git archive zip',release_published=False,design_accepted=False)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    print(json.dumps(build(parser.parse_args().out),indent=2))
