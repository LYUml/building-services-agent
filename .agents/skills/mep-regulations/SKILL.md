---
name: mep-regulations
description: Select source-pinned jurisdiction rule packs and bind supported MEP calculations to scoped regulatory checks. Use for local-code applicability, Hong Kong electrical voltage-drop or office lighting LPD checks, and regulatory workflow gates.
---

# MEP jurisdiction checks

Read repository-relative docs/REGULATION_PACKS.md. Establish the project's jurisdiction, building/works scope, relevant dates and required disciplines from the brief and official sources. Select explicit pack IDs and edition decisions; do not choose the latest edition merely from today's date. Distinguish legislation, codes, utility conditions, guidance and contract specifications. Missing statutory/application facts remain pending. The current Hong Kong modules cover selected electrical voltage-drop, office LPD and HVAC load-design condition paths, not full conformity.

Use the pack's official index/publication links to review amendments and transition provisions for the actual project. Fetch the required cached sources with scripts/fetch_regulation_sources.py; a hash mismatch needs source/version review and a new deliberately pinned pack rather than rewriting old evidence. Preserve source attribution and keep original official PDFs in the local ignored cache. A source catalog is not an executable rule set.

Choose the binding matching the available project evidence:

- For sourced facts only, use `bsa.regulations` or workflow kind `regulations`. Facts and edition decisions require evidence references; their strings do not authenticate the underlying documents.
- For electrical origin-to-equipment voltage drop, read docs/ELECTRICAL_PATHS.md and use `electrical_regulations` with original project, topology, basis, pack and sources. It recalculates supported single-phase radial paths and preserves branch failures. Never substitute a branch-only drop, starting transient or unsupported three-phase calculation. Topology completeness, feeder protection and coefficient applicability remain separate.
- For office lighting, read docs/HK_LIGHTING_RULES.md. Use `lighting_regulations` with shared electrical and geometry inputs plus exact per-space bases. This derives full fixture watts and rectangular source-space areas; it does not verify saved IFC geometry or statutory internal area. Do not reduce LPD with demand/dimming factors, infer driver losses, pool separate rooms or invent exclusions. Non-light classes and unresolved scope remain visible.
- For HVAC design-basis checks read docs/HK_HVAC_RULES.md and docs/HVAC_IDF_RULES.md. Use `bsa.hvac_idf_rules` for supported saved native static sizing controls and design days, with exact zone basis coverage. It derives native numeric values, checks the whole RH band conservatively and includes winter daily-range minima. Match its IDF hash to the actual engine run; automatic workflow correspondence and arbitrary controls remain unsupported. Separate JSON facts cannot prove model correspondence. Keep maintained-state performance, load-method, equipment and remaining HVAC clauses pending.
- When lighting performance is required, also use ../mep-lighting-analysis/SKILL.md. LPD and actual IES/Radiance illuminance are distinct checks. scripts/run_hk_lighting_demo.py is a synthetic integration demonstration, not an actual project's target/photometry source.

In a source-linked workflow, declare `requires_pass` for relevant downstream authoring tasks using docs/WORKFLOWS.md. Bind the checks to the same project/geometry as their consumers; known electrical/lighting consumers validate identical project/geometry bytes, including inherited producer inputs. Other cross-domain correspondences and mandatory-check discovery remain manual. Include outstanding statutory/control/domain requirements in the requirement matrix even when no executable rule supports them.

Inspect per-circuit/per-space findings, input/source hashes and coverage, then use `python -m bsa.workflow verify` and `python -m bsa.workflow_status` for recorded integrity and blockers. Preserve `pending`, `review_required`, `not_applicable` and branch failures. An exception to one rule is not whole-project approval. Even a passing supported task leaves `regulatory_compliance: not_established` and complete engineering acceptance unresolved; use ../mep-delivery-check/SKILL.md for the full deliverable review.
