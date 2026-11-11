---
name: building-services-design
description: Orchestrate building services assignments from a brief and source drawings to editable CAD/BIM, calculations, simulation and verified deliverables. Use for MEP project execution across electrical, HVAC, lighting and plumbing.
---

# building-services-design

For the first executed modular boundary,use bsa.modules with versioned request/
result and common box-space contracts in docs/MODULES.md. Select the trusted
MOOSAS provider and pass upstream/dependency locations as host arguments,never
document commands. Preserve disabled/unavailable/failed results and verify_result
source/artifact checks. Another real provider and DAG replacement/disable
propagation are still pending;mock dispatch and spatial exchange do not complete
the modular multi-discipline goal or establish simulation readiness.

Read docs/GOAL.md,docs/MODULAR_ARCHITECTURE.md and docs/MOOSAS_MODULE_MAP.md for
the user-authorized modular priority. Keep public contracts/orchestration separate
from application,performance and jurisdiction providers. Prefer direct pinned
MOOSAS geometry/space/exchange/analysis reuse where compatible;preserve existing
verified domain adapters and failed upstream trials. Develop the real exchange
contract/provider vertical slice before more course-specific helpers. Contract
plans do not prove implemented replacement or complete engineering acceptance.

The requested outcome is automatic preparation of complete models,calculations,
analyses and drawings for the user to inspect and use. Report progress against
artifact completeness and verified capability. Do not describe portal submission
as the user's goal or as the missing automation milestone. Authorized course
portal access in this project is for retrieving source material.

For domestic-water or sanitary-drainage demand, route to ../mep-network-analysis/SKILL.md and docs/PLUMBING_DEMAND.md. Distinguish supply loading units, independent identical-appliance probability and wastewater DU arithmetic; the available methods do not infer mixed-fixture supply tables. For Hong Kong drainage, also use ../mep-regulations/SKILL.md and docs/HK_DRAINAGE.md: workflow drainage_connections checks declared restricted-floor connections, then drainage_stack_demand inherits that exact individual inventory with depends_on and a sourced DU/use basis. Require pass before intended downstream tasks. Unknown full-stack inventory or routing remains pending even if the limited floor check passes. Preserve real survey, separate-pipe/building demand, stack/vent sizing, saved CAD/BIM correspondence and drawing/report requirements; these numerical checks do not complete a plumbing assignment.

For native RVT workflows use ../mep-revit/SKILL.md. It routes installed-host verification, native pipe/fitting inventory, original-request revision checks and workflow gates. Current native creation remains compile-only; preserve connected-system, real analysis, saved-reopen and drawing requirements instead of substituting a synthetic diagnostic report.

For a scoped equal-bore tee assembly, route to ../mep-ifc-authoring/SKILL.md and docs/IFC_TEE_TRIAL.md. Registered workflow kinds tee_assembly and tee_losses provide saved geometry and inherited signed-coefficient diagnostics. They support a sourced rigid placement but do not complete a branched hydraulic design or drawing deliverable. Preserve those remaining assignment requirements explicitly; select other verified tools or implement the missing integration rather than narrowing the brief to the example.

Read the project brief and assignment-specific instructions first. Preserve originals; create a new project and run directory. Do not reuse a previous course's assumptions as measured inputs.
Use ../mep-requirements/SKILL.md for intake. Select ../mep-electrical/SKILL.md for electrical calculations and CAD overlays, ../building-energy/SKILL.md for thermal/energy analysis, ../mep-ifc-authoring/SKILL.md for supported IFC4 MEP envelopes and topology, ../mep-network-analysis/SKILL.md for circular tree budgets, fixed-speed pump analysis and EPANET static-head water graphs, or ../mep-lighting-analysis/SKILL.md for IES-backed Radiance sensor illuminance. Keep each network pressure/geometry contract distinct. For other domains, inspect available tool capabilities and define explicit domain acceptance before authoring; absent tools are an implementation gap, not a successful design.
Maintain a common space/equipment/system/circuit identity across geometry, analysis and reports. Capture units, reference coordinate system, provenance, assumptions, applicable code editions and exact clauses/tables. Never combine incompatible code editions silently.

