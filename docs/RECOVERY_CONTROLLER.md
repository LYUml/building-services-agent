# Bounded automatic recovery controller

The controller selects ready failed pump tasks from fresh source-bound workflow
diagnosis, uses explicitly declared supplied catalogues, independently verifies
each screening/full-plan replay, then diagnoses the resulting whole graph before
choosing another action. It reuses pump_catalogue_iteration, workflow_status and
existing delivery/requirements verification. No solver or new dependency is added.

## Explicit policy

Save a project-local JSON policy before invoking bsa_run_recovery:

```json
{
  "schema": "bsa.recovery-policy/1",
  "max_steps": 4,
  "actions": [
    {"task": "pump", "catalogue": "pump-catalogue.json", "electrical_task": "coupled"}
  ]
}
```

Catalogue paths are relative to the original plan directory, confined by existing
workflow.local_path. Each action names a unique original pump_operating_point;
optional electrical_task must be its original pump_electrical consumer. Declare
that consumer when steady electrical constraints should affect ranking. Only
ready failed tasks without missing-input blockers are eligible. Policy order
breaks ties among eligible tasks; actions cannot select executables, change
ratings/targets, remove source requirements or approve manual review.

Call bsa_run_recovery(plan,original_run,policy,out) using a fresh output inside
the original plan tree and outside the original workflow. Runtime choices come
only from MCP host startup. Each step writes a fresh sibling target plan named
from the output folder and a child screening/replay directory. The existing
adapter reproduces original failure and preserves all original requirements,
ordinary gaps and evidence. Original plans/runs remain unchanged.

After each selected candidate, the whole plan runs and a new diagnosis determines
the next action. Each declared task may be attempted once, with at most twenty
steps. No selected candidate or unresolved preference stops immediately; unknown
preferred data never authorizes fallback. Unsupported failures, missing sources,
runtime blockers, unlisted tasks and manual reviews remain unresolved. An empty
queue does not establish engineering completeness.

Statuses are execution_pass_review_pending (recorded tasks pass only),
needs_action_or_review, step_limit, no_feasible_candidate, or
needs_candidate_evidence. Native failures propagate without a fabricated success;
partial child evidence remains available for diagnosis. Only supported pump
catalogue recovery is automatic here; arbitrary parameter repair, candidate
research, fan/terminal controller dispatch and full semantic design remain open.

## Independent verification

bsa_verify_recovery(out) checks controller source/policy/catalogue pins, reconstructs
each ready decision, verifies every existing pump recovery receipt and links each
next plan/run to the prior replay. It rejects an omitted eligible action, changed
policy, forged final diagnosis or continuation after inconclusive screening.
It returns scoped integrity/execution status and always design_accepted=false.

The public analytic test has two independent hypothetical pump scenarios, not
an installed two-pump system. Both original failures are retained; two fresh
recoveries pass the numerical tasks while the manual requirement stays pending.
Additional controls exercise one-step limit, no-feasible stop, undeclared tasks,
invalid policy, source-policy changes and forged chain. The actual MCP coupled
case also retains the original electrical eligibility gate and no-feasible stop.

Validation: sixteen tests passed with zero skips across two commands, including
actual 21-tool discovery, coupled MCP recovery/electrical constraints and
no-feasible stop. Three retained positive/negative controller journals were
independently reverified. See evidence/recovery-controller.json. An earlier test
was correctly rejected when source code changed in flight; it is not counted
as passing evidence.
