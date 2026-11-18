"""Build a repeatable committed-source candidate; never publish a release."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def build(out):
    out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():
        raise ValueError('Fresh repository runs output required')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    # Archive the committed tree without checkout-dependent newline conversion.
    out.mkdir(parents=True)
    archive=out/'building-services-agent-source.zip'
    subprocess.run(['git','-c','core.autocrlf=false','-c','core.eol=lf',
                    'archive','--format=zip','--output',str(archive),commit],cwd=ROOT,check=True)
    with zipfile.ZipFile(archive) as saved:
        entries=saved.infolist()
        forbidden={'runs','tools','.git','.codex','.venv','.bsa','build','dist','__pycache__'}
        for item in entries:
            p=Path(item.filename)
            if p.is_absolute() or '..' in p.parts or forbidden.intersection(p.parts) or p.name=='.env':
                raise ValueError('Candidate contains excluded runtime/private path: '+item.filename)
        if saved.testzip() is not None:raise ValueError('Candidate CRC validation failed')
        required={'pyproject.toml','src/bsa/workspace.py','scripts/setup_radiance.py',
                  'docs/START_USING.md','examples/office-electrical/project.json'}
        if not required.issubset(saved.namelist()):raise ValueError('Candidate source resources missing')
        uncompressed=sum(x.file_size for x in entries)
    with archive.open('rb') as stream:
        archive_hash=hashlib.file_digest(stream,'sha256').hexdigest()
    receipt=dict(schema='bsa.source-candidate/1',commit=commit,
        archive=archive.name,sha256=archive_hash,
        bytes=archive.stat().st_size,uncompressed_bytes=uncompressed,entries=len(entries),
        git_version=subprocess.check_output(['git','--version'],text=True).strip(),
        format='git archive zip',release_published=False,design_accepted=False)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    print(json.dumps(build(parser.parse_args().out),indent=2))