For jurisdiction requirements use ../mep-regulations/SKILL.md. Hong Kong is the first implemented region, with separately pinned electrical voltage-drop, office lighting LPD, supported HVAC design-condition and air-conditioning water-piping modules. Record scope/edition decisions and official-source evidence; do not inherit the completed coursework's basis. Use shared-source calculation bindings where supported and explicit requires_pass prerequisites for relevant authoring tasks. Preserve every unimplemented regulatory requirement in the matrix; supported checks cannot establish whole-project compliance.
Iterate design using computed results. Use ../mep-delivery-check/SKILL.md before delivery. Report implemented and verified capabilities separately from pending integrations. The repository provides scoped deterministic adapters around native engineering engines. Select the adapter whose physical assumptions match the assignment; no adapter represents a general MEP solver.

## Tool orchestration

For reviewed diffuser pressure tables,include --terminal-performance with the
source-pinned settings in hvac_package or hvac_project create. The optional stage
inherits the current single terminal lookup and places separate pressure/NC
evidence in the package index. Read docs/TERMINAL_PERFORMANCE.md. Preserve source
and acoustic conditions;static and total pressures are separate,NC is not
interpolated,and neither this stage nor its successful execution completes fan
duty or room-noise acceptance. Omitted stages remain omitted.

Before recording scoped numerical acceptance for a saved-native duct schedule,
use bsa.duct_schedule_check as described in docs/DUCT_SCHEDULE_CHECK.md when its
source contract matches the project. Reuse the exact native/sheet/schedule ancestry;
retain original requirements and physical/source/chart-reading gaps. Algebra and
candidate-ranking success may support only the examined numerical subrequirement,
not original complete sizing or drawing acceptance.

For repeat runs of a reviewed HVAC project, use bsa.hvac_project create to pin
the plan, discovered sources and selected package reviews, then run the saved
configuration with explicit host font/AutoCAD arguments. Read docs/HVAC_PROJECT.md.
Changed or omitted source inputs reject; do not edit hashes merely to accept an
unreviewed change. Reuse hvac_package evidence and preserve every original
engineering requirement. One-command settings replay is not raw-brief design
automation or delivery acceptance.

For a reviewed single-source HVAC package that needs whole-tree path coverage,
pass --system-paths-native-task with the exact declared duct_sheet_native task ID
to bsa.hvac_package. It executes the new native workflow first,then runs the
source-bound nominal path postprocessor and includes its report/errors in the
package. Read docs/HVAC_PACKAGE.md. Omitted checks are not passed;review failures
remain explicit. The stage retains full pressure/fan/physical acceptance pending.

After a completed passing native-sheet workflow,use bsa.duct_system_paths with
the exact source plan,workflow,native task and a new output directory to inspect
the entire original supply tree. Read docs/DUCT_SYSTEM_PATHS.md. Preserve every
original requirement and leaf boundary;do not infer downstream diffuser/flexible
connections. Its untrimmed source-centreline friction baseline is not a physical
straight loss,complete pressure bound or fan duty. Keep parallel paths separate
and retain unresolved finite fittings,trim,products,boundaries and acceptance.

For pending duct_fitting_data,read the source-bound diagnosis action's
engineering_data_requests and data-requests.json (docs/DUCT_FITTING_DATA.md).
Preserve every native path,its saved construction/source classification and
available reference pressures. Keep original upstream assignment requirements
and states distinct from current local affected-task links: the original context
does not mean all requirements depend on that fitting or are now accepted.
Resolve actual source/support/physical-review needs,then execute a new study;
never invent coefficients/products or replace pending acceptance with a queue.

Before applying a fitting example to a real supply layout, run
bsa.duct_junction_review on the exact passing native-sheet workflow, or include
--junction-review-native-task in the HVAC package. See DUCT_JUNCTION_REVIEW.md.
Use its source-bound node incidents, nominal sizes, angles and centreline lengths
to identify unequal tees, bends, transitions and multi-branch gaps. These are
connection requirements, not manufactured fitting dimensions or available trim
lengths. Preserve missing end stations, installation roll/elevation, products and
loss data. Do not replace unequal branches with the equal-section tee fixture.

For nominal-width planar obstacle screening in an HVAC package, use --plan-clearance with the inherited native-task/obstacle/coverage settings in docs/DUCT_PLAN_CLEARANCE.md. This reviews the same saved native sheet and sizing result; replacement geometry is forbidden. Keep open outlines, missing walls, outer-envelope/fitting dimensions and elevations in coverage. A clear tested projection stays review_required and cannot replace finite3D clash, installation, code or full delivery acceptance.

