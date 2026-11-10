"""Apply explicit reviewed work decomposition without losing source-passage coverage."""
import copy
import hashlib
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .workflow import plan_documents,validate_plan,local_path


def apply(plan,review):
    plan,review=Path(plan).resolve(),Path(review).resolve();root=plan.parent
    if not review.is_relative_to(root):raise ProjectError('planning review must be repository project-local')
    before={str(p):digest(p) for p in (plan,review)}
    validate_plan(plan)
    original=json.loads(plan.read_text(encoding='utf-8-sig'));record=json.loads(review.read_text(encoding='utf-8-sig'))
    source_names={original['brief']}|{r['brief'] for r in original.get('supplemental_briefs',[])}
    if set(record.get('source_sha256',{}))!=source_names or any(digest(local_path(root,name))!=sha for name,sha in record['source_sha256'].items()):raise ProjectError('work review source identity differs')
    passages={r['id']:r for r in plan_documents(root,original)['passages']}
    technical={k for k,v in original['passage_dispositions'].items() if v=='requirement'}
    mapping=record.get('passages',{})
    if set(mapping)!=technical:raise ProjectError('work review must preserve every technical passage')
    packages=record.get('tasks',[]);known={}
    for row in packages:
        if not isinstance(row,dict) or set(row)!={'id','description','blocker','acceptance','requires_pass'} or any(not isinstance(row[k],str) or not row[k].strip() for k in ('id','description','blocker','acceptance')) or row['id'] in known:raise ProjectError('unique explicit work task/acceptance/blocker required')
        deps=row['requires_pass']
        if not isinstance(deps,list) or any(not isinstance(d,str) or d not in known for d in deps) or len(set(deps))!=len(deps):raise ProjectError('work dependencies must be unique earlier reviewed tasks')
        known[row['id']]=row
    if not known:raise ProjectError('reviewed tasks required')
    used=set()
    for id,row in mapping.items():
        if set(row)!={'text_sha256','tasks'} or hashlib.sha256(passages[id]['text'].encode('utf-8')).hexdigest()!=row['text_sha256']:raise ProjectError('reviewed passage text changed')
        tasks=row['tasks']
        if not isinstance(tasks,list) or not tasks or len(set(tasks))!=len(tasks) or any(t not in known for t in tasks):raise ProjectError('known unique work tasks required for each passage')
        used.update(tasks)
    if used!=set(known):raise ProjectError('all reviewed work tasks need source passages')
    placeholder={t['id'] for t in original['tasks'] if t['kind']=='manual' and t['id'].startswith('interpret-')}
    if not placeholder or any(t['kind']=='manual' and t['id'] not in placeholder for t in original['tasks']):raise ProjectError('only original interpretation scaffold can be replaced')
    old_requirements=[r for r in original['requirements'] if r['task'] in placeholder]
    if {r['passage'] for r in old_requirements}!=technical:raise ProjectError('complete original interpretation coverage required')
    issues=original.get('unresolved_inputs',[])
    if any(set(i['blocks_tasks'])-placeholder or i['kind']!='missing' or not i['id'].startswith('interpretation-') or i['description']!='Source meaning, design inputs and acceptance criteria have not been interpreted.' for i in issues):raise ProjectError('unrelated unresolved issues must not be overwritten')
    result=copy.deepcopy(original)
    result['tasks']=[t for t in result['tasks'] if t['id'] not in placeholder]+[dict(id='work-'+id,kind='manual',description=row['description'],requires_pass=['work-'+d for d in row['requires_pass']]) for id,row in known.items()]
    result['requirements']=[r for r in result['requirements'] if r['task'] not in placeholder]
    for r in old_requirements:
        for task in mapping[r['passage']]['tasks']:
            result['requirements'].append(dict(r,id=r['id']+'-'+task,task='work-'+task,acceptance=known[task]['acceptance']+'; full source quote remains authoritative, acceptance pending'))
    result['unresolved_inputs']=[dict(id='gap-'+id,kind='missing',description=row['blocker'],blocks_tasks=['work-'+id],sources=[dict(passage=p,quote=passages[p]['text']) for p,m in mapping.items() if id in m['tasks']]) for id,row in known.items()]
    result['planning_records']=list(dict.fromkeys(result.get('planning_records',[])+[review.relative_to(root).as_posix()]))
    candidate=root/'work-plan-candidate.json'
    if candidate.exists():raise ProjectError('new candidate path required')
    try:
        candidate.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        validate_plan(candidate)
        if any(digest(Path(p))!=sha for p,sha in before.items()):raise ProjectError('planning source changed during review')
        candidate.replace(plan)
    finally:
        if candidate.exists():candidate.unlink()
    return dict(technical_passages=len(technical),reviewed_work_packages=len(known),original_quotes_preserved=True,design_accepted=False)
