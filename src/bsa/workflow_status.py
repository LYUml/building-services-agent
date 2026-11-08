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
        parents = list(dict.fromkeys(task[key] for key in ('depends_on', 'ifc_from') if task.get(key)))
        blocked = [parent for parent in parents if tasks[parent]['status'] != 'pass']
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
                         recorded_scope=state['scope'], dependencies=parents,
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
