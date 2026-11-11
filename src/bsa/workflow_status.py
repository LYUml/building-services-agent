"""Source-bound task dependency diagnosis for the host agent; never resumes engines."""
import argparse
import json
from pathlib import Path

from .cli import digest
from .delivery import context
from .engine import ProjectError


def fitting_data_recovery(run, report, task_id):
    """Read retained requests,without inventing a repair or a physical cause."""
    relative = task_id+'/data-requests.json'
    if relative not in report['artifact_hashes']: return {}
    path = run/relative
    if digest(path) != report['artifact_hashes'][relative]: raise ProjectError('Fitting data requests changed')
    data = json.loads(path.read_text(encoding='utf-8'))
    if any(not Path(p).is_file() or digest(Path(p)) != sha for p, sha in data['inputs'].items()):
        raise ProjectError('Fitting request source or generator changed; execute a fresh study')
    analysis = run/task_id/'analysis/analysis.json'
    if digest(analysis) != data['analysis_sha256']: raise ProjectError('Fitting request analysis changed')
    context = data['upstream_assignment_context']
    for p, sha in ((Path(context['plan']), context['plan_sha256']), (Path(context['workflow'])/'workflow.json', context['workflow_sha256'])):
        if not p.is_file() or digest(p) != sha: raise ProjectError('Original assignment context changed')
    return dict(data_requests=data['data_requests'], upstream_assignment_context=context,
        scope='Exact saved fitting data and review requests only; original requirement context is preserved without inferring cross-plan causal dependencies or selecting new products/geometry.')


def water_runtime_failures(run, report, task_id):
    """Expose explicit, hash-verified water worker policy evidence, not inferred causes."""
    failures=[]
    artifacts=report['artifact_hashes']
    for relative in sorted(artifacts):
        if not relative.startswith(task_id+'/') or Path(relative).name!='water.json':continue
        data=json.loads((run/relative).read_text(encoding='utf-8'))
        failure=data.get('engine_failure')
        if not isinstance(failure,dict) or failure.get('kind')!='application_control_block':continue
        if data.get('calculated_checks_pass') is not False or not data.get('engine_error'):
            raise ProjectError('inconsistent water runtime failure evidence')
        log=(Path(relative).parent/'worker.log').as_posix()
        if failure.get('evidence')!='worker.log' or log not in artifacts:
            raise ProjectError('water runtime failure lacks recorded worker log')
        if 'application control policy' not in (run/log).read_text(encoding='utf-8',errors='replace').lower():
            raise ProjectError('water policy failure classification differs from worker log')
        failures.append(dict(kind='application_control_block',report=relative,
                             report_sha256=artifacts[relative],evidence=log,evidence_sha256=artifacts[log]))
    return failures


def annual_runtime_failures(run,report,task_id):
    failures=[]
    for relative,sha in report['artifact_hashes'].items():
        if not relative.startswith(task_id+'/') or Path(relative).name!='runtime-failure.json':continue
        data=json.loads((run/relative).read_text(encoding='utf-8'))
        kind=data.get('kind');log=(Path(relative).parent/'runtime-import.log').as_posix()
        if kind not in ('application_control_block','dependency_import_error') or data.get('stage')!='openstudio_import' or data.get('simulation_executed') is not False or data.get('calculation_status')!='not_executed':raise ProjectError('Inconsistent annual startup failure evidence')
        if data.get('evidence')!='runtime-import.log' or log not in report['artifact_hashes'] or data.get('evidence_sha256')!=report['artifact_hashes'][log]:raise ProjectError('Annual startup failure lacks retained import log')
        if not data.get('inputs') or any(not Path(p).is_file() or digest(Path(p))!=h for p,h in data['inputs'].items()):raise ProjectError('Annual startup failure input evidence changed')
        text=(run/log).read_text(encoding='utf-8',errors='replace').lower()
        if (kind=='application_control_block')!=('application control policy' in text):raise ProjectError('Annual startup policy classification differs from import log')
        failures.append(dict(kind=kind,stage='openstudio_import',report=relative,report_sha256=sha,evidence=log,evidence_sha256=report['artifact_hashes'][log],simulation_executed=False))
    return failures


