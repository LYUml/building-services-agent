# Saved planar terminal connections

`bsa.air_terminal_drawing` reads a saved DXF, allocation JSON, duct project containing the declared tree, and rigid node-binding JSON. It matches every scoped rigid LINE to a tree section, checks shared node positions, locates each leaf's VAV CIRCLE and each terminal's closed axis-aligned rectangular LWPOLYLINE, and requires exactly one straight flex LINE between the declared pair. Reversed LINE direction is allowed. Duplicate, missing, extra, disconnected or nonplanar geometry rejects. Coordinates use drawing units converted to metres and an absolute correspondence tolerance of 1e-8 m.

```powershell
.venv/Scripts/python -m bsa.air_terminal_drawing reopened.dxf allocation.json ducts.json node-binding.json --out runs/new-terminal-audit.json --supply-layer BSA_SUPPLY --vav-layer BSA_VAV --terminal-layer BSA_DIFFUSER --flex-layer BSA_FLEX
```

Layer names are explicit scope selectors, not automatic discovery. The output pins the exact four source files and records matched handles, per-group outlet counts/flows and individual centre-to-centre plan lengths. The source files are read only and existing outputs are not overwritten. Reuse the native adapter's independently reopened DXF for native evidence; merely inspecting an authored DXF does not establish native DWG acceptance.

The standalone command checks declared inputs, not their association with a completed numerical workflow. Before using its result in delivery, verify that workflow and match the duct project's SHA to the schedule's input_sha256 and allocation to the same executed run. Workflow registration and inherited producer binding are still pending. Do not mistake geometric matching for label/ID annotation verification; identities come from the supplied coordinates and tree, and no symbol size or physical equipment interface is accepted.

Five tests exercise reversed lines, same-flow swapped membership, disconnected flex, extra geometry, nonplanar symbols, shifted VAV and duplicate terminal symbols. Actual private native-export inspection passes for 80 terminals, 20 four-outlet groups and 47 rigid sections. A separate source/hash check confirms the supplied duct project is the one used by the verified schedule. The result does not establish physical inlet/outlet ports, installed flexible length, bend losses, full route coordination, product suitability, ADPI, regulatory conformity or design acceptance.

## Inherit an executed workflow

Use `bsa delivery verify-terminal-connections <plan.json> <workflow-directory> <native-task-id> --out <review.json>` with the same four layer flags. MCP `bsa_verify_terminal_connections` takes project-relative `plan`, `workflow`, `out`, the `native_task` ID, and `supply_layer`, `vav_layer`, `terminal_layer`, `flex_layer`. It verifies the workflow, requires its exact source plan and follows passing native-sheet, prepared-sheet, duct-schedule and allocation dependencies. The drawing, allocation, duct project and rigid binding must match hashes recorded in that workflow. Store the fresh report outside the immutable run. This post-run review is also available as an automatic package stage through HVAC_PACKAGE.md.

Actual private inherited review again matches 80 terminals. Wrong-plan, wrong-task-kind and output-inside-run controls reject; the five geometry tests still pass. This replaces manual file selection while retaining the same limited geometric scope.

The repository's `examples/hvac-package/build_inputs.py` also provides an
independent four-terminal fixture. A fresh run at `ee91947` used AutoCAD 2027
Core Console to save, reopen and plot the DWG. CLI and MCP produced byte-identical
review reports covering four terminal connections and three rigid sections.
MCP rejected the prepared-sheet task ID without writing a report. The rendered
PDF showed both VAV groups, all four labels, the three sizing rows and the
scale reference legibly within the page. The native task passed and the manual
engineering task remained pending. The receipt and drawings stay in local runs.

A second native control swapped the VAV ends of two flex lines in the source
DXF while preserving counts, allocation and sizing inputs. AutoCAD saved and
reopened the altered geometry successfully. Both review interfaces refused a
report and located the missing expected VA–T1 line by group and terminal ID,
layer and endpoint coordinates. The diagnostic also lists saved flex handles
at the terminal, their opposite endpoints and any declared VAV centres at
those endpoints. Native geometric round-trip preservation and
correct terminal assignment are separately checked in this trial.

To reproduce the negative control, generate the fixture with
`python examples/hvac-package/build_inputs.py --out <inputs> --wrong-peer-control`.
Omit `--wrong-peer-control` for the matching positive case. Run
`bsa workflow <inputs>/plan.json --out <run> --autocad <accoreconsole.exe>`.
The workflow exits 2 while its manual engineering task is pending. Check that
the `native` task passed, then run the terminal review for `native` with layers
`DEMO_DUCT`, `DEMO_VAV`, `DEMO_TERMINAL` and `DEMO_FLEX`, in that order.
The positive case writes a report and the negative case exits 2 without one.
Use `--displaced-endpoint-control` with the same workflow to reproduce the
placement check. The AutoCAD 2027 Core Console run saved and reopened the DWG.
The review exited 2 and located the VA-side flex at handle `57`, with its saved
end at `(-5.75, -1.5, 0)` m, 0.25 m from T1. The diagnostic omits lines
whose other endpoint already matches another declared terminal on that VAV.
Verify the intended peer before editing a candidate.
When the HVAC package explicitly enables the terminal review, a failed review
also blocks the package's design-report HTML and PDF. The incomplete package
retains the connection error and native artifacts for diagnosis.
In a fresh paired run with the T1 endpoint restored to its declared centre,
the package generated both reports and returned `review_required` with a
passing terminal review. The offset and restored runs used the same four
scoped layers and AutoCAD 2027 Core Console.
For both saved packages, `bsa delivery inspect-hvac-package` and MCP
`bsa_inspect_hvac_project` returned identical structured results.
The CLI returned exit code 2 for the blocked package and 0 for the restored
package. MCP returned the gate and diagnostics in its successful tool response.
Project package inspection returns `terminal_review_gate` as `passed`,
`blocked` or `not_configured`. It reconciles the saved review with the selected
task and layers and rejects unexpected report output after a blocked review.
