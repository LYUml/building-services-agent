"""Apply explicit source-inspection notes to a fresh unchanged manual scaffold."""
import copy
import json
from pathlib import Path
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from .workflow import plan_documents,validate_plan
from .documents import check_review


def run(plan,notes,out):
    plan,out=Path(plan).resolve(),Path(out).resolve()
    if not all(allowed(p) for p in (plan,out)) or out.parent!=plan.parent or out.exists() or out.suffix!='.json':raise ValueError('Fresh sibling reviewed JSON source plan required')
    source=read_json(plan)
    if source.get('document_review') or not source.get('tasks') or any(t['kind']!='manual' for t in source['tasks']):raise ValueError('Unreviewed manual source scaffold required')
    documents=plan_documents(plan.parent,source);check_review(documents,notes)
    pins={str(p):digest(p) for p in [plan,*map(Path,documents.get('supporting_files',[]))]}
    for row in [source,*source.get('supplemental_briefs',[])]:
        p=(plan.parent/row['brief']).resolve();pins[str(p)]=digest(p)
    result=copy.deepcopy(source);result['document_review']=copy.deepcopy(notes)
    result['planning_records']=list(dict.fromkeys(source.get('planning_records',[])+[plan.name]))
    candidate=out.with_name(out.name+'.candidate')
    if candidate.exists():raise ValueError('Fresh source review candidate required')
    created=False
    try:
        with candidate.open('x',encoding='utf-8') as stream:
            created=True;json.dump(result,stream,indent=2,ensure_ascii=False)
        validate_plan(candidate)
        if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Source changed during source review')
        with out.open('xb') as stream:stream.write(candidate.read_bytes())
    finally:
        if created and candidate.exists():candidate.unlink()
    return dict(plan=str(out),status='needs_interpretation',source_inspection_notes=len(notes),requirements_preserved=True,
        ordinary_gaps_preserved=True,semantic_completeness='not_assessed',design_accepted=False)
