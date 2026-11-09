"""Review declared jurisdiction scope against available packs and scheduled tasks."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError


def run(catalog,scope,out,plan=None):
    catalog,scope,out=map(lambda p:Path(p).resolve(),(catalog,scope,out))
    snapshots={}
    def read(path):
        snapshots[str(path)]=digest(path)
        return json.loads(path.read_text(encoding='utf-8-sig'))
    def local(value):
        if not isinstance(value,str) or Path(value).is_absolute():raise ProjectError('relative catalog resource required')
        path=(catalog.parent/value).resolve()
        if not path.is_relative_to(catalog.parent):raise ProjectError('catalog resource escapes root')
        return path
    c=read(catalog);s=read(scope)
    if c.get('schema_version')!=1 or s.get('jurisdiction')!=c.get('jurisdiction') or s.get('catalog')!=c.get('id'):
        raise ProjectError('explicit matching coverage catalog and jurisdiction required')
    topics=c.get('topics',[]);ids=[r['id'] for r in topics]
    if not ids or len(ids)!=len(set(ids)) or set(s.get('topics',{}))!=set(ids):
        raise ProjectError('exact nonempty topic decision coverage required')
    inventory=read(local(c['source_inventory']))
    if inventory['jurisdiction']!=c['jurisdiction']:raise ProjectError('inventory jurisdiction mismatch')
    tasks=[];plan_root=None
    if plan:
        from .workflow import validate_plan
        plan=Path(plan).resolve();data,inputs=validate_plan(plan)
        read(plan);snapshots.update({str(p):digest(p) for p in inputs})
        tasks=data['tasks'];plan_root=plan.parent
    rows=[]
    for topic in topics:
        decision=s['topics'][topic['id']]
        state=decision.get('decision')
        if state not in ('required','excluded','unresolved') or not isinstance(decision.get('source'),str) or not decision['source'].strip():
            raise ProjectError('sourced required/excluded/unresolved topic decision required')
        if state=='excluded' and (not isinstance(decision.get('reason'),str) or not decision['reason'].strip()):
            raise ProjectError('excluded topic needs explicit rationale')
        source_id=topic.get('source_id')
        if source_id is not None and source_id not in inventory['sources']:raise ProjectError('unknown inventory source')
        available=[]
        for module in topic['modules']:
            path=local(module['pack']);pack=read(path)
            if pack['id']!=module['pack_id'] or pack['jurisdiction']!=c['jurisdiction'] or set(module['rules'])!={r['id'] for r in pack['rules']}:
                raise ProjectError('coverage module identity or rule list differs from pack')
            matching=[]
            for task in tasks:
                if task['kind'] in ('three_phase_regulations','plumbing_pump_set','plumbing_pump_regulations','ifc_circulation_checks','epanet_pipe_regulations','regulations','electrical_regulations','lighting_regulations','hvac_regulations','water_pipe_regulations','regulated_water_model'):
                    consumed=(plan_root/task['pack']).resolve()
                    if digest(consumed)==snapshots[str(path)]:matching.append(task['id'])
            available.append(dict(pack=pack['id'],sha256=snapshots[str(path)],rule_ids=module['rules'],
                                  scheduled_tasks=matching,execution_status='not_assessed',
                                  pack_coverage=pack['coverage']))
        gaps=[]
        if state=='unresolved':gaps.append('applicability_unresolved')
        if state=='required':
            if not available:gaps.append('no_implemented_module')
            if any(not m['scheduled_tasks'] for m in available):gaps.append('implemented_module_not_scheduled')
            if any(m['pack_coverage'].get('complete') is not True for m in available):gaps.append('partial_rule_coverage')
        rows.append(dict(id=topic['id'],title=topic['title'],decision=decision,
                         official_source=inventory['sources'].get(source_id),modules=available,gaps=gaps))
    if any(not Path(p).is_file() or digest(Path(p))!=h for p,h in snapshots.items()):raise ProjectError('coverage inputs changed')
    if any(out==Path(p) or out in Path(p).parents for p in snapshots):raise ProjectError('output must not contain inputs')
    result=dict(catalog=c['id'],jurisdiction=c['jurisdiction'],inputs=snapshots,inputs_unchanged=True,topics=rows,
                has_declared_gaps=any(r['gaps'] for r in rows),coverage_complete=False,
                regulatory_compliance='not_established',design_accepted=False,
                scope='Declared planning scope and scheduled pack bytes only; no check execution, legal applicability determination or exhaustive statutory coverage')
    out.mkdir(parents=True,exist_ok=False)
    (out/'coverage.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# Regulatory planning coverage','',result['scope'],'','| Topic | Decision | Planning gaps | Scheduled tasks |','|---|---|---|---|']
    for r in rows:
        cells=[r['title'],r['decision']['decision'],', '.join(r['gaps']) or 'None identified within declared scope',', '.join(t for m in r['modules'] for t in m['scheduled_tasks']) or 'None']
        lines.append('| '+' | '.join(v.replace('|','/').replace('\n',' ') for v in cells)+' |')
    lines+=['','Coverage is not established as complete. Exclusions are sourced assertions awaiting project review.']
    (out/'coverage.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','scope','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--plan',type=Path);a=p.parse_args()
    r=run(a.catalog,a.scope,a.out,a.plan)
    print(json.dumps({'has_declared_gaps':r['has_declared_gaps'],'coverage_complete':False}))
    return 2 if r['has_declared_gaps'] else 0


if __name__=='__main__':raise SystemExit(main())
