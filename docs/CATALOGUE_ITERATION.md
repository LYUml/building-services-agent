# Full-plan fan catalogue recovery

`bsa.catalogue_iteration` takes an existing source-verified failed workflow and
an explicitly host-supplied revised circular fan catalogue. It reproduces the
original no-selection failure before writing a new plan. It changes only the
selected task's catalogue path, preserving every requirement, source passage,
unresolved input, task dependency and engineering target.

The revised catalogue must be a real sourced input inside the original plan's
directory tree. Prepare it and any referenced mechanical source files there
without overwriting originals. This adapter does not invent vendor data or
expand a curve's validated range. The replacement is an explicit design choice;
it does not rewrite the original brief or constitute an approved substitution.

```
python -m bsa.catalogue_iteration ORIGINAL_PLAN ORIGINAL_RUN 
  --task SELECTION_ID --catalogue REVISED_CATALOGUE 
  --target NEW_SIBLING_PLAN --out NEW_RUN_DIRECTORY
```

The command creates a fresh requirements inventory bound to the new plan, runs
the entire original task graph through the existing executor, and diagnoses
the result. It preserves the failed run. Later consumers, IFC property writing
and drawing still depend on their original numerical checks. Manual review is
never accepted automatically. Exit status 2 is intentional: inspect the JSON
status, stages and stage errors; this command cannot establish full acceptance.
The Python API accepts the same explicit host runtime options as terminal
iteration; plan content cannot inject runtime commands.

Use `python -m bsa.catalogue_iteration_verify NEW_RUN_DIRECTORY` (or its `verify`
Python API) for independent
verification. It checks source/method/artifact pins, freshly reconstructs the
original failed candidates, confirms the exact catalogue-only plan change and
unchanged requirement/input lists, checks the bound inventory and new diagnosis,
and replays the selected catalogue handoff if selection passes. A successful
verification is scoped evidence integrity, not a complete engineering design.

Reuse: existing circular_fan_selection, its shared preference screen, fluids
network solver, requirements source-inventory provider, workflow executor and
dependency diagnosis. No engine, package, vendor curve or regulatory clause is
newly implemented. Existing upstream licensing and attribution apply unchanged.

Current scope is a ready failed `circular_fan_selection` task with no selected
candidate. Failed native geometry, missing source inputs, nonpassing upstream
pressure, arbitrary task repair, automatic catalogue discovery and complete
multi-discipline recovery are not handled by this adapter.

The executed positive case uses synthetic source curves on the existing local
circular chain. Its drawing task produces the inherited route-only DXF; this
recovery trial does not establish native DWG reopening or visual plot acceptance.
Real vendor equipment, complete branches and Hong Kong compliance remain pending.

Executed evidence: [catalogue-iteration.json](evidence/catalogue-iteration.json).
Both full runs reproduce the original failure and preserve all ten source
requirements. With an eligible synthetic candidate, selection/operation/IFC
state/route drawing pass and manual review stays pending. With only insufficient
candidates, selection fails and operation/state/drawing/review remain pending;
no operating-state IFC or DXF is created. Independent verification passes for
both. Four receipt mutations (removed requirements, forged plan hash, false
completion status, omitted original workflow pin) reject; original bytes are
restored and verified. Thirty-seven related tests and skill validation pass.
An earlier external-path attempt was retained as failed; plan-local path checks
now reject that condition before output creation.