For repeated HVAC studies, use the independent public example at examples/hvac-package/README.md to understand the input contracts, then derive each real project from its own sources. `hvac_package` accepts `--terminal-review` for inherited saved-native connection checks and `--adpi-settings` for a pinned criterion document and applicability facts. Configuring these stages retains their results and errors in the package index; generating a report does not clear pending/inapplicable ADPI. Read docs/HVAC_PACKAGE.md and docs/ADPI_BASIS.md before selecting criteria. Allocation `references` binds actual source-document bytes to the workflow; a source string alone cannot detect document changes.

When classroom material supplies a historical handbook table, retain its cited edition, load range, diffuser category and installation conditions together. Do not silently substitute a newer table. Distinguish rule-of-thumb total cooling times approximate SHF from verified room sensible load. For L, distinguish an actual wall or aligned opposing jet from a Voronoi boundary toward an offset terminal; unresolved interactions remain pending. An alignment change requires fresh allocation, maximum/minimum lookup in every affected direction, containment and downstream connection/sizing checks. Retain unselected trials rather than moving terminals merely to clear an interval.

For a reviewed single-system HVAC plan, use `python -m bsa.hvac_package <plan.json> --out runs/<new-package> --font <installed-font.ttf> --autocad <accoreconsole.exe>` as described in docs/HVAC_PACKAGE.md. It composes calculation/drawing execution, dependency diagnosis, a pending delivery review, and numerical HTML/PDF reporting. Read package.json and diagnosis.json to resolve failures; exit 2 and design_accepted=false retain outstanding acceptance. This command needs an interpreted plan, not just a raw brief. Render and inspect the actual generated PDFs, and complete source/ADPI/physical/regulatory review before presenting submission-ready work. Do not reuse private coursework assumptions for another assignment.

For HVAC coursework, use `mep-network-analysis` to build a source-classified `air_allocation` producer, then `terminal_throw` and `duct_schedule` consumers with `depends_on` on that producer. Omit duplicate consumer flow/turndown inputs; explicit terminal membership binds the supply tree. Duct sections may screen sourced candidate dimensions, retaining failures. Read docs/AIR_ALLOCATION.md and docs/DUCT_SCHEDULE.md for the actual contracts. For an existing single-line sheet, docs/DUCT_SHEET.md provides source/centreline/TEXT-bound schedule updates; chain `duct_sheet_native` to that producer for fresh AutoCAD save/reopen/scaled plotting. Actual plotted-page review remains separate from machine execution. Keep requirements for original sources, ADPI, routing, jurisdiction rules and final CAD/report acceptance alongside calculations; successful numerical tasks do not accept those requirements.

For source-native TCF graph research, workflow tcf_fan_research inherits a rectangular native producer and takes pdf/extraction/basis. Use explicit --pdf2plot-python at CLI level; never a plan executable. Require sourced inlet pressure/speed, native source speed order and all artifact checks. Missing runtime remains pending without output. Numerical endpoint success cannot clear this research-only pending task or downstream acceptance; use diagnosis actions to preserve unresolved source/manufacturer/installation/hardware requirements. Read docs/RECTANGULAR_FAN.md.

Use diagnosis.json `actions` as a source-bound, deduplicated recovery queue. Each root includes its recorded scope, evidence, input blockers, affected tasks and full affected requirement records. Resolve actual source/runtime/adapter issues, then execute a new run; this queue does not infer engineering causes, select repairs, resume tasks or approve requirements. Keep independent manual-review roots visible. Add --review <new-file-outside-run.json> to the unified workflow command to prepare the pending full-requirement review in the same invocation.

For one invocation of an already reviewed plan, use `python -m bsa.cli workflow <plan.json> --out runs/<new-run>` with explicit engine flags as needed. This reuses the existing executor and source-bound dependency diagnosis, saving `workflow.json`, `index.html` and `diagnosis.json`. Read the diagnosis before recovery. It does not interpret a raw brief, auto-repair tasks or replace delivery review; retain missing-engine/manual-review exit 2 and design acceptance false.

For bounded site drainage preparation, read docs/SWMM_TRIAL.md. Workflow kind drainage_input takes a source-linked project and emits editable SWMM input only. Use examples/drainage-preparation/plan.json as a synthetic planning example: native hydraulic simulation and engineering review are separate unresolved requirements. SWMM's native DLL is currently blocked by host policy; do not substitute preparation_pass for continuity, capacity, surcharge or Hong Kong compliance. Building sanitary-stack, vent and fixture-loading design remain unsupported by this adapter.
Use docs/WORKFLOWS.md and the `bsa.workflow` module to execute the source-linked plan. Supply engine paths explicitly through CLI arguments, never executable commands from a requirement document. Tasks may use only registered adapters. Review workflow.json for every task's narrow execution scope and pending requirement acceptance; aggregate tool success is not full design approval. Missing engines remain pending rather than being simulated by fabricated results.

