"""Source-bound task dependency diagnosis for the host agent; never resumes engines."""
import argparse
import json
from pathlib import Path

from .cli import digest
from .delivery import context
from .engine import ProjectError


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
        if blocked:
            action = 'resolve upstream tasks before rerunning dependent task'
        elif state['status'] == 'fail':
            action = 'inspect retained failure evidence and correct source or adapter before a new run'
        elif task['kind'] == 'manual':
            action = 'perform the specified review and record evidence separately'
        elif state['status'] == 'pending':
            action = 'resolve the recorded pending condition before a new run'
        else:
            action = 'review complete requirement acceptance against retained artifacts'
        rows.append(dict(id=name, kind=task['kind'], status=state['status'],
                         recorded_scope=state['scope'], dependencies=parents, iteration_baseline=iteration_baseline,
                         blocked_by=blocked, upstream_action_tasks=roots,
                         next_action=action,
                         requirement_ids=[r['id'] for r in source['requirements'] if r['task'] == name],
                         evidence=sorted(p for p in report['artifact_hashes'] if p.startswith(name + '/'))))
    return dict(plan_sha256=digest(plan), workflow_sha256=digest(run/'workflow.json'),
                integrity_pass=True, tasks=rows,
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
