---
name: mep-delivery-check
description: Audit building services models, drawings, calculations, CFD evidence and reports before delivery, including missing, incorrect or displaced connections after layout changes.
---

# mep-delivery-check

## Verify connections and placement after a layout change

Use this review for suspected gaps, wrong connections, misplaced equipment or
revised routing. Bind the adopted source layout, equipment and port identities,
expected connections and final artifact revision first. Record drawing units and
coordinate transforms. Keep intentional open ends, schematic continuations and
cross-sheet pairs explicit. If the expected relationship or position lacks a
source, leave that check unresolved.

1. **Check identity and topology.** Extract the actual pairs from the saved
   artifact, then compare with the expected pairs by stable identity. Flag
   missing, extra, duplicate and wrong-peer connections, including across sheets.
   Counts and total flows can agree after a wrong-peer swap. A crossing or
   visually touching line does not establish either endpoint's identity.
2. **Check geometry and placement.** Compare each changed component's position
   and orientation with the adopted source and check both ends of each affected
   connection. Measure endpoint displacement in common coordinates. For a
   physical IFC joint, check port ownership, world positions, opposing frames,
   profile dimensions and material contact wherever the supported method covers
   them. For grid-aligned equipment, use the adopted ceiling grid and compare
   each saved symbol centre with its assigned eligible tile centre. Check tile
   eligibility and footprint against the layout requirements where specified.
   When the source includes allocation areas, also check each centre lies
   in its assigned area. Match to actual closed tiles of the declared size
   inside the adopted boundary, reject ambiguous tile matches and verify
   exclusive use when one device per tile is required.
   Recheck the connection at the new centre or specified port. Keep clearance
   findings separate. Record the comparison tolerance and
   its basis. A numeric matching tolerance is not a construction allowance.
   For a planar obstruction review, bind each obstacle to its saved source
   outline. Recheck the final nominal duct footprints, flex centrelines and
   moved device symbols against that inventory. Record the tested pair counts
   and keep open outlines, missing obstacles and unknown elevations unresolved.
3. **Check the revision as delivered.** Re-read the saved IFC and the DXF
   exported from the actual reopened DWG. Use the supported independent checks
   below, then inspect the actual plot for ambiguous crossings, gaps and
   continuation labels. Record evidence tied to the exact source and artifact
   hashes. Reconcile schedules and calculations affected by the move, including
   route lengths or fitting geometry even if flows and topology are unchanged.
   Compare expected edits and affected neighbors with the previous verified
   revision to detect unintended moves or lost links.

For a supported planar VAV layout with workflow evidence, use
`bsa delivery verify-terminal-connections` or MCP `bsa_verify_terminal_connections`
with the exact plan, run, native task and four scoped layers. Follow
docs/AIR_TERMINAL_DRAWING.md. The review inherits the reopened drawing and the
matching allocation, sizing and rigid binding. A native save/reopen pass only
confirms the declared drawing round trip. Read the terminal correspondence result
before relying on group membership. Use the reported terminal/VAV IDs, DXF handle
and endpoint coordinates to locate a failed line in the saved export.
For revision review, compare `rigid_sections` by section ID and match the
coordinates by node ID in a common drawing frame. Check `saved_from_m`,
`saved_to_m` and `saved_plan_length_m` to detect both translation and
length change. Recheck affected branches and use each flex route's two
reported gaps against `correspondence_tolerance_m`. Carry a changed
plan length into a calculation only when its source and scope support it.

For a configured HVAC package, enable the terminal review when that inherited
scope applies. Inspect the saved package using `bsa delivery inspect-hvac-package`
or MCP `bsa_inspect_hvac_project`. A `blocked` terminal review retains diagnostic
artifacts and suppresses the design-report HTML/PDF. `not_configured` leaves
terminal assignment unverified by this gate. `passed` covers scoped planar
correspondence. Independently review the plot and remaining delivery requirements.

For a three-phase calculation schematic, read `drawing.json` and compare
`dxf_bus_contacts` with `native.bus_contacts` when a native DWG is required.
For a read-only recheck, use `bsa delivery verify-three-phase-contacts
<project.json> <study-directory> <saved.dxf>` or MCP
`bsa_verify_three_phase_contacts` with the same three inputs. For native
evidence, select the DXF exported from the reopened DWG and retain its hash.
Match each circuit ID and declared pair to the saved drawing, then inspect
the measured gaps in drawing millimetres. Investigate a disconnected circuit,
ambiguous pair or contact with an undeclared bus before supplying the sheet.
Use the reported line and bus handles to locate a contact with an undeclared
bus. Review the native PDF for readable phase rows and clear connections.
The schematic geometry and paper scale cover drawing verification only.

