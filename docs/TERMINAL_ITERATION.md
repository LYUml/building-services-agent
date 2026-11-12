# Single-command source-bound terminal iteration

This entry point composes existing terminal search, candidate-plan factory,
requirements provider, workflow execution and diagnosis. It adds no new design,
geometry, pressure or rule engine and no dependency. It starts from an existing
source-verified workflow; arbitrary raw-brief interpretation is not implemented
by this command. See AUTOMATIC_TERMINAL_SEARCH.md for the bounded design scope.

```powershell
.venv/Scripts/python -m bsa.terminal_iteration ORIGINAL_PLAN ORIGINAL_RUN --task PERFORMANCE_TASK --policy SEARCH_POLICY --geometry-policy GEOMETRY_POLICY --target NEW_PLAN --out NEW_RUN --module-provider recognition=ifcopenshell.polygon-spaces
```

All paths must be repository-local or explicitly host-selected project paths.
NEW_PLAN is a fresh same-directory sibling of ORIGINAL_PLAN, following the
existing factory contract. NEW_RUN is new and separate from original sources,
original run and target-plan input folders. Existing outputs are preserved;
partial failure outputs are diagnostic and a retry needs fresh paths.

Search uses declared grids/objective and inherited catalogue selections. If no
whole candidate is feasible, it publishes no plan or execution. If downstream
BIM tasks need geometry transfer and no explicit policy is supplied, it stops at
needs_geometry_policy rather than inventing templates. The supplied geometry
policy retains its existing same-room/classification restrictions.

For a feasible supported candidate, the command generates the full original
plan, regenerates bsa.source-requirements against that exact new plan, then
binds its completed result to the new workflow. It does not reuse an inventory
bound to the old plan. Source inventory is not semantic completeness or design
acceptance. Disabling the requirements provider stops before workflow execution.

Host module overrides, disabled providers, MOOSAS checkout/dependency paths and
optional AutoCAD path use existing trusted host configuration. Documents cannot
supply new commands or engine implementations. The Python API accepts the
existing engine options via a strict allowlist; source selection and nested
provider/disable records are rechecked. No host runtime is silently substituted.

Outputs are search/, requirements/, workflow/, diagnosis.json and iteration.json
when their prerequisite stages execute. The receipt retains all original
requirements/unresolved inputs, complete original source/artifact pins, stage
outcomes and execution/engineering action queues. No original review pass is
transferred, no thresholds are relaxed and no automatic physical repair occurs.
An explicit stage error stops later stages and preserves partial artifacts.

Statuses include no_feasible_candidate, needs_geometry_policy,
requirements_unavailable, execution_incomplete, needs_engineering_review,
failed and source_changed. The CLI returns2 because complete engineering
acceptance is never established by this entry point. Distinguish an executed
pipeline from a design that passed all required checks. Inspect stage_errors,
source integrity and action evidence instead of treating exit2 as one generic
engine failure. verify(folder) rechecks retained source/stages and nested reports;
it does not claim authenticated execution or actual installed truth.

See evidence/terminal-iteration.json for actual executions and limits. This is
an internal synthetic source-bound workflow demonstration, not automatic
coursework submission or a completed multi-discipline agent.

Executed validation:18related automated tests pass and the design skill format
is valid. Current-source native and infeasible single-command runs and complete
receipt replay were executed. The native run binds13fresh source requirements
to the exact new plan, creates five stubs/ten friction cases and retains five
clearance failures plus12engineering requests. The infeasible branch preserves
all13original requirements and starts neither target plan nor workflow.

External-project eligibility follows the underlying adapters and explicit host
workspace; this command does not migrate unsupported adapters or justify storing
private coursework in the tool repository.
