# Current WNTR runtime boundary

On 2026-11-11, a fresh isolated import of the installed pinned WNTR1.5.0 failed:
Windows reported that Application Control blocked the native `_network_isolation`
component. This happens while importing WNTR, before the EPANET solver is invoked.
An installed distribution does not establish runtime availability.

The actual source-example circulation reproduction in ignored
`runs/circulation-regression-probe` preserves the worker traceback and a failed
hydraulic report. No pipe flows were produced; the dependent thermal target cannot
pass. This is an environment failure, not evidence of an undersized pipe or
insufficient thermal transport. Source-based calculations that do not use WNTR,
including scoped fixture demand, have a different runtime boundary.

Recheck the import without changing policy or starting a simulation:

```powershell
.venv/Scripts/python -X utf8 scripts/probe_water_runtime.py --out runs/new-water-runtime-probe.json
```

The runner reuses the energy probe's isolated child-process helper and30-second
timeout. It records installed/required versions, raw output and whether the actual
message explicitly mentions Application Control. The executed report
`runs/water-runtime-regression-probe.json` has import_pass=false,
explicit_application_control_message=true and simulation_executed=false. A future
passing import still needs actual EPANET execution, numerical QA and all relevant
domain/model/regulatory checks. No security setting, binary or loader is modified.

The complete regression finished with988 invocations,25 failures,17 errors and103
skips; see REGRESSION_20261111.md for classification and limitations. The suite did
not pass. The water adapter now records an explicit application_control_block
category when the worker log contains that message, without emitting pipe results.
Historical successful WNTR/EPANET results remain evidence of their original runs,
not current-host availability. Existing failure/downstream gates must remain intact.