For supported physical IFC joints use
docs/INTERFACE_CONTACTS.md. For system sheets spanning multiple pages see
docs/CURRENT_SYSTEM_DRAWINGS.md for source-pair and cross-sheet reconciliation.
These routes cover different aspects of the review. For unsupported geometry,
record the coverage gap and any individually verified observations.

Make failures locatable. Record the sheet/view, component or port IDs, expected
and observed peer or coordinates, measured difference where applicable, and
artifact evidence. Keep untested interfaces and failed checks open in the
delivery review. A successful repair requires a fresh check of the saved result.

For IFC revisions with a documented coordinate translation, pass the same
baseline IFC, alignment file and metre limits to `ifc-port-bcf` and
`ifc-port-bcf-verify`, or their MCP equivalents. Confirm that the alignment
is tied to both model hashes. Check for residual port movement in aligned
coordinates and locate findings in the current model coordinates. Read the
IFC review status and measured relationship count even when the BCF is empty.
See docs/REUSE_SURVEY.md for the supported comparison and replay evidence.

For an existing verified native HVAC workflow, use bsa.vav_schedule run/verify
per docs/VAV_SCHEDULE.md to deliver a bounded group connection table. Reconstruct
native membership/endpoints and inherited maximum/minimum flows; require actual
DWG reopen and actual PDF inspection. Straight XY lengths remain lower bounds,
not installed flex length or product/ADPI/regulatory acceptance.

## Review CFD evidence

Resolve case inputs against their purpose and source. Use the experiment's
geometry, openings, fire and sensor locations for experimental comparison.
Record conflicts with teaching examples and bind each accepted interpretation
to the case. Keep experimental cases and design scenarios identifiable in the
run matrix, with sensitivity runs linked to their paired baseline. Leave
ambiguous case counts unresolved.

Track native solver completion, comparison with experimental measurements,
mesh and model sensitivity, and design criteria as separate checks. The FDS
probe in `docs/REUSE_SURVEY.md` checks saved output for its pinned case. For an
experimental comparison, reconcile saved device IDs, coordinates, units and
sampling windows with the source measurement locations and time basis before
calculating errors. Identify digitized quantities and their precision. A fit
to the same measurements is dependent evidence. For mesh, SGS or model constant
comparisons, record the intended change, hold the other relevant inputs fixed
and compare the same observations and averaging windows across runs.

For a saved OpenFOAM fixed-step steady segment, use
`bsa openfoam-history-review` or MCP `bsa_review_openfoam_history` with the
explicit project, matching patch histories, and declared source and observer
basis. Read flow, mass balance and pressure stability separately. For saved
physical-time pressure histories, use `bsa openfoam-pressure-review` or MCP
`bsa_review_openfoam_pressure`. Bind the pressure definitions and keep the
selected restart segment and exact time window from `docs/OPENFOAM_TRANSIENT.md`.
Treat steady
window stability, grid/domain sensitivity and experimental agreement as distinct
evidence when assessing a pressure claim.

For smoke-layer acceptance, record the adopted interface definition, evaluation
locations and time window, and treatment of weak stratification or temporary
excursions. Keep cases with missing criteria pending. Tie figures and metrics
to the saved input deck, solver version and native result files.

## Reconcile the released package

When a submission folder contains copies, use its handover record and adopted
scenario to identify the canonical report, drawings, native models and
schedules. Rehash the actual copies and compare hashes where copies are intended
to be byte-identical. Check the expected inventory, including required template
pages and appendices; inspect the assembled PDF for crops, readable content and
correct figure/table references. For report numbers and drawing callouts, check
selected governing and failed rows against the bound calculation or native
exports. Keep supplementary cases clearly identified so their values do not
replace the adopted values in the report, schedules, or drawings.

