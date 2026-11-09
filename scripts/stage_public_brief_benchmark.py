"""Stage hash-pinned public coursework for noncommercial intake; never solve or approve it."""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.workflow_draft import draft
ROOT=Path(__file__).resolve().parents[1]


def apply_source_review(plan_path,review_path):
    from bsa.workflow import plan_documents,validate_plan
    from hashlib import sha256
    plan_path,review_path=Path(plan_path).resolve(),Path(review_path).resolve()
    plan=json.loads(plan_path.read_text(encoding='utf-8'));review=json.loads(review_path.read_text(encoding='utf-8'))
    document=plan_documents(plan_path.parent,plan)
    actual={d['path']:d['sha256'] for d in document['documents']}
    if review['source_hashes']!=actual or set(review['issue_notes'])!={i['id'] for i in document['issues']}:raise ProjectError('reviewed source/issue identity differs')
    rows={r['id']:r for r in document['passages']}
    for id in review['context_passages']:
        text=rows[id]['text'].strip()
        if sha256(rows[id]['text'].encode('utf-8')).hexdigest()!=review['context_passage_text_sha256'][id] or not (text.isdigit() or text.startswith('MIT OpenCourseWare')):raise ProjectError('reviewed context no longer matches boilerplate')
    if any(t['kind']!='manual' for t in plan['tasks']):raise ProjectError('source review applies only to the original blocked intake scaffold')
    contexts=set(review['context_passages']);removed={r['task'] for r in plan['requirements'] if r['passage'] in contexts}
    plan['requirements']=[r for r in plan['requirements'] if r['passage'] not in contexts]
    if any(r['task'] in removed for r in plan['requirements']):raise ProjectError('context task also carries a technical requirement')
    plan['tasks']=[t for t in plan['tasks'] if t['id'] not in removed]
    plan['unresolved_inputs']=[i for i in plan['unresolved_inputs'] if not set(i['blocks_tasks'])<=removed]
    for id in contexts:plan['passage_dispositions'][id]='context'
    plan.update(document_review=review['issue_notes'],context_notes=review['context_passages'],source_review_sha256=digest(review_path))
    plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    validate_plan(plan_path)
    return dict(review_notes_applied=len(review['issue_notes']),context_passages=len(contexts),pending_interpretation_tasks=len(plan['tasks']))


def run(out,cache=None,apply_review=False):
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
    if apply_review:summary.update(apply_source_review(out/'plan.json',ROOT/'benchmarks/mit-4401-2018/source-review.json'))
    (out/'benchmark-intake.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--cache',type=Path);p.add_argument('--apply-reviewed-notes',dest='apply_review',action='store_true')
    print(json.dumps(run(**vars(p.parse_args()))))
