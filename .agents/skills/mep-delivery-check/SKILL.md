---
name: mep-delivery-check
description: Audit building services models, drawings, calculations and reports against source requirements before delivery, preserving unresolved engineering and visual checks.
---

# mep-delivery-check

For recorded PDF output, use bsa_render_artifact_page after bsa_artifact_index
per docs/MCP_ARTIFACT_PAGES.md. Actually inspect every required page, retain
workflow/PDF/image hashes and separate scoped observations. A rendered image
does not establish native reopening, print scale or full design acceptance.


For MCP delivery review, use bsa_delivery_template and bsa_assess_delivery per
docs/MCP_DELIVERY.md. Read the artifact index requirement/evidence matrix and
actual saved artifacts first. Save explicit observations in a fresh review;
unexamined obligations stay pending. Never treat one Boolean flag or a reviewer
assertion as whole-requirement engineering approval.


For conditional duct-schedule presentation,read every bound section/field and drawing label from the saved DXF and the actual native-reopened export;independently reconcile Q/(width*height),units and displayed rounding. Inspect the actual PDF separately. A source/native match does not accept friction-method applicability,physical geometry,routing or installation. Preserve unrelated sizing/ADPI blockers and original requirement coverage. See docs/DUCT_SHEET.md.

For ifc_views annotation_mode:keyed-schedule,verify source GUID-number/tag and
full parameter-row correspondence,exact saved text position/height/width/rotation
and conservative graphic nonintersection. Both view_tags/route_annotations helper
pins must be present. No leader routing or physical clearance is inferred.
Inspect every actual plotted page for ambiguity/clipping/legibility;source/native
and graphic checks do not accept fittings,equipment,installation or full design.
See docs/IFC_VIEWS.md and the retained failed versus corrected native trials.

For modular workflows inspect module_selection and nested results per
docs/MODULES.md. Delivery context reconstructs selected provider method inputs
and checks actual provider/disable correspondence. workflow_status retains
module_state and distinct disabled/missing-runtime actions with affected
requirements. Valid host overrides must use the selected inventory rather than
only the default provider's files. Pending module acceptance and preparation-only
thermal results cannot establish simulation or full engineering acceptance.

For HVAC reports with an ADPI review,check the rendered applicability/evidence
section against the source-pinned review. The reporter must reconstruct current
settings/lookup facts rather than copy a success flag. PDF paragraph checks retain
missing facts,scope and source notes alongside the numeric rows;they do not prove
the declarations or actual ADPI. Keep source-workflow requirement states distinct
from the separate effective delivery review. Read docs/HVAC_REPORT.md.

For tee_assembly and tee_losses, read docs/IFC_TEE_TRIAL.md. Inspect assembly-checks.json, the actual saved IFC and tee-loss.json against the original specs/basis. Separate saved geometry/identity/connection checks from coefficient evaluation; workflow pass is not proof of pressure balance. Keep BIM-viewer review, actual products/joints, network balance, fitting reference stations/friction, native drawings and applicable code checks pending whenever required and unverified. Retain synthetic labels and sourced rigid placement; coefficient values are signed and referenced to combined inlet velocity. Use the ordinary separate delivery template/audit rather than marking all requirements accepted from two passing tasks.

For tee_pressure, tee_split and tee_selection, inspect pressure boundary semantics, bracket/table coverage, residual, net fitting dissipation and source capacity separately. Selection must retain rejected candidates and the selected rerun under unchanged common duty. Verify the delivered IFC and drawing use that selected candidate. On the actual plotted page check callout-to-schedule correspondence, bore/OD, saved-port overall/reach dimensions and scope note. Numerical/schema/format checks alone cannot establish source authenticity, manufacturer applicability or Hong Kong compliance.

Re-read the requirement matrix and inspect evidence for each deliverable. Check source hashes and provenance, unknown assumptions, code editions, IDs and counts across equipment, circuits, model, diagrams and report.
For preliminary coursework calculations,use docs/COURSEWORK_SCOPE.md to preserve
the requested scope and explicit assumption classifications. A supported
rule-of-thumb load review does not verify actual room load for ADPI or accept
layout/product obligations sharing the same source quote. Preserve the original
input issue,source resolution,new producer prerequisites and unchanged full
requirement matrix before recording any separate scoped review pass.
Run calculations and review failures. Validate units and native model semantics. For DWG, reopen in AutoCAD and inspect native entities; separately export and visually review every PDF sheet for scale, clipped content, lineweights and legibility. A successful command or DXF validator cannot stand in for either gate.
For simulations inspect actual engine logs, version, model/weather inputs and result units. Distinguish reproducibility, numerical checks and engineering acceptance.