When a release has several review receipts, make one index for the exact
submitted revision. Rehash the current sources, artifacts and receipts,
then cross-check the hashes each receipt claims. Carry unresolved checks
and observed exceptions into the index alongside the checks completed.
If the submission is a ZIP, test the archive and rehash its actual
members against the verified loose files. Check the expected member list
and flag duplicate or unexpected members before relying on the archive.
Use `bsa delivery verify-archive <archive.zip> <sha256-manifest.json>`
or the read-only MCP tool `bsa_verify_delivery_archive`
for a flat JSON mapping of exact in-archive file paths to independently
recorded lowercase SHA-256 values. The verifier reads member bytes in
place and does not extract the archive.

For every released DWG, compare the exact file hash with the native
reopen and plot receipt. A matching schedule or PDF can confirm that
artifact's identity while the DWG itself still needs its own check.
Require a fresh saved-DWG reopen and plot review if the released DWG
hash differs from the verified revision. In a grouped outlet schedule,
check each terminal ID appears exactly once and reconcile maximum and
minimum group flows against the same released coordinate table, allowing
only its documented display rounding.
When rechecking the released supply drawing, independently match terminal
symbol centres to the coordinate table, VAV symbols to unique labels, and
each native flex line's two endpoints to the resulting symbol identities.
Record the matching distance and reject ambiguous matches. Recompute the
group minimum and maximum straight lengths before comparing the displayed
schedule. Keep the label-association distance separate from the endpoint
matching tolerance.
For a declared single-source rigid duct tree, match each native line
to the verified section binding by both endpoints. Check that adjacent
sections share the declared node, every section is used once, and all
terminal groups are reachable from the root. Sum the unrounded released
terminal flows upstream and compare each section with the sizing CSV.
Identify this as a topology and flow-accounting check for the declared case.
When an outlet move changes a directional throw check, reconstruct the
directional distance from the released centres and adopted boundaries.
Track which boundary or eligible facing outlet governs each direction and
recompute the throw at every declared flow case from the adopted curve.
Keep the individual out-of-interval rows visible in the report and tie
their review to the declared classroom or project criterion.
For a released drawing table, recover rows by the saved cell positions
and require a unique row ID. Compare every cell to its source CSV when
the table is small enough to exhaustively check. Reconcile corresponding
report rows using the display precision of each artifact. Record coverage
as row and cell counts so a sample check remains identifiable.

When workspace reorganization changes artifact paths, retain the original
receipt and use an explicit relocation index to find the current file.
Verify the current bytes against the original receipt before reusing a
saved reopen, native calculation or plot result. Treat a path that cannot
be resolved or a hash mismatch as unresolved. Follow each documented move
through subsequent archive renames before marking a path missing. Report
current delivery copies and historical migration records separately, with
matched, missing and changed counts for each audited set. For adopted and comparison
models, bind each approved scenario to its own saved native model, raw
calculation output and report claims.

Determine the review stage from the artifacts present. Requirements notes,
extracted brief pages and reference downloads support intake. Simulation
review requires an executed model, saved outputs and case-specific checks.
An empty workspace provides no project evidence. Record missing stages
before assigning a delivery status.

When an audit flags a conditional engineering result, trace the controlling
assumption or manufacturer quantity to its source. For electrical protection,
for example, verify that a device operating characteristic came from the
applicable protection basis. A calculated conductor or ring-leg current cannot
stand in for that characteristic. Preserve a conditional sizing result and
state any unresolved device or installation evidence in the released report.

After recording actual scoped observations, run a fresh delivery audit and use
its `review_agenda` to select remaining source requirement reviews. Null means
the audit is invalid, not that work is finished. Keep every returned dependency
and input blocker; scoped manual passes do not authorize downstream execution.
Use workflow_status separately for execution recovery. Read docs/DELIVERY_REVIEW.md.

For closed GUID-linked source-network outlines, ifc_native now supports scoped
planar zero-width LWPOLYLINE contours per docs/NATIVE_NETWORK_CONTOURS.md. Require
actual save/reopen/export, unchanged geometry/identity and fixed-scale PDF review.
Keep standalone visual-review receipts separate from producer pending states;
this does not accept installation detail, products or complete engineering.

For a selected source elbow backbone with failed native clash evidence, use
bsa.duct_coordination_diagnosis per docs/DUCT_COORDINATION_DIAGNOSIS.md. Inspect
unique pairs and unresolved source-node actions; linked contacts and source
adjacency never automatically waive raw failures or prove installation fit.

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
