# Saved planar terminal connections

`bsa.air_terminal_drawing` reads a saved DXF, allocation JSON, duct project containing the declared tree, and rigid node-binding JSON. It matches every scoped rigid LINE to a tree section, checks shared node positions, locates each leaf's VAV CIRCLE and each terminal's closed axis-aligned rectangular LWPOLYLINE, and requires exactly one straight flex LINE between the declared pair. Reversed LINE direction is allowed. Duplicate, missing, extra, disconnected or nonplanar geometry rejects. Coordinates use drawing units converted to metres and an absolute correspondence tolerance of 1e-8 m.

```powershell
.venv/Scripts/python -m bsa.air_terminal_drawing reopened.dxf allocation.json ducts.json node-binding.json --out runs/new-terminal-audit.json --supply-layer BSA_SUPPLY --vav-layer BSA_VAV --terminal-layer BSA_DIFFUSER --flex-layer BSA_FLEX
```

Layer names are explicit scope selectors, not automatic discovery. The output pins the exact four source files and records matched handles, per-group outlet counts/flows and individual centre-to-centre plan lengths. The source files are read only and existing outputs are not overwritten. Reuse the native adapter's independently reopened DXF for native evidence; merely inspecting an authored DXF does not establish native DWG acceptance.

The standalone command checks declared inputs, not their association with a completed numerical workflow. Before using its result in delivery, verify that workflow and match the duct project's SHA to the schedule's input_sha256 and allocation to the same executed run. Workflow registration and inherited producer binding are still pending. Do not mistake geometric matching for label/ID annotation verification; identities come from the supplied coordinates and tree, and no symbol size or physical equipment interface is accepted.

Five tests exercise reversed lines, same-flow swapped membership, disconnected flex, extra geometry, nonplanar symbols, shifted VAV and duplicate terminal symbols. Actual private native-export inspection passes for 80 terminals, 20 four-outlet groups and 47 rigid sections. A separate source/hash check confirms the supplied duct project is the one used by the verified schedule. The result does not establish physical inlet/outlet ports, installed flexible length, bend losses, full route coordination, product suitability, ADPI, regulatory conformity or design acceptance.

## Inherit an executed workflow

Prefer `python -m bsa.air_terminal_review <plan.json> <workflow-directory> <native-task-id> --out <review.json>` with the same four explicit layer flags. It verifies the workflow, requires its exact source plan and follows passing native-sheet, prepared-sheet, duct-schedule and allocation dependencies. Drawing, allocation, duct project and rigid binding are resolved from that ancestry; no replacement source arguments are accepted. The review records the workflow/plan/schedule hashes and checks workflow integrity again afterward. Store it outside the immutable run. This is a post-run review command, not yet a registered task or an automatic package stage.

Actual private inherited review again matches 80 terminals. Wrong-plan, wrong-task-kind and output-inside-run controls reject; the five geometry tests still pass. This replaces manual file selection while retaining the same limited geometric scope.
