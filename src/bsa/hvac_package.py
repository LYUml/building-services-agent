"""Execute one reviewed HVAC plan through drawing and report preparation.

This orchestration retains unresolved requirements; it never certifies delivery.
"""
import argparse
import html
import json
from pathlib import Path
from .cli import digest
from .workflow import validate_plan,execute,verify
from .workflow_status import diagnose
from .delivery import template


def run(plan,output,*,font,autocad=None,terminal_review=None):
    plan,output,font=map(lambda p:Path(p).resolve(),(plan,output,font))
    validated,inputs=validate_plan(plan)
    protected=set(inputs)|{plan,font}
    review_settings=None;review_pin=None
    if terminal_review is not None:
        terminal_review=Path(terminal_review).resolve();protected.add(terminal_review)
        review_pin=digest(terminal_review)
        review_settings=json.loads(terminal_review.read_text(encoding='utf-8'))
        if set(review_settings)!={'native_task','layers'}:
            raise ValueError('Terminal review settings require only native_task and layers')
        kinds={t['id']:t['kind'] for t in validated['tasks']}
        if kinds.get(review_settings['native_task'])!='duct_sheet_native':
            raise ValueError('Terminal review must select a declared native sheet task')
        layers=review_settings['layers']
        if not isinstance(layers,dict) or set(layers)!={'supply','vav','terminal','flex'} or any(not isinstance(v,str) or not v.strip() for v in layers.values()) or len(set(layers.values()))!=4:
            raise ValueError('Four distinct nonempty review layers required')
    if autocad:protected.add(Path(autocad).resolve())
    if output.exists() or any(output==p or output in p.parents for p in protected):
        raise ValueError('New package directory separate from all inputs required')
    if not font.is_file():raise ValueError('Existing explicit report font required')
    output.mkdir(parents=True)
    workflow=execute(plan,output/'workflow',autocad=autocad)
    diagnosis=diagnose(plan,output/'workflow')
    (output/'diagnosis.json').write_text(json.dumps(diagnosis,indent=2),encoding='utf-8')
    template(plan,output/'workflow',output/'delivery-review.json')
    stages={};errors={}
    if review_settings is not None:
        try:
            from .air_terminal_drawing import from_workflow
            stages['terminal_review']=from_workflow(plan,output/'workflow',review_settings['native_task'],
                output/'terminal-review.json',layers=review_settings['layers'])
        except (ValueError,OSError,KeyError) as exc:errors['terminal_review']=str(exc)
    try:
        from .hvac_report import run as report
        stages['report']=report(output/'workflow',output/'report')
    except (ValueError,OSError,KeyError) as exc:errors['report']=str(exc)
    if 'report' in stages:
        try:
            from .hvac_report_pdf import run as render
            stages['report_pdf']=render(output/'report',output/'report-pdf',font)
        except (ValueError,OSError,KeyError,ImportError) as exc:errors['report_pdf']=str(exc)
    if not verify(output/'workflow')['integrity_pass']:raise ValueError('Workflow changed during packaging')
    if terminal_review is not None and digest(terminal_review)!=review_pin:
        raise ValueError('Terminal review settings changed during packaging')
    pending=[dict(id=name,kind=t['kind'],status=t['status'],scope=t['scope']) for name,t in workflow['tasks'].items() if t['status']!='pass']
    result=dict(plan_sha256=digest(plan),workflow_sha256=digest(output/'workflow/workflow.json'),
                generator_sha256=digest(Path(__file__)),stages=stages,stage_errors=errors,
                unresolved_tasks=pending,status='incomplete' if errors else 'review_required',
                design_accepted=False,scope='Prepared calculation/drawing/report package; actual visual and full requirement acceptance remain separate')
    result['terminal_review_configuration']=None if terminal_review is None else dict(path=str(terminal_review),sha256=review_pin,settings=review_settings)
    links=[('Workflow evidence','workflow/index.html'),('Dependency diagnosis','diagnosis.json'),('Pending delivery review','delivery-review.json')]
    if 'report' in stages:links.append(('Report HTML','report/HVAC System Design.html'))
    if 'report_pdf' in stages:links.append(('Report PDF','report-pdf/HVAC System Design.pdf'))
    if 'terminal_review' in stages:links.append(('Saved terminal connection review','terminal-review.json'))
    for name,t in workflow['tasks'].items():
        if t['kind']=='duct_sheet_native' and t['status']=='pass':
            links.extend([(name+' DWG',f'workflow/{name}/Supply Air Distribution.dwg'),(name+' PDF',f'workflow/{name}/Supply Air Distribution.pdf')])
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>HVAC Project Review</title><style>body{font:16px/1.5 Arial;max-width:1000px;margin:35px auto}td,th{padding:8px;border:1px solid #ccd}table{border-collapse:collapse}li{margin:8px}</style><h1>HVAC Project Review</h1><p>Design study. Full requirement acceptance is pending.</p><ul>'
    page+=''.join('<li><a href="'+html.escape(path,quote=True)+'">'+html.escape(label)+'</a></li>' for label,path in links)+'</ul>'
    page+='<h2>Unresolved execution tasks</h2><table><tr><th>Task</th><th>Status</th><th>Scope</th></tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(t[k]))+'</td>' for k in ('id','status','scope'))+'</tr>' for t in pending)+'</table>'
    if errors:page+='<h2>Preparation and review errors</h2><pre>'+html.escape(json.dumps(errors,indent=2))+'</pre>'
    (output/'index.html').write_text(page+'</html>',encoding='utf-8')
    result['artifact_hashes']={str(p.relative_to(output)):digest(p) for p in output.rglob('*') if p.is_file()}
    (output/'package.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('--out',required=True);p.add_argument('--font',required=True);p.add_argument('--autocad')
    p.add_argument('--terminal-review',help='JSON containing native_task and four explicit layer names')
    a=p.parse_args();r=run(a.plan,a.out,font=a.font,autocad=Path(a.autocad) if a.autocad else None,terminal_review=a.terminal_review)
    print(r['status'],len(r['unresolved_tasks']),'unresolved tasks; design acceptance pending')
    raise SystemExit(2)
