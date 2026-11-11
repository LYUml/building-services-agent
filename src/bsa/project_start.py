"""Stage original briefs and compose existing source-linked intake/handoff tools."""
import argparse
import json
from pathlib import Path
import shutil
from .cli import digest
from .workflow_draft import draft
from .work_plan_review import template

ROOT=Path(__file__).resolve().parents[2]


def start(brief,out,*,supplements=()):
    originals=[Path(p).resolve() for p in (brief,*supplements)];out=Path(out).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('New repository runs project directory required')
    if len(originals)!=len(set(originals)):raise ValueError('Distinct original source documents required')
    for p in originals:
        if not p.is_file() or p.suffix.lower() not in ('.pdf','.docx','.md','.txt'):raise ValueError('Existing PDF,DOCX,Markdown or text briefs required')
        if p.is_relative_to(out):raise ValueError('Project output must not contain original sources')
    before={str(p):digest(p) for p in originals};out.mkdir(parents=True)
    methods={str(Path(__file__).with_name(name).resolve()):digest(Path(__file__).with_name(name)) for name in ('project_start.py','workflow_draft.py','work_plan_review.py')}
    staged=[]
    for i,p in enumerate(originals,1):
        folder=out/'sources'/f'D{i:03}';folder.mkdir(parents=True)
        target=folder/p.name;shutil.copyfile(p,target)
        if digest(target)!=before[str(p)]:raise ValueError('Staged source differs from original snapshot')
        staged.append(target)
    errors={};result=None;review_ready=False
    try:
        result=draft(staged[0],out/'plan.json',staged[1:])
        if result['extraction_issues']:
            errors['work_review']='Inspect extraction issues against original pages before preparing the interpretation handoff.'
        else:
            template(out/'plan.json',out/'work-review.json');review_ready=True
    except Exception as exc:
        errors['intake']=type(exc).__name__+': '+str(exc)
    if any(not p.is_file() or digest(p)!=before[str(p)] for p in originals):raise ValueError('Original document changed during intake')
    if any(digest(p)!=before[str(original)] for original,p in zip(originals,staged)):raise ValueError('Staged document changed during intake')
    if any(digest(Path(p))!=sha for p,sha in methods.items()):raise ValueError('Intake orchestration method changed during execution')
    report=dict(status='needs_source_review' if errors else 'needs_interpretation',
        sources=[dict(original=str(p),staged=s.relative_to(out).as_posix(),sha256=before[str(p)]) for p,s in zip(originals,staged)],
        originals_unchanged=True,methods=methods,draft=result,stage_errors=errors,interpretation_template_ready=review_ready,
        artifacts={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()},
        design_accepted=False,scope='Source staging and conservative interpretation handoff only;no semantic design,engineering execution or acceptance')
    (out/'intake.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('brief');p.add_argument('--supplement',action='append',default=[]);p.add_argument('--out',required=True)
    a=p.parse_args();r=start(a.brief,a.out,supplements=a.supplement)
    print(json.dumps(dict(status=r['status'],interpretation_template_ready=r['interpretation_template_ready'],stage_errors=r['stage_errors'],design_accepted=False),indent=2))
    return 2


if __name__=='__main__':raise SystemExit(main())
