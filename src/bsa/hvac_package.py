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


def review_actions(stages,errors):
    """Collect post-run engineering work without clearing workflow/manual gates."""
    actions=[dict(stage=name,code='stage_execution_error',detail=message,
                  action='Resolve the stage error and rerun against reviewed inputs.')
             for name,message in sorted(errors.items())]
    if 'adpi_review' in stages:
        review=stages['adpi_review']
        actions.extend(dict(item,stage='adpi_review') for item in review['data_requests'])
        failed=[row for row in review['cases'] if row['status']=='fail']
        if failed:
            actions.append(dict(stage='adpi_review',code='terminal_ratio_screen_failed',
                cases=[{key:row[key] for key in ('terminal','direction','case')} for row in failed],
                action='Review catalogue coverage and terminal design for the listed cases; rerun both operating conditions.'))
    return actions


def run(plan,output,*,font,autocad=None,terminal_review=None,adpi_settings=None,plan_clearance=None,junction_review_native_task=None,system_paths_native_task=None,terminal_performance=None,requirements_result=None,module_providers=None,disabled_module_providers=()):
    plan,output,font=map(lambda p:Path(p).resolve(),(plan,output,font))
    validated,inputs=validate_plan(plan)
    if junction_review_native_task is not None and (not isinstance(junction_review_native_task,str) or not any(t['id']==junction_review_native_task and t['kind']=='duct_sheet_native' for t in validated['tasks'])):
        raise ValueError('Junction review must select a declared native sheet task')
    if system_paths_native_task is not None and (not isinstance(system_paths_native_task,str) or not any(t['id']==system_paths_native_task and t['kind']=='duct_sheet_native' for t in validated['tasks'])):
        raise ValueError('System path review must select a declared native sheet task')
    from .workflow_modules import host_selection
    module_selection=host_selection(validated['tasks'],module_providers,disabled_module_providers)
    protected=set(inputs)|{plan,font}
    if requirements_result is not None:
        from .requirements_binding import bind
        requirements_result=Path(requirements_result).resolve()
        _, requirement_pins=bind(plan,requirements_result)
        protected.update(Path(p) for p in requirement_pins)
    performance_pins={};performance_task=None
    if terminal_performance is not None:
        from .terminal_performance import settings_inputs as performance_inputs
        terminal_performance=Path(terminal_performance).resolve()
        _,performance_pins=performance_inputs(terminal_performance)
        protected.update(Path(p) for p in performance_pins)
        matches=[t['id'] for t in validated['tasks'] if t['kind']=='terminal_throw']
        if len(matches)!=1:raise ValueError('One declared terminal lookup required for performance stage')
        performance_task=matches[0]
    clearance_pin=None
    if plan_clearance is not None:
        plan_clearance=Path(plan_clearance).resolve();protected.add(plan_clearance)
        clearance_pin=digest(plan_clearance)
    adpi_pins={}
    if adpi_settings is not None:
        from .adpi_review import settings_inputs
        adpi_settings=Path(adpi_settings).resolve()
        _,adpi_pins=settings_inputs(adpi_settings)
        protected.update(Path(p) for p in adpi_pins)
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
    workflow=execute(plan,output/'workflow',autocad=autocad,**({'requirements_result':requirements_result} if requirements_result is not None else {}),**(dict(module_providers=module_providers,disabled_module_providers=disabled_module_providers) if module_providers or disabled_module_providers else {}))
    diagnosis=diagnose(plan,output/'workflow')
    (output/'diagnosis.json').write_text(json.dumps(diagnosis,indent=2),encoding='utf-8')
    template(plan,output/'workflow',output/'delivery-review.json')
    stages={};errors={}
    if terminal_performance is not None:
        try:
            from .terminal_performance import run as performance
            stages['terminal_performance']=performance(plan,output/'workflow',performance_task,terminal_performance,output/'terminal-performance')
        except (ValueError,OSError,KeyError,ImportError) as exc:errors['terminal_performance']=str(exc)
    if system_paths_native_task is not None:
        try:
            from .duct_system_paths import run as system_paths
            stages['system_paths']=system_paths(plan,output/'workflow',system_paths_native_task,output/'system-paths')
        except (ValueError,OSError,KeyError,ImportError) as exc:errors['system_paths']=str(exc)
    if junction_review_native_task is not None:
        try:
            from .duct_junction_review import from_workflow as junction_review
            stages['junction_review']=junction_review(plan,output/'workflow',junction_review_native_task,output/'junction-review.json')
        except (ValueError,OSError,KeyError) as exc:errors['junction_review']=str(exc)
    if plan_clearance is not None:
        try:
            from .duct_plan_clearance import from_workflow as clearance_review
            stages['plan_clearance']=clearance_review(plan,output/'workflow',plan_clearance,output/'plan-clearance.json')
        except (ValueError,OSError,KeyError) as exc:errors['plan_clearance']=str(exc)
    if adpi_settings is not None:
        try:
            from .adpi_review import run as adpi_review
            stages['adpi_review']=adpi_review(output/'workflow',adpi_settings,output/'adpi-review.json')
        except (ValueError,OSError,KeyError) as exc:errors['adpi_review']=str(exc)
    if review_settings is not None:
        try:
            from .air_terminal_drawing import from_workflow
            stages['terminal_review']=from_workflow(plan,output/'workflow',review_settings['native_task'],
                output/'terminal-review.json',layers=review_settings['layers'])
        except (ValueError,OSError,KeyError) as exc:errors['terminal_review']=str(exc)
    try:
        from .hvac_report import run as report
        stages['report']=report(output/'workflow',output/'report',
            terminal_review=output/'terminal-review.json' if 'terminal_review' in stages else None,
            adpi_review=output/'adpi-review.json' if 'adpi_review' in stages else None)
    except (ValueError,OSError,KeyError) as exc:errors['report']=str(exc)
    if 'report' in stages:
        try:
            from .hvac_report_pdf import run as render
            stages['report_pdf']=render(output/'report',output/'report-pdf',font)
        except (ValueError,OSError,KeyError,ImportError) as exc:errors['report_pdf']=str(exc)
    if not verify(output/'workflow')['integrity_pass']:raise ValueError('Workflow changed during packaging')
    if 'system_paths' in stages and any(digest(Path(p))!=sha for p,sha in stages['system_paths']['inputs'].items()):
        raise ValueError('System path source or method changed during packaging')
    if any(digest(Path(p))!=sha for p,sha in adpi_pins.items()):raise ValueError('ADPI settings/source changed during packaging')
    if any(digest(Path(p))!=sha for p,sha in performance_pins.items()):raise ValueError('Terminal performance settings/source changed during packaging')
    if 'terminal_performance' in stages and any(digest(Path(p))!=sha for p,sha in stages['terminal_performance']['inputs'].items()):
        raise ValueError('Terminal performance source or method changed during packaging')
    if terminal_review is not None and digest(terminal_review)!=review_pin:
        raise ValueError('Terminal review settings changed during packaging')
    if plan_clearance is not None and digest(plan_clearance)!=clearance_pin:
        raise ValueError('Plan clearance settings changed during packaging')
    pending=[dict(id=name,kind=t['kind'],status=t['status'],scope=t['scope']) for name,t in workflow['tasks'].items() if t['status']!='pass']
    result=dict(plan_sha256=digest(plan),workflow_sha256=digest(output/'workflow/workflow.json'),
                generator_sha256=digest(Path(__file__)),stages=stages,stage_errors=errors,
                unresolved_tasks=pending,status='incomplete' if errors else 'review_required',
                design_accepted=False,scope='Prepared calculation/drawing/report package; actual visual and full requirement acceptance remain separate')
    result['module_selection']=module_selection
    result['review_actions']=review_actions(stages,errors)
    result['terminal_review_configuration']=None if terminal_review is None else dict(path=str(terminal_review),sha256=review_pin,settings=review_settings)
    result['adpi_configuration_inputs']=adpi_pins
    result['terminal_performance_configuration_inputs']=performance_pins
    result['junction_review_native_task']=junction_review_native_task
    result['system_paths_native_task']=system_paths_native_task
    result['plan_clearance_configuration']=None if plan_clearance is None else dict(path=str(plan_clearance),sha256=clearance_pin)
    links=[('Workflow evidence','workflow/index.html'),('Dependency diagnosis','diagnosis.json'),('Pending delivery review','delivery-review.json')]
    if 'report' in stages:links.append(('Report HTML','report/HVAC System Design.html'))
    if 'report_pdf' in stages:links.append(('Report PDF','report-pdf/HVAC System Design.pdf'))
    if 'terminal_review' in stages:links.append(('Saved terminal connection review','terminal-review.json'))
    if 'adpi_review' in stages:links.append(('ADPI applicability and ratio screening','adpi-review.json'))
    if 'plan_clearance' in stages:links.append(('Nominal-width planar obstacle review','plan-clearance.json'))
    if 'junction_review' in stages:links.append(('Source-bound connection requirements','junction-review.json'))
    if 'system_paths' in stages:links.append(('Whole source-tree nominal centreline study','system-paths/index.html'))
    if 'terminal_performance' in stages:links.append(('Diffuser catalogue operating pressures and NC references','terminal-performance/index.html'))
    for name,t in workflow['tasks'].items():
        if t['kind']=='duct_sheet_native' and t['status']=='pass':
            links.extend([(name+' DWG',f'workflow/{name}/Supply Air Distribution.dwg'),(name+' PDF',f'workflow/{name}/Supply Air Distribution.pdf')])
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>HVAC Project Review</title><style>body{font:16px/1.5 Arial;max-width:1000px;margin:35px auto}td,th{padding:8px;border:1px solid #ccd}table{border-collapse:collapse}li{margin:8px}</style><h1>HVAC Project Review</h1><p>Design study. Full requirement acceptance is pending.</p><ul>'
    page+=''.join('<li><a href="'+html.escape(path,quote=True)+'">'+html.escape(label)+'</a></li>' for label,path in links)+'</ul>'
    page+='<h2>Post-run review actions</h2><p>These supplement unresolved workflow tasks and the full requirement review.</p><ul>'
    page+=''.join('<li>'+html.escape(item['stage']+' / '+item['code']+': '+item['action'])+'</li>' for item in result['review_actions'])+'</ul>'
    if 'adpi_review' in stages:
        review=stages['adpi_review']
        page+='<h2>ADPI scope</h2><p>Applicability: '+html.escape(review['applicability'])+'. Full ADPI acceptance is not established.</p><p>Missing facts: '+html.escape(', '.join(review['missing_facts']))+'</p>'
        page+='<ul>'+''.join('<li>'+html.escape(item['code']+': '+item['action'])+'</li>' for item in review['data_requests'])+'</ul>'
    if 'plan_clearance' in stages:
        review=stages['plan_clearance']
        page+='<h2>Nominal-width planar review</h2><p>Tested planar target met: '+str(review['planar_target_met'])+'. Physical/three-dimensional clearance acceptance is pending.</p><p>Unresolved coverage: '+html.escape('; '.join(review['coverage']['unresolved']))+'</p>'
    if 'junction_review' in stages:
        review=stages['junction_review']
        page+='<h2>Connection requirements</h2><p>Plan centreline and nominal sizes only. Physical fittings and engineering acceptance remain pending.</p><table><tr><th>Requirement</th><th>Nodes</th></tr>'
        page+=''.join('<tr><td>'+html.escape(kind.replace('_',' '))+'</td><td>'+str(count)+'</td></tr>' for kind,count in sorted(review['counts'].items()))+'</table>'
        page+='<p>Missing design inputs: '+html.escape('; '.join(review['missing_design_inputs']))+'</p>'
    if 'system_paths' in stages:
        review=stages['system_paths']
        page+='<h2>Whole original supply tree</h2><p>'+str(review['section_count'])+' source sections and '+str(review['outlet_path_count'])+' original outlet paths checked. Nominal untrimmed centreline friction only;physical straight lengths,fitting/terminal/equipment losses,full pressure and fan duty remain pending. Downstream routes are not inferred.</p>'
    page+='<h2>Unresolved execution tasks</h2><table><tr><th>Task</th><th>Status</th><th>Scope</th></tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(t[k]))+'</td>' for k in ('id','status','scope'))+'</tr>' for t in pending)+'</table>'
    if errors:page+='<h2>Preparation and review errors</h2><pre>'+html.escape(json.dumps(errors,indent=2))+'</pre>'
    (output/'index.html').write_text(page+'</html>',encoding='utf-8')
    result['artifact_hashes']={str(p.relative_to(output)):digest(p) for p in output.rglob('*') if p.is_file()}
    (output/'package.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('--out',required=True);p.add_argument('--font',required=True);p.add_argument('--autocad')
    p.add_argument('--module-provider',action='append',default=[],help='Trusted TASK=PROVIDER host selection')
    p.add_argument('--disable-module-provider',action='append',default=[])
    from .workflow_modules import parse_provider_options
    p.add_argument('--requirements-result',help='Verified requirements inventory for the exact plan')
    p.add_argument('--terminal-review',help='JSON containing native_task and four explicit layer names')
    p.add_argument('--adpi-settings',help='Source-pinned criterion and applicability settings')
    p.add_argument('--plan-clearance',help='Inherited native-sheet obstacle/coverage settings')
    p.add_argument('--junction-review-native-task',help='Native sheet task whose exact sizing/tree ancestry supplies connection requirements')
    p.add_argument('--system-paths-native-task',help='Native sheet task whose completed source tree supplies nominal centreline path studies')
    p.add_argument('--terminal-performance',help='Source-pinned diffuser pressure/NC performance settings')
    a=p.parse_args();r=run(a.plan,a.out,font=a.font,autocad=Path(a.autocad) if a.autocad else None,terminal_review=a.terminal_review,adpi_settings=a.adpi_settings,plan_clearance=a.plan_clearance,junction_review_native_task=a.junction_review_native_task,system_paths_native_task=a.system_paths_native_task,terminal_performance=a.terminal_performance,requirements_result=a.requirements_result,module_providers=parse_provider_options(a.module_provider),disabled_module_providers=a.disable_module_provider)
    print(r['status'],len(r['unresolved_tasks']),'unresolved tasks; design acceptance pending')
    raise SystemExit(2)
