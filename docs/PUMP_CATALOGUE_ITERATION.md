# Supplied pump catalogue to full-plan iteration

`bsa.pump_catalogue_iteration` now compares a bounded set of supplied curves on
the original failed pump's exact network and hydraulic targets, ranks passing
candidates, independently reruns the preferred candidate, then delegates the
chosen curve to the existing full-plan revision orchestrator. It reuses
`pump.solve/run`, fluids pressure calculation, the existing shared preference
screen, requirements modules and catalogue iteration. No solver, optimization
objective, third-party dependency or manufacturer search service is added.

```powershell
python -m bsa.pump_catalogue_iteration run ORIGINAL_PLAN ORIGINAL_RUN --task PUMP_TASK --catalogue SUPPLIED_CATALOGUE --target FRESH_SIBLING_PLAN --out FRESH_PROJECT_LOCAL_FOLDER
python -m bsa.pump_catalogue_iteration verify FRESH_PROJECT_LOCAL_FOLDER
```

The source must be a verified workflow with a ready failed `pump_operating_point`
task. The adapter reconstructs the original failure before creating output.
The exact catalogue fields are `objective`, `source`, `candidates`. Objective is
`lowest declared preference among passing candidates`; each of 1–100 rows has
exactly `id`, `source`, finite `preference` and an embedded existing pump `curve`
contract. IDs are unique, and ties use lexical candidate ID. Curve units, fluid,
speed, pressure rise, efficiency basis, declared bracket and numerical bounds
are validated by the existing pump engine. No extrapolation or new target is
introduced. Invalid catalogue contracts reject; unsupported domain trials remain
recorded as unsuccessful candidates rather than fabricated operating points.

The preferred passing candidate is conditional on the original hydraulic checks,
not on verified motor/NPSH/product suitability or an energy/cost objective.
Electrical performance and other source tasks are freshly evaluated by the
original downstream graph. A downstream failure remains a failure; this adapter
does not re-rank by undeclared electrical criteria or waive missing equipment
facts. Source strings and input hashes do not authenticate vendor data. Inspect
and source actual manufacturer curve/efficiency/speed/applicability before use.

The screening folder must be new and inside the source plan tree. Generated
candidate and selected curves are immutable copies of the supplied catalogue
data. The new target plan is a separate fresh sibling of the original. Original
inputs/runs, all source requirements, ordinary gaps and electrical baseline/
hardware remain unchanged. With no passing candidate, no target plan or replay
is created. With a choice, the existing recovery runner reproduces the failed
baseline again, changes only the pump curve reference, rebuilds requirements and
reruns the complete plan. Trusted Python `execute_options` supports the existing
host engines/provider controls; documents cannot choose executables.

Verification reconstructs the original failure and every candidate from current
source, repeats ranking/tie-break, checks saved curves/results and full artifact
inventories, then independently verifies the exact selected-curve full-plan
replay. Passing is correspondence, not complete engineering approval. Changed
source, selected ID/ranking, saved curve or omitted obligations cannot be accepted
by rehashing output files. CLI run returns 2 while acceptance remains incomplete;
verify returns 0 for intact correspondence and still reports `design_accepted=false`.

Public synthetic trials:

```powershell
python scripts/run_pump_catalogue_iteration_demo.py --out runs/new-pump-catalogue
python scripts/run_pump_catalogue_iteration_demo.py --out runs/new-empty-pump-catalogue --no-eligible
```

Actual positive trial excludes the preferred insufficient curve, selects the
eligible synthetic curve and passes all eight existing coupled water/electrical/
IFC/DXF tasks. All eight requirements and original 0.75 kW baseline survive. The
negative retains no feasible candidate and creates neither a target nor replay.
These curves are synthetic controls, not actual products. Native DWG/visual
plotting, physical installation, full Hong Kong applicability and complete
engineering acceptance remain pending. See
[executed evidence](evidence/pump-catalogue-iteration.json).

Thirty-one related tests pass, including actual direct-network ranking/replay,
no-feasible suppression, tied preference, rehashed saved-curve/selected-ID rejection,
invalid catalogues, and existing pump/fan/recovery behavior. The existing upstream
IfcOpenShell ResourceWarning remains visible; it does not constitute design approval.
