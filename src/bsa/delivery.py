"""Source-bound delivery review records; execution and engineering acceptance stay separate."""
import argparse
from datetime import datetime,timezone
import hashlib
import html
import json
import re
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .workflow import validate_plan,verify,plan_documents


def fingerprint(requirement):
    return hashlib.sha256(json.dumps(requirement,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def context(plan,root):
    plan,root=Path(plan).resolve(),Path(root).resolve()
    source,inputs=validate_plan(plan);inputs.add(plan)
    report=json.loads((root/'workflow.json').read_text(encoding='utf-8-sig'))
    from .requirements_binding import verify_report as verify_requirements
    inputs.update(Path(p) for p in verify_requirements(report,plan))
    from .workflow import three_phase_rule_bindings,three_phase_model_bindings
    if report.get('three_phase_source_bindings',[])!=three_phase_rule_bindings(source['tasks']):raise ProjectError('three-phase source bindings differ from plan')
    if report.get('three_phase_model_bindings',[])!=three_phase_model_bindings(plan.parent,source['tasks']):raise ProjectError('three-phase model bindings differ from plan')
    if report.get('unresolved_inputs',[])!=source.get('unresolved_inputs',[]):
        raise ProjectError('run unresolved input register differs from plan')
    from .workflow_modules import selection_inputs,verify_selection
    selection=report.get('module_selection')
    if selection is not None:
        inputs.update(selection_inputs(source['tasks'],plan.parent,selection))
        verify_selection(source['tasks'],root,selection,plan.parent,report.get('tasks',{}))
    if not isinstance(report,dict) or report.get('inputs')!={str(p):digest(p) for p in inputs}:
        raise ProjectError('run input set/hashes differ from the current source-linked plan')
    tasks={t['id']:t for t in source['tasks']}
    if set(report.get('tasks',{}))!=set(tasks):raise ProjectError('run task set differs from plan')
    for id,task in report['tasks'].items():
        if task.get('kind')!=tasks[id]['kind'] or task.get('status') not in ('pass','fail','pending'):
            raise ProjectError('run task metadata differs from plan or has unknown status')
    from .module_water_rules import verify_workflow
    verify_workflow(source['tasks'],root,plan.parent,report['tasks'])
    from .module_electrical_rules import verify_workflow as verify_electrical_workflow
    verify_electrical_workflow(source['tasks'],root,plan.parent,report['tasks'])
    from .module_electrical_native import verify_workflow as verify_electrical_native_workflow
    verify_electrical_native_workflow(source['tasks'],root,report['tasks'])
    from .spatial_terminal_stubs import verify_workflow as verify_terminal_stub_workflow
    verify_terminal_stub_workflow(source['tasks'],root,plan.parent,report['tasks'])
    from .spatial_terminal_inlets import verify_workflow as verify_terminal_inlet_workflow
    verify_terminal_inlet_workflow(source['tasks'],root,plan.parent,report['tasks'])
    from .spatial_terminal_ifc import verify_workflow as verify_terminal_ifc_workflow
    verify_terminal_ifc_workflow(source['tasks'],root,plan.parent,report['tasks'])
    from .spatial_terminal_coordination import verify_workflow as verify_terminal_coordination_workflow
    verify_terminal_coordination_workflow(source['tasks'],root,plan.parent,report['tasks'])
    from .spatial_terminal_native import verify_workflow as verify_spatial_native_workflow
    verify_spatial_native_workflow(source['tasks'],root,plan.parent,report['tasks'])
    from .spatial_terminal_drawing import verify_workflow as verify_terminal_drawing_workflow
    verify_terminal_drawing_workflow(source['tasks'],root,plan.parent,report['tasks'])
    from .spatial_terminal_performance import verify_workflow as verify_terminal_performance_workflow
    verify_terminal_performance_workflow(source['tasks'],root,plan.parent,report['tasks'])
    from .spatial_air_allocation import verify_workflow as verify_air_allocation_workflow
    verify_air_allocation_workflow(source['tasks'],root,plan.parent,report['tasks'])
    from .spatial_air_balance import verify_workflow as verify_air_balance_workflow
    verify_air_balance_workflow(source['tasks'],root,plan.parent,report['tasks'])
    for name,task in tasks.items():
        if task['kind']=='rectangular_fan_operating_point' and task.get('depends_on') in tasks and tasks[task['depends_on']]['kind']=='module_analysis':
            if (root/name/'fan.json').is_file() or report['tasks'][name]['status']=='pass':
                from .module_fan import verify as verify_module_fan
                fan=verify_module_fan(root/name)
                if report['tasks'][name]['status']!=('pass' if fan['calculated_checks_pass'] else 'fail'):raise ProjectError('Workflow fan status contradicts retained/replayed result')
    recorded=report.get('requirements',[])
    if not isinstance(recorded,list) or len(recorded)!=len(source['requirements']):raise ProjectError('run requirement coverage differs from plan')
    by_id={r['id']:r for r in recorded}
    if len(by_id)!=len(recorded) or set(by_id)!={r['id'] for r in source['requirements']}:raise ProjectError('run requirement identities differ from plan')
    artifacts=report.get('artifact_hashes')
    if not isinstance(artifacts,dict):raise ProjectError('recorded artifact hashes required')
    source_rows={r['id']:r for r in plan_documents(plan.parent,source)['passages']}
    for requirement in source['requirements']:
        row=by_id[requirement['id']]
        if any(row.get(key)!=value for key,value in requirement.items()):raise ProjectError('run requirement text/task differs from source plan')
        if row.get('execution_status')!=report['tasks'][requirement['task']]['status']:raise ProjectError('run execution matrix contradicts task status')
        locator=json.loads(json.dumps({k:v for k,v in source_rows[requirement['passage']].items() if k not in ('id','text')}))
        if row.get('source_locator')!=locator:raise ProjectError('run source locator differs from current brief passage')
        from .workflow import requirement_support
        if row.get('supporting_evidence',{})!=requirement_support(requirement,report['tasks'],artifacts):
            raise ProjectError('run supporting evidence differs from declared tasks')
        expected={name for name in artifacts if name.startswith(requirement['task']+'/')}
        if set(row.get('evidence',[]))!=expected:raise ProjectError('run requirement artifact inventory differs from task evidence')
    return source,report,verify(root)


def template(plan,root,out):
    plan,root,out=Path(plan).resolve(),Path(root).resolve(),Path(out).resolve()
    if out==plan or out.is_relative_to(root):raise ProjectError('store review separately from plan/run artifacts')
    source,_,integrity=context(plan,root)
    if not integrity['integrity_pass']:raise ProjectError('repair or rerun stale evidence before creating a review')
    result=dict(version=1,plan_sha256=digest(plan),workflow_sha256=digest(root/'workflow.json'),requirements=[
        dict(id=r['id'],requirement_sha256=fingerprint(r),status='pending',reviewer='',reviewed_at_utc='',notes='',evidence=[],attachments=[],checks=[])
        for r in source['requirements']])
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as stream:stream.write(json.dumps(result,ensure_ascii=False,indent=2))
    return result


def relative_file(root,name):
    if not isinstance(name,str) or not name or Path(name).is_absolute():raise ProjectError('relative evidence path required')
    path=(root/name).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise ProjectError('evidence path missing or outside run')
    return path


def pointer(value,path):
    if not isinstance(path,str) or not path.startswith('/'):raise ProjectError('explicit JSON pointer required')
    for token in path[1:].split('/'):
        if re.search(r'~(?![01])',token):raise ProjectError('invalid JSON pointer escape')
        token=token.replace('~1','/').replace('~0','~')
        if isinstance(value,list):
            if re.fullmatch(r'0|[1-9][0-9]*',token) is None:raise ProjectError('invalid JSON array pointer')
            value=value[int(token)]
        else:value=value[token]
    return value


def review_agenda(rows,diagnosis):
    """Schedule remaining requirement reviews without changing execution gates."""
    tasks={task['id']:task for task in diagnosis['tasks']}
    groups={}
    for row in rows:
        if row['effective_review_status']=='pass':continue
        task=tasks[row['task']]
        group=groups.setdefault(row['task'],dict(task=row['task'],execution_status=task['status'],
            blocked_by=task['blocked_by'],input_blockers=task['input_blockers'],
            next_action=task['next_action'],requirements=[]))
        group['requirements'].append(row)
    return dict(scoped_reviewed_requirement_ids=[row['id'] for row in rows if row['effective_review_status']=='pass'],
        remaining_requirement_count=sum(len(group['requirements']) for group in groups.values()),
        remaining_tasks=list(groups.values()),execution_gates_unchanged=True,design_accepted=False,
        scope='Remaining source requirement reviews only; scoped passes do not authorize dependent execution or establish whole-design acceptance')


def assess(plan,root,review_path):
    plan,root,review_path=Path(plan).resolve(),Path(root).resolve(),Path(review_path).resolve()
    before={str(p):digest(p) for p in (plan,root/'workflow.json',review_path)}
    result=dict(design_accepted=False,review_checks_pass=False,source_integrity_pass=False,requirements=[],issues=[],
                engineering_actions=[],review_agenda=None,engineering_acceptance='not_established',
                scope='Source/byte consistency, recorded reviewer assertions and optional adapter-reported Boolean facts; not reviewer authentication, semantic completeness or engineering certification')
    context_loaded=False;attachments_seen={}
    try:
        source,report,integrity=context(plan,root);result['source_integrity_pass']=integrity['integrity_pass']
        context_loaded=True
        recorded_requirements={r['id']:r for r in report['requirements']}
        result['issues'].extend(integrity['issues'])
        from .workflow_status import diagnose
        diagnosis=diagnose(plan,root)
        dependency_rows = {r['id']: r for r in diagnosis['tasks']}
        result['engineering_actions']=diagnosis.get('engineering_actions',[])
        review=json.loads(review_path.read_text(encoding='utf-8-sig'))
        if not isinstance(review,dict) or set(review)!={'version','plan_sha256','workflow_sha256','requirements'} or type(review['version']) is not int or review['version']!=1:
            raise ProjectError('review version 1 and exact source/report hashes required')
        if review['plan_sha256']!=digest(plan) or review['workflow_sha256']!=digest(root/'workflow.json'):
            raise ProjectError('review is stale for this exact source plan or run report')
        rows=review['requirements']
        if not isinstance(rows,list) or len(rows)!=len(source['requirements']):raise ProjectError('review must cover every source requirement exactly once')
        by_id={r['id']:r for r in rows}
        if len(by_id)!=len(rows) or set(by_id)!={r['id'] for r in source['requirements']}:raise ProjectError('missing/duplicate/unknown review requirement')
        for requirement in source['requirements']:
            row=by_id[requirement['id']];issues=[];facts=[]
            fields={'id','requirement_sha256','status','reviewer','reviewed_at_utc','notes','evidence','attachments','checks'}
            if set(row)!=fields or row['requirement_sha256']!=fingerprint(requirement):raise ProjectError('review requirement text binding changed')
            status=row['status']
            if status not in ('pass','fail','pending'):raise ProjectError('review status must be pass/fail/pending')
            for key in ('reviewer','reviewed_at_utc','notes'):
                if not isinstance(row[key],str):raise ProjectError('review metadata must be text')
            if status!='pending':
                if not row['reviewer'].strip() or not row['notes'].strip():raise ProjectError('nonpending review requires reviewer and substantive observations')
                stamp=datetime.fromisoformat(row['reviewed_at_utc'].replace('Z','+00:00'))
                if stamp.tzinfo is None or stamp.utcoffset()!=timezone.utc.utcoffset(stamp):raise ProjectError('review timestamp must be UTC')
                if not row['evidence']:raise ProjectError('nonpending review requires cited original artifacts')
            if not all(isinstance(row[k],list) for k in ('evidence','attachments','checks')):raise ProjectError('evidence/attachments/checks must be lists')
            cited=set()
            for evidence in row['evidence']:
                if not isinstance(evidence,dict) or set(evidence)!={'artifact','sha256'}:raise ProjectError('artifact path/hash required')
                name=evidence['artifact'];path=relative_file(root,name)
                if name not in report['artifact_hashes'] or evidence['sha256']!=report['artifact_hashes'][name] or digest(path)!=evidence['sha256']:
                    issues.append('cited artifact hash mismatch: '+name)
                cited.add(name)
            for attachment in row['attachments']:
                if not isinstance(attachment,dict) or set(attachment)!={'path','sha256','source_artifact','source_sha256'}:raise ProjectError('supplemental evidence requires attachment/source hashes')
                path=relative_file(root,attachment['path']);name=attachment['source_artifact']
                attachments_seen[path]=attachment['sha256']
                if name not in cited or report['artifact_hashes'].get(name)!=attachment['source_sha256'] or digest(path)!=attachment['sha256']:
                    issues.append('attachment/source binding mismatch: '+attachment['path'])
            for check in row['checks']:
                if not isinstance(check,dict) or set(check)!={'artifact','pointer','expected','basis'} or type(check['expected']) is not bool or not isinstance(check['basis'],str) or not check['basis'].strip():
                    raise ProjectError('Boolean fact check requires artifact/pointer/expected/basis')
                if check['artifact'] not in cited:raise ProjectError('fact check must cite its source artifact')
                value=pointer(json.loads(relative_file(root,check['artifact']).read_text(encoding='utf-8-sig')),check['pointer'])
                passed=type(value) is bool and value is check['expected']
                facts.append(dict(**check,actual=value,pass_check=passed))
                if not passed:issues.append('adapter Boolean fact failed: '+check['artifact']+check['pointer'])
            task=report['tasks'][requirement['task']]
            if not integrity['integrity_pass']:issues.append('run source/artifact integrity failed')
            if task['status']=='fail':issues.append('upstream task failed; review cannot clear it')
            effective='fail' if issues or status=='fail' else status
            blocked_by = dependency_rows[requirement['task']]['blocked_by']
            input_blockers=dependency_rows[requirement['task']]['input_blockers']
            if effective=='pass' and (blocked_by or input_blockers):effective='pending'
            if effective=='pass' and task['status']=='pending' and task['kind']!='manual':effective='pending'
            result['requirements'].append(dict(id=requirement['id'],task=requirement['task'],quote=requirement['quote'],acceptance=requirement['acceptance'],
                passage=requirement['passage'],source_locator=recorded_requirements[requirement['id']]['source_locator'],
                execution_status=task['status'],recorded_review_status=status,effective_review_status=effective,blocked_by=blocked_by,
                input_blockers=input_blockers,
                engineering_review_requests=dependency_rows[requirement['task']].get('module_state',{}).get('engineering_review_requests',[]),
                reviewer=row['reviewer'],reviewed_at_utc=row['reviewed_at_utc'],notes=row['notes'],evidence=row['evidence'],attachments=row['attachments'],facts=facts,issues=issues))
        result['review_checks_pass']=integrity['integrity_pass'] and all(r['effective_review_status']=='pass' for r in result['requirements'])
    except (ProjectError,ValueError,TypeError,KeyError,IndexError,AttributeError,OSError) as exc:
        result['issues'].append(str(exc));result['review_checks_pass']=False
    if context_loaded:
        try:
            end=verify(root)
            if not end['integrity_pass']:
                result['issues'].extend(end['issues']);result['source_integrity_pass']=False;result['review_checks_pass']=False
        except (ValueError,TypeError,KeyError,AttributeError,OSError) as exc:
            result['issues'].append('run integrity changed during review: '+str(exc));result['source_integrity_pass']=False;result['review_checks_pass']=False
    if any(not p.is_file() or digest(p)!=sha for p,sha in attachments_seen.items()):
        result['issues'].append('supplemental evidence changed during review');result['review_checks_pass']=False
    result['inputs']=before
    result['inputs_unchanged']=all(Path(p).is_file() and digest(Path(p))==sha for p,sha in before.items())
    if not result['inputs_unchanged']:result['issues'].append('source plan/report/review changed during audit');result['review_checks_pass']=False
    if result['source_integrity_pass'] and result['inputs_unchanged'] and not result['issues']:
        result['review_agenda']=review_agenda(result['requirements'],diagnosis)
    result['status']='failed' if result['issues'] or any(r['effective_review_status']=='fail' for r in result['requirements']) else 'review_complete' if result['review_checks_pass'] else 'needs_review'
    return result


def render(result):
    """Keep long source quotes and review distinctions readable at narrow widths."""
    def esc(value): return html.escape(str(value))
    def structured(value): return esc(json.dumps(value,ensure_ascii=False,indent=2))
    counts={state:sum(r['effective_review_status']==state for r in result['requirements']) for state in ('pass','fail','pending')}
    cards=[]
    for row in result['requirements']:
        fields=[('Task',row['task']),('Source passage',row['passage']),
            ('Execution',row['execution_status']),('Recorded review',row['recorded_review_status']),
            ('Effective review',row['effective_review_status'])]
        metadata='<dl>'+''.join('<div><dt>'+esc(k)+'</dt><dd>'+esc(v)+'</dd></div>' for k,v in fields)+'</dl>'
        cards.append('<article><h2>'+esc(row['id'])+' <span class="status '+esc(row['effective_review_status'])+'">'+esc(row['effective_review_status'])+'</span></h2>'+metadata+
            '<h3>Acceptance target</h3><p>'+esc(row['acceptance'])+'</p><h3>Review observations</h3><p class="notes">'+esc(row['notes'] or 'No review observations recorded.')+'</p>'+
            '<details><summary>Original source and review evidence</summary><h3>Source locator</h3><pre>'+structured(row['source_locator'])+'</pre><h3>Original quote</h3><blockquote>'+esc(row['quote'])+'</blockquote>'+
            '<h3>Reviewer assertion</h3><p>'+esc(row['reviewer'] or 'Unrecorded')+' · '+esc(row['reviewed_at_utc'] or 'Unrecorded')+'</p>'+
            ''.join('<h3>'+esc(label)+'</h3><pre>'+structured(row.get(key,[]))+'</pre>' for label,key in [('Blocking tasks','blocked_by'),('Input blockers','input_blockers'),('Engineering review requests','engineering_review_requests'),('Cited artifacts','evidence'),('Supplemental attachments','attachments'),('Reported Boolean facts','facts'),('Review issues','issues')])+'</details></article>')
    def request_title(request):
        identity=' / '.join(str(request[k]) for k in ('terminal','condition') if k in request)
        return (identity+': ' if identity else '')+request['code'].replace('_',' ')
    engineering=[]
    for action in result.get('engineering_actions',[]):
        requests=action['data_requests']
        engineering.append('<section class="notice"><h3>'+esc(action['task'])+' — engineering review pending</h3><p>Requirements: '+esc(', '.join(action['requirement_ids']))+'</p><ul>'+''.join('<li><strong>'+esc(request_title(request))+'</strong><p>'+esc(request['requested'])+'</p><details><summary>Retained engineering evidence</summary><pre>'+structured(request)+'</pre></details></li>' for request in requests)+'</ul><p>Source artifact: '+esc(action['evidence'])+'</p><details><summary>Source SHA256</summary><pre>'+esc(action['evidence_sha256'])+'</pre></details></section>')
    engineering_section='<section><h2>Engineering review requests</h2><p>Engineering acceptance: not established. '+str(sum(len(a['data_requests']) for a in result.get('engineering_actions',[])))+' retained requests. An empty queue does not establish complete engineering coverage.</p>'+''.join(engineering)+'</section>'
    agenda=result.get('review_agenda')
    if agenda is not None:
        engineering_section+='<section><h2>Remaining requirement reviews</h2><p>'+str(agenda['remaining_requirement_count'])+' requirements remain. Execution prerequisites are unchanged.</p><ul>'+''.join('<li><strong>'+esc(group['task'])+'</strong> — '+esc(', '.join(row['id'] for row in group['requirements']))+'<p>'+esc(group['next_action'])+'</p></li>' for group in agenda['remaining_tasks'])+'</ul></section>'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Delivery review evidence</title><style>body{font:16px/1.5 Arial,sans-serif;color:#20343c;max-width:1050px;margin:32px auto;padding:0 18px;overflow-wrap:anywhere}h1{line-height:1.2}h2{font-size:21px}h3{font-size:16px;margin-bottom:6px}.notice{background:#fff1d6;border-left:5px solid #a96a10;padding:16px}.counts{display:flex;gap:16px;flex-wrap:wrap}.status{font-size:14px;padding:3px 8px;border-radius:4px;background:#edf0f2}.pass{background:#e1f0e7}.fail{background:#f9e3e0}.pending{background:#fff1d6}article{border:1px solid #cad3d7;border-radius:6px;margin:22px 0;padding:18px}dl{display:flex;flex-wrap:wrap;gap:12px 30px}dl div{min-width:140px}dt{font-size:13px;color:#52656c}dd{margin:0}p,blockquote,pre{white-space:pre-wrap}blockquote{margin:12px 0;padding:12px 16px;background:#f4f6f7}pre{font:13px/1.5 Consolas,monospace;overflow-wrap:anywhere}summary{cursor:pointer;color:#075665}details{border-top:1px solid #dce2e5;padding-top:12px}a{color:#075665}</style><h1>Delivery review evidence</h1><p class="notice"><strong>'+esc(result['status'])+'</strong>. Design accepted: false. Scoped review passes do not establish whole-design acceptance.</p><p>'+esc(result['scope'])+'</p><div class="counts">'+''.join('<p class="status '+state+'">'+esc(state)+': <strong>'+str(count)+'</strong></p>' for state,count in counts.items())+'</div><p>Execution, recorded review and effective review are separate. Expand each requirement to inspect the original quote, source locator, blockers and evidence. <a href="audit.json">Complete audit JSON</a>.</p>'+(''.join('<p class="notice">'+esc(issue)+'</p>' for issue in result['issues']))+engineering_section+''.join(cards)+'</html>'


def run(plan,root,review,out):
    plan,root,review,out=[Path(p).resolve() for p in (plan,root,review,out)]
    if out.is_relative_to(root) or any(out==p or out in p.parents for p in (plan,review,root/'workflow.json')):
        raise ProjectError('store audit separately; output must not contain source/run/review')
    result=assess(plan,root,review);out.mkdir(parents=True,exist_ok=False)
    (out/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'report.html').write_text(render(result),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('template','audit'):
        command=sub.add_parser(name);command.add_argument('plan',type=Path);command.add_argument('run',type=Path);command.add_argument('--out',type=Path,required=True)
        if name=='audit':command.add_argument('--review',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='template':template(args.plan,args.run,args.out);print('Pending review template created; no requirement automatically accepted');return 0
    result=run(args.plan,args.run,args.review,args.out)
    print(json.dumps({k:result[k] for k in ('status','review_checks_pass','design_accepted')},indent=2))
    return 0 if result['review_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
