# Original electrical constraints in pump ranking

Pump catalogue iteration now optionally checks the operating electrical scenario
for each hydraulically passing candidate before ranking. Select an explicit
original downstream `pump_electrical` task; it must depend on the failed pump.
The project, device ID, steady operating power factor and circuit criteria come
from that task's original source files. Unknown/unrelated tasks reject before
screening output. No replacement electrical project or relaxed hardware is accepted.

```powershell
python -m bsa.pump_catalogue_iteration run ORIGINAL_PLAN ORIGINAL_RUN --task PUMP_ID --catalogue SUPPLIED_CURVES --electrical-task ORIGINAL_COUPLED_TASK --target FRESH_SIBLING_PLAN --out FRESH_PROJECT_LOCAL_FOLDER
python -m bsa.pump_catalogue_iteration verify FRESH_PROJECT_LOCAL_FOLDER
```

The Python API accepts the same `electrical_task` choice. Omission retains the
existing hydraulic-only mode. For a project requiring this coupled eligibility,
select the original task explicitly rather than interpreting hydraulic success
as electrical acceptance.

The new check reuses `pump_electrical.operating_project`, extracted unchanged
from the saved-IFC handoff, and the existing electrical engine. Candidate
hydraulic kW and combined wire-to-water efficiency supply steady electrical kW;
the original power factor, supply voltage, other devices, circuits, breaker,
ampacity factors and branch-drop criteria stay fixed. Both the preliminary screen
and final coupled IFC handoff now use this same load projection. The original
0.75 kW example design baseline is retained separately; the operating estimate
is not a motor nameplate, starting load or replacement design rating.

Candidates must pass both original hydraulic checks and the existing steady
`Ib <= In <= Iz` and branch voltage-drop checks. Reports retain separate
`numerical_checks_pass` and electrical status/details. The objective remains
lowest declared preference among eligible candidates, with lexical ID tie-break;
it is not lowest energy/cost or complete equipment suitability.

If wire-to-water efficiency is absent, electrical input is unknown. The candidate
is pending, never zero-load or assumed-efficiency. A preferred unknown candidate
blocks selecting a less-preferred known passing one; status becomes
`needs_candidate_evidence`, with no target plan or replay. A lower-ranked unknown
does not block an already confirmed preferred choice. This reuses the existing
preference blocker with a domain-neutral pending eligibility flag; existing fan
mechanical pending behavior remains intact. Known electrical failure excludes a
candidate. No eligible candidate produces `no_feasible_candidate` and no replay.

After selection, the unchanged full original graph reruns, including actual
saved IFC identity/units/schema checks and dependent drawing. Screen success
cannot bypass downstream geometry, source, regulatory or engineering failures.
Verification reconstructs source choices, current/voltage checks and pending
preference before checking the ordinary full-plan recovery receipt. Rehashing a
forged electrical pass or removed unknown blocker rejects.

Public synthetic controls:

```powershell
python scripts/run_pump_electrical_catalogue_demo.py --out runs/new-coupled-screen
python scripts/run_pump_electrical_catalogue_demo.py --out runs/new-all-fail --control all-electrical-fail
python scripts/run_pump_electrical_catalogue_demo.py --out runs/new-preferred-unknown --control preferred-unknown
```

Actual positive execution excludes a hydraulically passing synthetic low-efficiency
candidate on original electrical checks, selects the eligible curve and passes
all eight original tasks. Screen and final saved electrical circuit results match
exactly, with original requirements, baseline and hardware preserved. All-fail
and preferred-unknown controls create no target or replay. The curves/efficiencies
are explicit synthetic controls, not manufacturer data. An initial demonstration
filename collision with the pipe-sizing catalogue was rejected before workflow
execution; failed folders are retained and fresh corrected runs verified.
Twenty-six related tests pass, including unchanged baseline/hardware/other-device
projection, current-limit rejection, preferred/lower unknown efficiency ordering,
unrelated task rejection, actual IFC handoff and existing fan behavior.
See [executed evidence](evidence/pump-electrical-catalogue.json).

Motor starting, short-circuit/protection coordination, NPSH, actual product/speed/
efficiency applicability, native DWG/visual review and complete Hong Kong/engineering
acceptance remain pending. Branch-drop checks do not establish whole-installation
statutory compliance. No new solver, dependency, equipment rating or rule clause
is introduced; existing upstream attribution applies.
