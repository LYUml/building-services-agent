---
name: mep-requirements
description: Extract source-backed requirements, missing parameters and acceptance criteria from MEP assignment briefs and reference drawings before design.
---

# mep-requirements

Read the actual document, including drawing notes and deliverable list; cite page/section for each requirement. Create requirements.json with id, source_document, locator, requirement, discipline, deliverable, verification_method, status and evidence. Unknown values must remain unresolved.
Create a project data file using docs/PROJECT_FORMAT.md for supported electrical tasks. Distinguish measured inputs, manufacturer data, course-given values, design targets and explicit assumptions. A proposed assumption is not a supplied fact. Record thermal kW, electrical kW and kVA separately.
Before geometry, prove source units and scale using a known dimension and identify WCS/local coordinate transformation. Before simulation, collect climate/weather, constructions, infiltration, occupancy/load schedules and HVAC control assumptions. Missing inputs may permit an explicitly labelled scenario, but not an asserted measured answer.
Keep supplied files unchanged and record hashes. Do not upload private source documents to external services without task authorization.

## Executable intake and planning
Read docs/WORKFLOWS.md. Run `python -m bsa.workflow intake <brief.md> --out <new-intake.json>` for supported UTF-8 text. Interpret every indexed passage, classify requirement/context with care, author a plan following examples/workflow-plan.json, and populate the appropriate source-backed project JSON. Quotes must match the actual brief. `python -m bsa.workflow validate <plan.json>` checks source linkage and coverage, not semantic correctness. Keep unsupported formats or missing inputs explicit; do not silently discard drawing notes, tables or pages.
