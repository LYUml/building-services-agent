"""Prepare a local unsigned review bundle; no signing, registration or execution."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(output):
    repo=Path(__file__).resolve().parents[1]
    output=Path(output).resolve()
    if not output.is_relative_to(repo/'runs') or output.exists():
        raise ValueError('New repository-local runs directory required')
    adapter=repo/'adapters/revit'
    build=adapter/'bin/Release/net10.0-windows'
    # Explicit allowlist excludes proprietary API references, PDBs and user models.
    payload=[build/'Bsa.Revit.dll',build/'Bsa.Revit.deps.json']
    sources=[*sorted(adapter.glob('*.cs')),adapter/'Bsa.Revit.csproj',adapter/'global.json']
    if any(not p.is_file() for p in payload+sources):
        raise ValueError('Build output and complete local adapter sources required')
    pins={str(p.relative_to(repo)):digest(p) for p in payload+sources}
    manifest=dict(payload={p.name:pins[str(p.relative_to(repo))] for p in payload},
        sources={str(p.relative_to(repo)):pins[str(p.relative_to(repo))] for p in sources},
        build_provenance='Current build output and current source hashes recorded; this packager does not compile or prove their correspondence.',
        scope='Local candidate for authorized signing/deployment review only. Not a signed release or verified Revit integration.',
        root_license_present=(repo/'LICENSE').is_file(),signed_release=False,native_executed=False,
        excluded=['Autodesk API binaries','symbols','models','credentials','private coursework'],
        pending=['Owner distribution-license decision','Approved signing/deployment trust basis','Post-signing exact-binary verification','Native capture and creation/rollback','Saved model reopening and connected-system acceptance'])
    output.mkdir(parents=True)
    archive=output/'Bsa.Revit-review.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in payload:z.writestr(p.name,p.read_bytes())
        z.writestr('review-manifest.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(archive) as z:
        if set(z.namelist())!={p.name for p in payload}|{'review-manifest.json'}:
            raise ValueError('Unexpected archive content')
        if any(hashlib.sha256(z.read(p.name)).hexdigest()!=manifest['payload'][p.name] for p in payload):
            raise ValueError('Archived payload differs from build output')
    if any(digest(repo/name)!=sha for name,sha in pins.items()):
        raise ValueError('Input changed while preparing handoff')
    (output/'preparation.json').write_text(json.dumps(dict(archive_sha256=digest(archive),manifest=manifest),indent=2),encoding='utf-8')
    return archive


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True)
    print(prepare(p.parse_args().out))