For jurisdiction evidence use ../mep-regulations/SKILL.md. Check selected packs/editions, official file hashes, actual per-circuit/per-space coverage and unresolved rule inventory. Confirm requires_pass gates refer to the same project sources as their consumers; inspect recorded regulatory_source_bindings for supported electrical/lighting consumers. Byte identity does not establish semantic applicability or arbitrary cross-domain correspondence. Preserve branch protection failures, lighting-performance failures and scoped exceptions separately. Do not relabel regulatory_compliance: not_established as complete conformity because supported_checks_pass is true.

For annual_energy, inspect docs/ANNUAL_ENERGY.md: raw/asset weather hashes and station/site, full 8760/8784 calendar, weather-only environment, warmup exclusion, hourly units/intervals, monthly/annual reconciliation and independent lighting balance. Review per-zone unmet targets and completion.json under docs/ENERGY_COMPLETION.md. The exact pinned executable's initialized flags may have a source-backed explanation; raw flags stay false, and unknown or failed native evidence cannot be cleared. Keep ideal thermal supply separate from lighting/plant electricity; real construction/gains/schedules/weather/HVAC applicability and engineering acceptance remain pending.

For electrical_fault outputs, inspect docs/ELECTRICAL_FAULTS.md: exact circuit coverage, shared route/voltage/breaker identity, coherent minimum/maximum fault cases, device/energy applicability and source/code evidence. A source-envelope numeric pass is conditional; unknown guarantees remain pending. Check CPC thermal and standalone breaking criteria without clearing mechanical minima, other conductor protection, selectivity or full electrical acceptance.

For pump operating points, inspect the explicit fixed terminal-pressure/free-flow boundary, original curve and positive bracket, fluid/regime applicability, signed root residuals, both convergence tolerances, conservative minimum-flow/velocity checks and saved-state rerun. Verify power uses pump-added pressure and explicitly combined wire-to-water efficiency. A converged point can fail capacity; an electrical estimate does not update or validate the electrical project. See docs/PUMPS.md for limits.

For `pump_electrical`, verify explicit electrical/pump/outlet identity, connected source geometry, source/artifact hashes and replay. Compare baseline and operating scenarios, unchanged hardware/other devices, unchanged original IFC entities and saved new properties. Require baseline checks as well as operating checks; keep nameplate/starting/protection, electrical topology and unbound devices pending. See docs/PUMP_ELECTRICAL.md.
The initial CLI manifest proves only its JSON input remained unchanged and its emitted CIRCLE count matches device count. It does not prove all source documents unchanged, correct native geometry, print quality or complete protection design.
Create an acceptance record with pass/fail/pending and evidence paths. Pending required checks mean the delivery is incomplete; never erase them to obtain a green status. Delivery audits also check execution dependency consistency: inspect blocked_by for each requirement. A reviewer assertion cannot clear a blocked manual task, and a passing child with nonpassing required parents is rejected. Recording upstream manual review does not itself execute or authorize downstream tasks.

Use docs/DELIVERY_REVIEW.md and `python -m bsa.delivery template <plan> <run> --out <separate-review.json>` to start a source-bound record; every requirement begins pending. Inspect actual source/artifacts, record scoped findings and hashes, then run `bsa.delivery audit`. Cite original files and bind supplemental render images to their source artifact hashes. Optional Boolean facts only check adapter-reported flags; they do not replace independent math or actual visual review. Do not clear missing engines, failed tasks or unknown engineering inputs through reviewer text. Review records are evidence assertions, not user permissions, credential authentication or automatic design certification.

For saved-IFC schedules/diagrams, inspect drawing.json coverage, excluded classes, profile/port/metadata consistency and DXF GUID/count reconciliation. Compare true and projected lengths, then inspect preview legibility. IFC_DRAWINGS.md documents the limited centreline scope; native plots, equipment/fittings and installation acceptance remain separate gates.

