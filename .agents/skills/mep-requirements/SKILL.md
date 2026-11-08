---
name: mep-requirements
description: Extract source-backed requirements, missing parameters and acceptance criteria from MEP assignment briefs and reference drawings before design.
---

# mep-requirements

Read the actual document, including drawing notes and deliverable list; cite page/section for each requirement. Create requirements.json with id, source_document, locator, requirement, discipline, deliverable, verification_method, status and evidence. Unknown values must remain unresolved.
Create a project data file using docs/PROJECT_FORMAT.md for supported electrical tasks. Distinguish measured inputs, manufacturer data, course-given values, design targets and explicit assumptions. A proposed assumption is not a supplied fact. Record thermal kW, electrical kW and kVA separately.
Before geometry, prove source units and scale using a known dimension and identify WCS/local coordinate transformation. Before simulation, collect climate/weather, constructions, infiltration, occupancy/load schedules and HVAC control assumptions. Missing inputs may permit an explicitly labelled scenario, but not an asserted measured answer.
Keep supplied files unchanged and record hashes. Do not upload private source documents to external services without task authorization.

For local-code requirements use ../mep-regulations/SKILL.md. Record jurisdiction, building/works scope, relevant dates, selected editions and applicability evidence before assigning numeric limits. Keep regulatory clauses distinct from course targets and contract specifications. Map unimplemented disciplines/clauses to explicit pending review requirements; a narrow rule pack cannot replace the brief's full scope.

For DWG/DXF input, read docs/DRAWING_INTAKE.md and use `bsa.cad_intake` or a `drawing_intake` workflow task. Inventory first, then review and hash-bind an explicit selection of boundary handles plus a known independent LINE dimension. Do not infer room meaning from a closed outline, derive scale from labels alone, or silently ignore nested blocks/xrefs. Unitless, curved or unsupported geometry remains unresolved. Native export and polygon measurements do not prove DWG fidelity or plot quality.

## Executable intake and planning
Read docs/WORKFLOWS.md and docs/DOCUMENT_INTAKE.md. Run `python -m bsa.workflow intake <brief> --out <new-intake.json>` for Markdown, text, PDF or DOCX. Interpret every indexed passage, classify requirement/context with care, author a plan following examples/workflow-plan.json, and populate the appropriate source-backed project JSON. Quotes must match the actual extracted source. `python -m bsa.workflow validate <plan.json>` checks source linkage and coverage, not semantic correctness. Keep missing inputs explicit; do not silently discard drawing notes, tables or pages.

Inspect every extraction issue against actual source pages or Word rendering, then record specific `document_review` notes. Word XML locators are not page numbers. Tracked changes and pages without extracted text block planning. For PDF OCR, use the optional local `bsa.ocr` adapter, retain raw text/boxes/confidence and bind sidecar/images to source hashes. Review symbols, decimal points and units visually; confidence does not prove correctness. Never silently normalize a mistaken OCR equipment ID into an assumed design value. Mixed readable text/image pages still need figure review.