def module_state(run,report,task):
    """Expose verified module diagnostics without inferring a native failure cause."""
    if task['kind'] in ('module_electrical_rules','module_water_rules') and task.get('provider'):
        relative=task['id']+'/provider/result.json'
    elif task['kind'] in ('module_exchange','module_authoring','module_analysis'):
        relative=task['id']+('/exchange/result.json' if task.get('depends_on') else '/result.json')
    else:return {}
    if relative not in report['artifact_hashes']:return {}
    from .modules import verify_result
    result=verify_result(run/relative)
    return dict(provider=result['provider'],execution=result['execution'],acceptance=result['acceptance'],
        numerical_result=dict(status=result['payload']['status'],checks=result['payload']['checks']) if result['execution']['status']=='completed' and result['payload_schema'] in ('bsa.electrical-circuits/1','bsa.air-budget/1','bsa.bound-air-budget/1','bsa.water-graph/1','bsa.bound-water-graph/1') else {},
        regulatory_result=dict(status=result['payload']['status']) if result['execution']['status']=='completed' and result['payload_schema']=='bsa.rule-assessment/1' else {},
        evidence=relative,evidence_sha256=report['artifact_hashes'][relative],design_accepted=False)


def diagnose(plan, run):
    plan, run = Path(plan).resolve(), Path(run).resolve()
    source, report, integrity = context(plan, run)
    if not integrity['integrity_pass']:
        raise ProjectError('stale execution evidence: ' + '; '.join(integrity['issues']))
    tasks = report['tasks']
    ancestors = {}
    rows = []
    for task in source['tasks']:
        name = task['id']
        state = tasks[name]
        from .input_issues import blockers
        input_blockers=blockers(source,name)
        if input_blockers and state['status']=='pass':
            raise ProjectError(f'passing task {name} has unresolved design inputs')
        parents = list(dict.fromkeys([task[key] for key in
            ('depends_on', 'ifc_from', 'junction_from', 'connector_from')
            if task.get(key)]+task.get('requires_pass',[])))
        blocked = [parent for parent in parents if tasks[parent]['status'] != 'pass']
        iteration_baseline = None
        parent = task.get('depends_on')
        if (task['kind']=='circulation_pump_design' and task.get('allow_failed_baseline') is True
                and parent in blocked and parent not in task.get('requires_pass',[]) and state['status']=='pass'):
            from .iteration_baseline import verify_failed_baseline
            from .workflow import local_path
            baseline = next(t for t in source['tasks'] if t['id']==parent)
            iteration_baseline = verify_failed_baseline(run/parent,local_path(plan.parent,baseline['project']),local_path(plan.parent,baseline['binding']))
            recorded = json.loads((run/name/'pump-screening.json').read_text()).get('baseline_recovery')
            if recorded != iteration_baseline:raise ProjectError('missing or changed failed-baseline recovery evidence')
            blocked.remove(parent)
        if blocked and state['status'] == 'pass':
            raise ProjectError(f'passing task {name} has nonpassing dependencies: {blocked}')
        roots = sorted({root for parent in blocked for root in ancestors[parent]})
        if state['status'] != 'pass' and not blocked:
            roots = [name]
        ancestors[name] = roots
        runtime_failures=water_runtime_failures(run,report,name) if state['status']=='fail' else []
        if state['status']=='fail' and task['kind'] in ('annual_energy','annual_energy_ifc'):runtime_failures+=annual_runtime_failures(run,report,name)
        engineering_data_requests=fitting_data_recovery(run,report,name) if task['kind']=='duct_fitting_data' else {}
        module=module_state(run,report,task)
        module_codes={r['code'] for r in module.get('execution',{}).get('diagnostics',[])}
        if input_blockers:
            action = 'resolve the cited missing/conflicting design inputs before a new run'
        elif blocked:
            action = 'resolve upstream tasks before rerunning dependent task'
        elif runtime_failures:
            action = 'resolve the recorded runtime startup failure through a compatible approved environment before a new run;design quantities cannot fix this startup failure'
        elif 'provider_disabled' in module_codes:
            action = 'enable the selected provider or explicitly select a compatible trusted replacement in host configuration before a new run'
        elif 'runtime_missing' in module_codes:
            action = 'supply the selected provider runtime through host options or explicitly select a compatible trusted replacement before a new run'
        elif 'upstream_incompatible' in module_codes:
            action = 'restore the declared clean pinned upstream checkout or explicitly select a compatible trusted replacement before a new run'
        elif 'unsupported_source_semantics' in module_codes:
            action = 'review declared phases and power meaning;select an adapter covering the actual source semantics without deleting fields or converting thermal power into electrical input'
        elif module.get('numerical_result',{}).get('status')=='fail':
            action = 'review the failed declared numerical checks and source design assumptions before revising the design and executing a new run;retain original targets and unresolved engineering acceptance'
        elif module.get('regulatory_result',{}).get('status') in ('fail','pending'):
            action = 'review retained rule assessment and cited source/applicability requirements;resolve failed or unknown checks before a new source-bound run'
        elif state['status'] == 'fail':
            action = 'inspect retained failure evidence and correct source or adapter before a new run'
        elif task['kind'] == 'manual':
            action = 'perform the specified review and record evidence separately'
        elif engineering_data_requests:
            action = 'resolve each retained fitting source/support/review request; preserve original assignment requirements and execute a new source-bound study'
        elif state['status'] == 'pending':
            action = 'resolve the recorded pending condition before a new run'
        else:
            action = 'review complete requirement acceptance against retained artifacts'
        rows.append(dict(id=name, kind=task['kind'], status=state['status'],
                         recorded_scope=state['scope'], dependencies=parents, iteration_baseline=iteration_baseline,
                         blocked_by=blocked, upstream_action_tasks=roots,
                         input_blockers=input_blockers,
                         runtime_failures=runtime_failures,
                         engineering_data_requests=engineering_data_requests,
                         module_state=module,
                         next_action=action,
                         requirement_ids=[r['id'] for r in source['requirements'] if r['task'] == name],
                         evidence=sorted(p for p in report['artifact_hashes'] if p.startswith(name + '/'))))
    # Group declared recovery roots once, retaining every affected requirement.
    # This is scheduling evidence, never a diagnosis of an engineering cause.
    actions=[]
    for row in rows:
        name=row['id']
        affected=[child for child in rows if name in child['upstream_action_tasks']]
        if not affected:continue
        requirement_ids={rid for child in affected for rid in child['requirement_ids']}
        actions.append(dict(task=name,kind=row['kind'],status=row['status'],
            next_action=row['next_action'],recorded_scope=row['recorded_scope'],
            input_blockers=row['input_blockers'],evidence=row['evidence'],
            runtime_failures=row['runtime_failures'],
            engineering_data_requests=row['engineering_data_requests'],
            module_state=row['module_state'],
            affected_tasks=[child['id'] for child in affected],
            affected_requirements=[r for r in source['requirements'] if r['id'] in requirement_ids]))
    return dict(plan_sha256=digest(plan), workflow_sha256=digest(run/'workflow.json'),
                integrity_pass=True, tasks=rows,
                actions=actions,
                execution_pass=all(t['status'] == 'pass' for t in rows),
                design_accepted=False,
                scope='Recorded execution and declared dependency graph only; no engine invocation, automatic repair, or engineering acceptance')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    try:
        result = diagnose(args.plan, args.run)
    except (ProjectError, OSError, ValueError) as exc:
        parser.exit(2, str(exc) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['execution_pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
