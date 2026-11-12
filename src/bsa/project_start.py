"""Stage original briefs and compose existing source-linked intake/handoff tools."""
import argparse
import json
from pathlib import Path
import shutil
from .cli import digest
from .workflow_draft import draft
from .work_plan_review import template
from .workspace import intake_output

ROOT=Path(__file__).resolve().parents[2]


def start(brief,out,*,supplements=(),references=()):
    supplements,references=tuple(supplements),tuple(references)
    originals=[Path(p).resolve() for p in (brief,*supplements,*references)];out=Path(out).resolve()
    if not intake_output(out) or out.exists():raise ValueError('New project directory under repository runs or explicit host workspace required')
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
    errors={};result=None;review_ready=False;effective_plan=out/'plan.json';requirements_module=None
    try:
        result=draft(staged[0],out/'plan.json',staged[1:])
        if references:
            plan=json.loads(effective_plan.read_text(encoding='utf-8'))
            prefixes={f'D{i:03}:' for i in range(2+len(supplements),len(staged)+1)}
            context={k for k in plan['passage_dispositions'] if any(k.startswith(prefix) for prefix in prefixes)}
            removed={r['task'] for r in plan['requirements'] if r['passage'] in context}
            for passage in context:plan['passage_dispositions'][passage]='context'
            plan['requirements']=[r for r in plan['requirements'] if r['passage'] not in context]
            plan['tasks']=[t for t in plan['tasks'] if t['id'] not in removed]
            plan['unresolved_inputs']=[i for i in plan['unresolved_inputs'] if not set(i['blocks_tasks'])<=removed]
            role_record=out/'source-roles.json'
            role_record.write_text(json.dumps(dict(original_plan_sha256=digest(effective_plan),
                reference_passages=sorted(context),basis='Explicit host --reference selection;retain indexed source content and extraction review,without inferring assignment obligations from reference passages.',
                design_accepted=False),indent=2),encoding='utf-8')
            plan['planning_records']=[role_record.name]
            effective_plan=out/'role-plan.json';effective_plan.write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
        if result['extraction_issues']:
            errors['work_review']='Inspect extraction issues against original pages before preparing the interpretation handoff.'
        else:
            template(effective_plan,out/'work-review.json');review_ready=True
            from .modules import run as run_module
            request=dict(schema='bsa.module-request/1',project_id=out.name,scenario_id='source-intake',
                capability='requirements.source-inventory',coordinate_frame=dict(id='intake-no-geometry-claim',kind='source-world-si',length_unit='m',georeferenced=False),
                sources=dict(plan=dict(path=effective_plan.name,sha256=digest(effective_plan))))
            request_path=out/'requirements-request.json'
            request_path.write_text(json.dumps(request,indent=2),encoding='utf-8')
            module=run_module(request_path,'bsa.source-requirements',out/'requirements')
            requirements_module=dict(result='requirements/result.json',execution=module['execution'],interpretation_status='not_assessed')
            if module['execution']['status']!='completed':errors['requirements_inventory']='Common requirements inventory did not complete;inspect retained module diagnostics.'
    except Exception as exc:
        errors['intake']=type(exc).__name__+': '+str(exc)
    if any(not p.is_file() or digest(p)!=before[str(p)] for p in originals):raise ValueError('Original document changed during intake')
    if any(digest(p)!=before[str(original)] for original,p in zip(originals,staged)):raise ValueError('Staged document changed during intake')
    if any(digest(Path(p))!=sha for p,sha in methods.items()):raise ValueError('Intake orchestration method changed during execution')
    report=dict(status='needs_source_review' if errors else 'needs_interpretation',
        sources=[dict(original=str(p),staged=s.relative_to(out).as_posix(),sha256=before[str(p)],
            role='primary' if i==0 else 'supplement' if i<=len(supplements) else 'reference') for i,(p,s) in enumerate(zip(originals,staged))],
        effective_plan=effective_plan.relative_to(out).as_posix() if effective_plan.is_file() else None,requirements_module=requirements_module,
        originals_unchanged=True,methods=methods,draft=result,stage_errors=errors,interpretation_template_ready=review_ready,
        artifacts={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()},
        design_accepted=False,scope='Source staging and conservative interpretation handoff only;no semantic design,engineering execution or acceptance')
    (out/'intake.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('brief');p.add_argument('--supplement',action='append',default=[]);p.add_argument('--reference',action='append',default=[]);p.add_argument('--out',required=True)
    a=p.parse_args();r=start(a.brief,a.out,supplements=a.supplement,references=a.reference)
    print(json.dumps(dict(status=r['status'],interpretation_template_ready=r['interpretation_template_ready'],stage_errors=r['stage_errors'],design_accepted=False),indent=2))
    return 2


if __name__=='__main__':raise SystemExit(main())