Record delivery reviews separately using docs/DELIVERY_REVIEW.md and `bsa.delivery`. Pin the exact source plan/run report, preserve every requirement and attach actual artifact/image hashes. The host agent may record observations after inspecting evidence; absent data remains pending. A complete review record is not automatic proof of semantic engineering completeness or professional acceptance.

When execution leaves failed or pending tasks, run `python -m bsa.workflow_status <plan.json> <run-directory>` before planning recovery. It verifies source/run correspondence and artifact integrity, maps requirements to evidence, and traces declared dependencies to upstream action tasks. Inspect each root task's recorded scope and actual evidence; the dependency graph does not diagnose an engineering cause. Fix the source, adapter or missing runtime as supported by that evidence, then execute into a new run directory while preserving failed attempts. An exit code of 2 with valid JSON means execution remains unresolved; an error without JSON means the evidence could not be validated. Do not treat the command as a resume operation or edit recorded statuses to clear blockers. Passing tasks still need complete requirement review.


For saved circulation pump iteration, follow docs/SELECTED_PUMP_IFC.md: water_coordination â†’ circulation_pump_design â†’ selected_pump_ifc â†’ ifc_circulation_checks and ids_check. Read ../mep-network-analysis/SKILL.md for the catalogue and hydraulic contract. Inherited model/selection inputs cannot be replaced. This chain updates curve properties, not manufacturer pump geometry. Keep physical clash checks and native drawing/plot review as separate required tasks when the brief calls for drawings; the synthetic runner alone is not a full assignment deliverable.

Before implementing a missing capability, consult docs/REUSE_SURVEY.md and test an appropriate pinned upstream CLI/library/MCP. Reuse the existing engine and add only necessary provenance/binding/workflow glue. Record actual execution and licensing separately from advertised capability. OSE/FreeCAD's native Part import was blocked by host application control (docs/OSE_FREECAD_TRIAL.md); do not route production fitting work to that unexecuted probe or bypass host policy.


For inspecting an existing IFC inventory or adding source-backed text metadata to an existing pump, use ../mep-ifc-mcp/SKILL.md. Its isolated official server has executed query/property evidence; inventory is workflow kind ifc_query with an explicitly supplied isolated runtime; source-bound pump text editing is workflow kind ifc_metadata and revised models require fresh downstream checks. Route physical modeling, calculations and drawings to existing domain adapters. The local 0.9.0 geometry kernel is blocked by application control, so advertised MCP plotting must not be selected as an available delivery path.

When requirements include cable-product bend constraints, route to mep-electrical and docs/CABLE_BEND_LIMITS.md. Schedule three_phase_bend_limits on the intended numerical producer and exact saved IFC/binding/basis, then require its pass before drawing. Product/source/installed-or-pulling identity, diameter and radius datum must be explicit; unknowns remain pending. Do not substitute geometry validity or numerical convergence for product selection, source interpretation or complete regional acceptance.

When electrical geometry must coordinate with building/MEP obstacles, use docs/CABLE_COORDINATION.md and three_phase_coordination as a same-model prerequisite before drawing. Preserve native solid/clearance and coverage failures; the earlier ideal-node shared-end fixture fails without a real sourced interface and must not receive an invented waiver. Generic source-box staging is available through ifc_obstacles, with a deliberate new IFC revision/binding/fresh study. Declared 30 mm demo targets are not code limits.

For concept daylight input conversion use docs/HONEYBEE_SCENE.md and bsa.honeybee_scene with an explicit isolated Honeybee runtime. It rechecks native facade/source and creates saved HBJSON, upward grids and punched Radiance polygons. This is not annual simulation; keep solver_ready=false while site/ground/weather/detailing and validated runtime/recipe are missing. Do not substitute electric-light illuminance or generated sensor files for sDA/ASE/DGP.

Honeybee input conversion is now unified workflow kind honeybee_scene: inherit an earlier concept_facade, supply only basis and explicit CLI --honeybee-python. Reject source/runtime overrides from plan content. Missing runtime stays pending without outputs. Retain original engineering work packages, native producer/source pins and full scene/annual acceptance gaps; conversion pass is not a performance result.
