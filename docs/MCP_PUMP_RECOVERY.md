# MCP pump failure to candidate screening and full-plan replay

Two MCP tools now expose the existing verified pump catalogue recovery and its
independent verifier. No selection algorithm, engineering engine, dependency or
new repair policy is added. The server now has fourteen tools; the exact guide
is available at `bsa://recovery-guide`.

After `bsa_execute_workflow` or `bsa_diagnose_workflow`, inspect the source-linked
`recovery_schedule.ready_tasks` and original task kinds. For a ready failed
`pump_operating_point` with an explicitly supplied sourced curve catalogue, call:

| Tool | Arguments |
|---|---|
| bsa_recover_pump_catalogue | plan, original_run, task, catalogue, target, out; optional electrical_task |
| bsa_verify_pump_recovery | out |

All paths are relative to the fixed host project root. `target` is a fresh
sibling plan; `out` is a new screening folder inside its source plan tree.
The source graph, original failure, inputs, method pins and ready-task state are
validated before recovery. The worker invokes existing
`pump_catalogue_iteration.run/verify`; native runtime/provider choices come only
from server startup, not client arguments or brief contents.

Select `electrical_task` explicitly when original downstream steady electrical
constraints should affect ranking. It must be the original `pump_electrical`
consumer of this pump. Curve contract, original hydraulic targets, current/
ampacity/branch-drop checks, pending preferred efficiency and lexical preference
tie-break remain those documented in [pump screening](PUMP_CATALOGUE_ITERATION.md)
and [electrical eligibility](PUMP_ELECTRICAL_CATALOGUE.md). Do not invent curve
points, relax a target, replace original hardware or assume missing efficiency.

The existing engine reconstructs the failed baseline, evaluates supplied
candidates and independently reruns the preferred eligible curve. If selected,
the original full graph executes with a fresh requirements inventory and only
the declared pump-curve reference changed. Original requirements, ordinary gaps,
baseline electrical load and failed evidence remain intact. An empty numerical
recovery queue is not design approval.

Read structured status, not only MCP call success. `no_feasible_candidate` or
`needs_candidate_evidence` creates no target/replay. Other source, native,
regulatory and engineering failures stay in the complete rerun. Verification
reconstructs source/ranking/result correspondence and returns
`design_accepted=false`; it cannot certify actual equipment or installation.

Actual stdio client execution obtains eleven declared JSON assets through the
committed reference resources; only the public original brief is host-staged.
The authored synthetic pressure-deficient baseline fails. The client selects
the pump task from the actual diagnosis ready queue, supplies two synthetic
curves and invokes recovery through MCP. The preferred hydraulically passing
low-efficiency candidate fails original electrical checks; the eligible curve
is selected and all eight original water/electrical/IFC/DXF tasks pass scoped
execution. The independent MCP verifier passes. A second all-ineligible catalogue
stops without target/replay. Original plan and failed workflow bytes remain
unchanged. The existing source/visual/reference protocol case also still passes.
Seven targeted protocol/reference tests pass.
See [executed evidence](evidence/mcp-pump-recovery.json).

These are supplied synthetic curves, not discovered manufacturer data. This
adapter handles a specific existing recoverable task, not arbitrary autonomous
engineering repair. Real equipment/speed/efficiency, motor starting/protection,
NPSH, physical installation, native DWG/RVT/plot and complete Hong Kong/engineering
acceptance remain unestablished. Existing task/model/licence scopes are retained.
