"""Stage hash-pinned public coursework for noncommercial intake; never solve or approve it."""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow_draft import draft
ROOT=Path(__file__).resolve().parents[1]


def run(out,cache=None):
    manifest_path=ROOT/'benchmarks/mit-4401-2018/sources.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ProjectError('new repository-local benchmark output required')
    cache=Path(cache).resolve() if cache else None
    out.mkdir(parents=True);files=[]
    for row in manifest['files']:
        relative=Path(row['file']);destination=(out/relative).resolve()
        if relative.is_absolute() or not destination.is_relative_to(out) or not row['url'].startswith('https://ocw.mit.edu/'):raise ProjectError('reviewed local source mapping required')
        data=(cache/relative.name).read_bytes() if cache else urlopen(row['url'],timeout=30).read()
        from hashlib import sha256
        if sha256(data).hexdigest()!=row['sha256']:raise ProjectError('public source hash differs: '+relative.name)
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data);files.append(destination)
    primary=out/manifest['primary'];supplements=[p for p in files if p!=primary]
    result=draft(primary,out/'plan.json',supplements)
    summary=dict(manifest_sha256=digest(manifest_path),source_hashes={p.relative_to(out).as_posix():digest(p) for p in files},passages=result['passages'],extraction_issue_count=len(result['extraction_issues']),extraction_issue_codes=sorted({i['code'] for i in result['extraction_issues']}),license=manifest['license'],creator=manifest['creator'],interpretation_complete=False,design_accepted=False)
    (out/'benchmark-intake.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--cache',type=Path)
    print(json.dumps(run(**vars(p.parse_args()))))
