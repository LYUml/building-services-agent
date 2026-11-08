---
name: building-services-design
description: Orchestrate building services assignments from a brief and source drawings to editable CAD/BIM, calculations, simulation and verified deliverables. Use for MEP project execution across electrical, HVAC, lighting and plumbing.
---

# building-services-design

Read the project brief and assignment-specific instructions first. Preserve originals; create a new project and run directory. Do not reuse a previous course's assumptions as measured inputs.
Use ../mep-requirements/SKILL.md for intake. Select ../mep-electrical/SKILL.md for electrical calculations and CAD overlays, ../building-energy/SKILL.md for thermal/energy analysis, ../mep-ifc-authoring/SKILL.md for supported IFC4 MEP envelopes and topology, ../mep-network-analysis/SKILL.md for prescribed-demand circular tree pressure budgets, or ../mep-lighting-analysis/SKILL.md for IES-backed Radiance sensor illuminance. For other domains, inspect available tool capabilities and define explicit domain acceptance before authoring; absent tools are an implementation gap, not a successful design.
Maintain a common space/equipment/system/circuit identity across geometry, analysis and reports. Capture units, reference coordinate system, provenance, assumptions, applicable code editions and exact clauses/tables. Never combine incompatible code editions silently.
Iterate design using computed results. Use ../mep-delivery-check/SKILL.md before delivery. Report implemented and verified capabilities separately from pending integrations. The repository CLI is a deterministic tool for the electrical slice, not a replacement for your reasoning or a general MEP solver.

## Tool orchestration
Use docs/WORKFLOWS.md and the `bsa.workflow` module to execute the source-linked plan. Supply engine paths explicitly through CLI arguments, never executable commands from a requirement document. Tasks may use only registered adapters. Review workflow.json for every task's narrow execution scope and pending requirement acceptance; aggregate tool success is not full design approval. Missing engines remain pending rather than being simulated by fabricated results.

Record delivery reviews separately using docs/DELIVERY_REVIEW.md and `bsa.delivery`. Pin the exact source plan/run report, preserve every requirement and attach actual artifact/image hashes. The host agent may record observations after inspecting evidence; absent data remains pending. A complete review record is not automatic proof of semantic engineering completeness or professional acceptance.
