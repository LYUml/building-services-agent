# Bounded automatic recovery controller

The controller selects ready failed pump or circular-fan selection tasks from fresh source-bound workflow
diagnosis, uses explicitly declared supplied catalogues, independently verifies
each screening/full-plan replay, then diagnoses the resulting whole graph before
choosing another action. It reuses pump_catalogue_iteration, catalogue_iteration, workflow_status and
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
workflow.local_path. Each action names a unique original pump_operating_point or circular_fan_selection;
optional electrical_task must be its original pump_electrical consumer. Declare
that consumer when steady electrical constraints should affect ranking. Fan actions cannot declare electrical_task; their existing source-backed
mechanical constraints remain inside the supplied catalogue, with secondary
record/PDF files pinned before the first action. Only
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
partial child evidence remains available for diagnosis. Only supported pump catalogue and circular-fan selection recovery are automatic
here; arbitrary parameter repair, candidate research, terminal controller dispatch
and full semantic design remain open.

## Independent verification

bsa_verify_recovery(out) checks controller source/policy/catalogue pins, reconstructs
each ready decision, verifies every existing pump/fan recovery receipt and links each
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

## Mixed air/water recovery

For a circular_fan_selection action, the controller uses the existing
catalogue_iteration failure reconstruction, unchanged source/requirement plan
revision, common requirements inventory and full workflow execution. Its
independent verifier reconstructs that source/ranking/operating handoff.
The next action consumes that actual replay, never the original diagnosis.

Pump no-selection retains its original run without creating a new target.
Fan catalogue revision uses the existing engine's fresh full failed replay even
when no supplied candidate is eligible: the controller records that revised
failed plan/run as current, then stops before any later action. It does not
report the unchanged old catalogue as the final evaluated state. Pending preferred
mechanical evidence normalizes to needs_candidate_evidence; known failure to
no_feasible_candidate. No fan motor/electrical eligibility is implied by the pump
consumer option.

The mixed public trial preserves all ten original air-system source requirements,
adds an explicit independent hypothetical pump paragraph, and retains its manual
review. It is a combined recovery graph, not a physically coupled air/water design.
No real product, measured route or source target is invented. Native air route,
pressure, fan operation, saved IFC metadata and drawing remain their existing
scoped adapters; original air and weak pump evidence is retained.

Actual SDK transport can be exercised against an existing declared public project:

```powershell
python scripts/run_recovery_mcp_demo.py --project-root runs/PUBLIC_PROJECT --plan plan.json --original-run original --policy policy.json --out mcp-controller --receipt mcp-protocol.json
```

The script configures the local stdio host, invokes the controller and verifier,
and saves their actual structured responses to a fresh project-local receipt.
It does not stage private sources, configure a desktop client or select native
executables. Domain/runtime availability remains the existing host prerequisite.

## Execution cost

The current engine reruns unchanged native route geometry in each full replay.
The demonstrated mixed case therefore takes minutes, including on this small
public scenario. No incremental-execution speedup is claimed. The SDK demo waits
for synchronous completion; named desktop-client timeout behavior is unverified.
Future reuse/progress handling must preserve source, model and result checks.

Confirmed mixed evidence: 27 regression tests passed (8.348 seconds), and the
retained no-feasible fan scenario passed one actual test (360.948 seconds).
The direct positive and real MCP mixed runs independently verify two steps,
eleven preserved requirements and ten passing scoped tasks, with manual review
pending. The negative retains its revised failed run and never starts the pump
action. An earlier full-suite terminal result was not retrieved and is not
counted as a complete passing suite. See evidence/mixed-recovery-controller.json.