For `ifc_native`, inspect native-verification.json and the reopened DWG export: model handles/counts, IFC XDATA, supported geometry, source hashes and physical PDF reference must pass. Render that run's actual PDF; store its hash and image hash with the visual observations separately, preserving workflow artifact integrity. Equipment/fittings and full installation acceptance remain pending for centreline diagrams.

For `ifc_views`/`ifc_views_native`, require all source segments in every view, explicit end-on symbols, nonzero combined axis coverage, correct true/projected lengths and complete GUID/layer/annotation reconciliation. Each sheet needs its own non-end-on reference, native reopen and physical PDF check. Inspect every actual merged page, including leaders, symbolic/physical size distinction and clipping; preserve render/source hashes separately. Do not use one view or one reference as proof of the entire drawing set. See docs/IFC_VIEWS.md.

For orchestrated projects, run `python -m bsa.workflow verify <run-directory>` before interpreting results. It checks recorded source and task-artifact hashes, not report authenticity or engineering correctness. Compare every acceptance description in workflow.json against its actual artifacts and source paragraph; do not use execution_status as acceptance_status. Record visual and domain reviews separately with artifact hashes.

When IFC coordination is required, inspect docs/CLASH.md and the saved clash.json. Confirm geometry coverage, units, policy sources/tolerances, Boolean checks and all accepted contact exceptions. A source-connected pair is not exempt from solid overlap. For outside_regions mode inspect both directional proofs; legacy pair-minimum exceptions leave non-interface clearances pending. Keep unverified product geometry pending; an empty findings table alone is insufficient.


For BIM information requirements, reuse pinned IfcTester through ids_check as described in docs/IDS_WORKFLOW.md. Require the brief's actual IDS contract and the intended saved model. Prefer depends_on for an in-workflow IFC producer; explicit IFC and dependency cannot be combined. Inspect ids-report.json and ids-check.json: upstream process exit 0 alone is not success, and empty/no-applicable checks cannot pass. Bind required downstream tasks with requires_pass and verify they consume the same model identity. This adapter checks information conformance only; presence of a source string or screening hash does not prove its truth.

For a selected circulation pump, read docs/SELECTED_PUMP_IFC.md. Inspect retained baseline/rejections and selected rerun, stable pump/port GUIDs, selected-template.json, saved selection properties and the fresh rebound. Confirm ifc_circulation_checks and ids_check depend on selected_pump_ifc rather than the original model. Preserve manufacturer/efficiency/motor/NPSH, physical fitting clashes and remaining code checks. The seven-stage synthetic demonstration contains no drawing release and must not satisfy a brief demanding installation drawings or full building-services design.


For plumbing_pump_set, inspect both independent role reports and the common receiving boundary. Require both roles to meet the full sourced tank outflow alone. Downstream network/pump/pipe-rule checks must declare pump_role and record matching role-specific source hashes through their requires_pass ancestry. Review the full set status; a passing duty result cannot clear a failing standby. Installed duplicate equipment, switching/interlocks/isolation, suction/NPSH and full WSD applicability remain separate evidence requirements. See docs/HK_PLUMBING_PUMPS.md.


For allocated HVAC supply-tree tasks, verify consumers inherit the exact current `air_allocation` output; a matching total alone cannot prove per-terminal/per-section correspondence. Check terminal identity, one-time leaf membership, selected candidate dimensions and every failed option. For `duct_sheet` outputs, compare the saved native schedule with the current calculations and verify the bound centrelines, not just text counts. Its saved-DXF pass deliberately leaves native reopening/plot review pending. Inspect the actual newly plotted page, repair visible annotation conflicts, and preserve separate unresolved ADPI, thermal/source, spatial/fitting, fan and regulatory requirements. A fixed-centreline single-line schedule update does not establish 3D or physical-width duct coordination.

For HVAC packages (docs/HVAC_PACKAGE.md), distinguish artifact completeness from design acceptance. Inspect package.json stage_errors and unresolved_tasks, verify the nested workflow, and compare report numerical rows with the same run's allocation/lookup/schedule. The PDF renderer checks extracted numbers but leaves visual review pending. Record actual page inspection outside the immutable package; do not change hashes or task statuses to clear a missing engineering check. The supplied delivery-review.json starts pending for every requirement, including requirements whose numerical task passed.
