# Cross-discipline recovery scheduling

`python -m bsa.workflow_status <plan.json> <run-directory>` now includes
`recovery_schedule` alongside source-verified task diagnosis, grouped root
actions and engineering review requests.

The scheduler reuses the diagnosed dependency graph. Independent unresolved roots
appear together in the first wave. A shared consumer waits for every nonpassing
prerequisite; deeper consumers appear in later conditional waves. Only the first
wave has `ready_now=true`: ready for the recorded inspection/action, not a blind
rerun. Each wave requires fresh execution and diagnosis before proceeding.
No command is executed, parameter changed, target relaxed or review accepted.

Items retain task identity, direct requirement IDs, prerequisites, evidence paths
and the existing next action. Categories distinguish cited missing inputs,
recorded runtime failures, unavailable/disabled providers, failure evidence,
pending conditions and manual reviews. They do not infer physical causes.
Existing `actions` retains transitive affected requirements. `engineering_actions`
remains a separate required queue, including review requests on passing tasks.
An empty schedule therefore does not establish engineering completion.

Reuse: existing workflow_status diagnosis, delivery.context integrity checks and
declared dependencies; no new engine/dependency or CAD/BIM modelling capability.
Upstream engine attribution and licenses remain unchanged.

Executed evidence: [recovery-schedule.json](evidence/recovery-schedule.json).
The saved positive airflow chain yields manual review only. The no-feasible fan
control yields selection, fan, IFC state, drawing, then review, with only
selection initially ready. The 29 passing related tests cover independent water
and electrical roots, shared prerequisites, input/runtime categories, cycles,
source/artifact tampering, water failure propagation, delivery and iteration.

This prepares a common controller entry for supported recovery adapters.
Automatic design repair, arbitrary brief interpretation and full engineering
acceptance remain unfinished.
