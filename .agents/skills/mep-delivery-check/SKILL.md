---
name: mep-delivery-check
description: Audit building services models, drawings, calculations and reports against source requirements before delivery, preserving unresolved engineering and visual checks.
---

# mep-delivery-check

Re-read the requirement matrix and inspect evidence for each deliverable. Check source hashes and provenance, unknown assumptions, code editions, IDs and counts across equipment, circuits, model, diagrams and report.
Run calculations and review failures. Validate units and native model semantics. For DWG, reopen in AutoCAD and inspect native entities; separately export and visually review every PDF sheet for scale, clipped content, lineweights and legibility. A successful command or DXF validator cannot stand in for either gate.
For simulations inspect actual engine logs, version, model/weather inputs and result units. Distinguish reproducibility, numerical checks and engineering acceptance.

For pump operating points, inspect the explicit fixed terminal-pressure/free-flow boundary, original curve and positive bracket, fluid/regime applicability, signed root residuals, both convergence tolerances, conservative minimum-flow/velocity checks and saved-state rerun. Verify power uses pump-added pressure and explicitly combined wire-to-water efficiency. A converged point can fail capacity; an electrical estimate does not update or validate the electrical project. See docs/PUMPS.md for limits.

For `pump_electrical`, verify explicit electrical/pump/outlet identity, connected source geometry, source/artifact hashes and replay. Compare baseline and operating scenarios, unchanged hardware/other devices, unchanged original IFC entities and saved new properties. Require baseline checks as well as operating checks; keep nameplate/starting/protection, electrical topology and unbound devices pending. See docs/PUMP_ELECTRICAL.md.
The initial CLI manifest proves only its JSON input remained unchanged and its emitted CIRCLE count matches device count. It does not prove all source documents unchanged, correct native geometry, print quality or complete protection design.
Create an acceptance record with pass/fail/pending and evidence paths. Pending required checks mean the delivery is incomplete; never erase them to obtain a green status.

For saved-IFC schedules/diagrams, inspect drawing.json coverage, excluded classes, profile/port/metadata consistency and DXF GUID/count reconciliation. Compare true and projected lengths, then inspect preview legibility. IFC_DRAWINGS.md documents the limited centreline scope; native plots, equipment/fittings and installation acceptance remain separate gates.

For `ifc_native`, inspect native-verification.json and the reopened DWG export: model handles/counts, IFC XDATA, supported geometry, source hashes and physical PDF reference must pass. Render that run's actual PDF; store its hash and image hash with the visual observations separately, preserving workflow artifact integrity. Equipment/fittings and full installation acceptance remain pending for centreline diagrams.

For orchestrated projects, run `python -m bsa.workflow verify <run-directory>` before interpreting results. It checks recorded source and task-artifact hashes, not report authenticity or engineering correctness. Compare every acceptance description in workflow.json against its actual artifacts and source paragraph; do not use execution_status as acceptance_status. Record visual and domain reviews separately with artifact hashes.

When IFC coordination is required, inspect docs/CLASH.md and the saved clash.json. Confirm geometry coverage, units, policy sources/tolerances, Boolean checks and all accepted contact exceptions. A source-connected pair is not exempt from solid overlap. For outside_regions mode inspect both directional proofs; legacy pair-minimum exceptions leave non-interface clearances pending. Keep unverified product geometry pending; an empty findings table alone is insufficient.
