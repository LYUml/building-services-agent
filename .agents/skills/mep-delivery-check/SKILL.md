---
name: mep-delivery-check
description: Audit building services models, drawings, calculations and reports against source requirements before delivery, preserving unresolved engineering and visual checks.
---

# mep-delivery-check

Re-read the requirement matrix and inspect evidence for each deliverable. Check source hashes and provenance, unknown assumptions, code editions, IDs and counts across equipment, circuits, model, diagrams and report.
Run calculations and review failures. Validate units and native model semantics. For DWG, reopen in AutoCAD and inspect native entities; separately export and visually review every PDF sheet for scale, clipped content, lineweights and legibility. A successful command or DXF validator cannot stand in for either gate.
For simulations inspect actual engine logs, version, model/weather inputs and result units. Distinguish reproducibility, numerical checks and engineering acceptance.
The initial CLI manifest proves only its JSON input remained unchanged and its emitted CIRCLE count matches device count. It does not prove all source documents unchanged, correct native geometry, print quality or complete protection design.
Create an acceptance record with pass/fail/pending and evidence paths. Pending required checks mean the delivery is incomplete; never erase them to obtain a green status.

For saved-IFC schedules/diagrams, inspect drawing.json coverage, excluded classes, profile/port/metadata consistency and DXF GUID/count reconciliation. Compare true and projected lengths, then inspect preview legibility. IFC_DRAWINGS.md documents the limited centreline scope; native plots, equipment/fittings and installation acceptance remain separate gates.

For orchestrated projects, run `python -m bsa.workflow verify <run-directory>` before interpreting results. It checks recorded source and task-artifact hashes, not report authenticity or engineering correctness. Compare every acceptance description in workflow.json against its actual artifacts and source paragraph; do not use execution_status as acceptance_status. Record visual and domain reviews separately with artifact hashes.

When IFC coordination is required, inspect docs/CLASH.md and the saved clash.json. Confirm geometry coverage, units, policy sources/tolerances, Boolean checks and all accepted contact exceptions. A source-connected pair is not exempt from solid overlap. For outside_regions mode inspect both directional proofs; legacy pair-minimum exceptions leave non-interface clearances pending. Keep unverified product geometry pending; an empty findings table alone is insufficient.
