---
name: mep-network-analysis
description: Calculate source-linked air/water networks, pump operating points and bounded fixture demand. Use for supported duct/pipe pressure and sizing, sourced pump curves, identical-appliance probability and wastewater DU studies.
---

# Network pressure analysis

For a saved-native water graph,use wntr.ifc-steady with
analysis.water.ifc-steady-graph. module_analysis may inherit module_authoring
with a project/binding-only request;see examples/modular-bound-water-plan.json.
Require exact selected-system GUID/port/connection coverage and derive dimensions
from native hollow profiles. Reject repeated lengths,bores and elevations. Verify
the copied IFC,derived input,binding and raw numerical replay;preserve static head
and signed flow. Source/native agreement does not accept physical nodes,K,products,
clashes,HK rules or a complete design. See docs/MODULES.md.

For declared steady water/circulation graphs,use module_analysis with
wntr.epanet-steady and analysis.water.steady-graph per examples/modular-water-plan.json.
It wraps the existing WNTR1.5.0/EPANET2.2 worker. Inspect native files,raw/report
agreement and source/raw evaluator replay;preserve signed flow and static head
in metres of water. Completed numerical fail blocks required work;worker failure
has no hydraulic payload. Geometry,HK rules,pump electricity and full acceptance
remain unverified through this boundary. See docs/MODULES.md.

For the initial modular air-budget boundary,use module_analysis with
fluids.rectangular-air-budget and a source-pinned analysis.air.rectangular-tree
request. It reuses the existing rectangular_network calculator/fluids1.3.1;
see docs/MODULES.md and examples/modular-analysis-plan.json. Preserve typed units,
raw branch/node results and separate completed/numerical-fail states. Only a
numerical pass may satisfy requires_pass;do not change targets to hide failure.
Declared lengths/K/applicability are not saved-native geometry,fan selection or
full engineering acceptance. Other analysis-provider replacement is unverified.

For saved-native rectangular binding,use fluids.rectangular-ifc-budget with
analysis.air.rectangular-ifc-tree. module_analysis may inherit module_authoring
using a project/binding-only template;the workflow binds its exact IFC and
canonical source. See examples/modular-bound-analysis-plan.json and docs/MODULES.md.
Do not repeat dimensions/elevations or replace the model. Existing source
derivation and saved solid/profile/port/connection reconciliation must pass.
geometry_bound means source/native agreement;installed truth,K,junction physics,
fan selection and complete acceptance remain pending.

For the existing single-path fan consumer,rectangular_fan_operating_point may
depend on a passing bound module_analysis and an explicit total-pressure curve.
Use examples/modular-fan-plan.json and docs/MODULES.md. The network_input artifact
must be declared;do not guess provider paths or repeat network values. Replay
point/trace/targets and the operating-network rerun. Convergence cannot clear
failed capacity;missing sign brackets must not extrapolate. Air power cannot
populate motor electrical input or HK fan-power evidence. Synthetic curves do
not select actual equipment;mechanical/stable/installation/product review remains.

For an explicit planar layout change,use bsa.terminal_layout_revision only when
the original drawing matches the full allocation/tree and ID-label bindings.
Read docs/TERMINAL_LAYOUT_REVISION.md. Preserve rigid/VAV geometry and unrelated
entities,then rerun actual allocation,lookup,section sizing,sheet/native plotting
and connection review in a new plan/package. A translated panel and straight flex
endpoint do not verify installed length,physical ports or ADPI. Retain original
requirements,unrelated gaps and the previous accepted/reviewed baseline.

For explicit diffuser-position alternatives,use bsa.air_layout_study and
docs/AIR_LAYOUT_STUDY.md. Reuse source-classified loads and the reviewed catalogue;
compare full terminal inventories,flow conservation,panel envelopes and cardinal
polygon/aligned-midpoint rays. Off-axis neighbours are not automatically opposing
jets,and allocation cells are not physical jet boundaries. Keep diagnostic ratios
distinct from ADPI applicability. Candidate geometry does not select a design or
update CAD:rebuild source-bound connections,sizing and native plots after actual
position changes,and preserve original studies.

For catalogue pressure operating points after a passing terminal_throw workflow,
use bsa.terminal_performance and docs/TERMINAL_PERFORMANCE.md. Bind the original
document/table/product and inherit exact maximum/minimum flow,without replacement
values. Inspect published Pt/Ps columns and installation notes. Keep static and
total pressures separate;never sum parallel terminals or both pressure columns.
NC stays at exact published flows or as adjacent reference rows,without numeric
interpolation or assumed room-noise bounds. This does not complete fan,room
acoustic,product/installation or ADPI acceptance.

ADPI settings support optional fact_evidence document/hash/locator/note records
(docs/ADPI_BASIS.md). Use them to retain independent sources behind a scoped
interpretation,such as a course's explicit product/table mapping. Evidence never
sets a fact automatically. Keep that mapping within its selected criterion and
edition;room load,L,installation and actual ADPI remain separate. Package and
saved-project inputs must include every supporting document.

For an independent numerical audit of an existing saved-native duct schedule,use
bsa.duct_schedule_check with the exact plan,workflow,native task and a new output
directory. Read docs/DUCT_SCHEDULE_CHECK.md. It checks geometry/flow identities,
all source candidate calculations,stored Colebrook residuals and declared ranking
without another friction solver. Preserve scanned-chart readings,physical source
applicability and full acceptance as pending;residual tolerance is not an
engineering acceptance band. Keep actual and equivalent-round velocities separate.

For whole source supply-tree review after native-sheet execution,use
bsa.duct_system_paths and docs/DUCT_SYSTEM_PATHS.md. It replays the selected
friction method against saved-native centreline/node/source correspondence and
enumerates all original leaf paths. Keep its untrimmed nominal baseline separate
from trimmed physical straight/fitting studies. It cannot establish a pressure
bound,fan critical path,downstream terminal route or accepted whole design.

For external source/manufacturer rectangular fitting tables,use duct_fitting_data
with basis and depends_on on the saved duct_fitting_chain. Read
docs/DUCT_FITTING_DATA.md. Bind exact product/native body/path/reference-port
identities and hash-pinned source documents; native quantities supply the queries.
Null support cells and bounds remain pending,never clamped or extrapolated. Keep
negative coefficients signed and parallel paths separate. A complete numeric
table set or declared applicability/friction note cannot accept full pressure:
physical/transcription/friction/boundary review remains pending and required
downstream consumers must stay blocked. Do not publish licensed/private tables.

Use data-requests.json and the workflow_status engineering_data_requests queue
to acquire missing data. Each unique path preserves saved geometry source and
classification,actual owned-port quantities and affected outlet identities.
Retain the upstream plan's complete requirement context and original states
separately from declared local dependencies. Interpolated results still require
physical review; changed model/source/generator evidence requires a fresh study.

External fitting tables may declare native quantity conditions with explicit
minimum/maximum bounds. Failed conditions stay pending with a null coefficient.
deflection_deg comes from actual inward-inlet/outward-outlet world port axes;
it is not a transition's wall opening angle. Record partial geometric checks
without accepting full method applicability. Follow exact source cross-references:
a supported main-path table does not resolve that fitting's unsupported branch.

For transition sources with a common width/height opening angle,inspect both
native angles and use taper_angle_difference_deg in declared conditions where
appropriate. Do not substitute major_taper_angle_deg for a source's equal-angle
geometry. Bounds used for software alignment are not regulatory or fabrication
tolerances;the source conditions still require explicit interpretation.

For centred rectangular transition source matching,use transition_geometry in
the fresh chain product/data-request records. It provides native taper length,
separate end straights,width/height opening angles and outlet hydraulic-diameter
ratios;these are available as transition-only table quantities. Preserve reversed
flow and mixed width/height change classes. Boolean bore extensions are not
physical length,and a major angle is not both plane angles. Reject unavailable
quantities on tees. Native geometry still needs applicable source/product/regime
evidence;hydraulic diameter alone does not authorize a circular correlation.

For published/manufacturer transition tables,declare transition_flow_change from
the source coverage for the actual path. It must match the fresh native class:
contraction,expansion or mixed_width_height_change. Missing declarations remain
source_applicability_required;wrong ones remain native_condition_failed,with no
coefficient. Do not substitute net area reduction for mixed width/height geometry.
Synthetic controls may omit the source declaration but never establish physical
acceptance. Matching this one guard cannot clear the remaining method review.

Inspect boundary_paths from bsa.duct_chain_analysis before using local pressure
results. Keep inlet-to-outlet paths separate; shared straight contributions must
not be added across parallel outlets. Full pressure and critical_path stay null
until fitting applicability, losses and boundary conditions are established. The
reviewed hvac-pressure0.1.1 wheel is an executed research candidate only: silent
bounds clamping and rounded-tee/two-parallel-side requirements prevent direct use
for the current sharp tee and two-dimension-changing taper case. See
docs/DUCT_CHAIN_ANALYSIS.md; do not install it as an accepted solver.

For the saved source-bound local duct chain, use duct_chain_analysis depending on
duct_fitting_chain; read docs/DUCT_CHAIN_ANALYSIS.md. Inherit every port flow and
air condition from the exact source schedule, and read saved native cross-sections
and separate straight length. Keep actual-port velocities separate from the
equivalent-round friction velocity. The actual16-port case conserves flow and
computes a straight contribution, but eight fitting paths still require applicable
rectangular loss/reference-velocity/friction-inclusion data. Missing coefficients
are null, full pressure is unavailable and pressure-gated outputs remain pending.
Do not substitute circular pipe coefficients, original full centreline length,
zero losses or a finite straight subtotal for complete pressure/fan acceptance.

For fixture demand read docs/PLUMBING_DEMAND.md before choosing a method. Workflow plumbing_demand supports only explicit independent identical-appliance binomial inputs through pinned SciPy; discharge_demand computes supplied K*sqrt(sum DU). Keep supply loading units, discharge units and thermal/volumetric quantities distinct. No automatic mixed-fixture table selection or assumed use probability is implemented. Source-bound scope facts can be true/false/unknown; unknown facts prevent calculation and rejected applicability blocks downstream tasks.

For a Hong Kong stack, read docs/HK_DRAINAGE.md and use drainage_connections followed by drainage_stack_demand with depends_on on that producer and a pinned basis. Individual IDs/counts come from the original connection inventory; DU rates and K come from the basis. Do not supply a replacement project or hand-copied aggregate floor multiplier. Require explicit full-stack inventory confirmation separately from the restricted-floor survey. Direct-manhole fixtures are excluded only from this stack total, not from building demand; unknown/contradictory upper routes remain pending. For applicability and official-source scope use ../mep-regulations/SKILL.md. Capacity/venting, other inflows, real fixture tables and saved-model correspondence still need separate implementation/evidence.

For HVAC diffuser lookup and equivalent-round section schedules, use the registered `terminal_throw` and `duct_schedule` workflow tasks with `project` inputs. Read docs/TERMINAL_THROW.md or docs/DUCT_SCHEDULE.md for the relevant input contract. These adapters reuse pinned fluids; prefer them over private interpolation or friction scripts. Keep the two methods distinct from hydraulic-diameter rectangular network analysis. A passing task establishes bounded lookup or supplied-section criteria only, not topology, fan duty, source applicability or complete design acceptance.

For terminal selection, review the original catalogue configuration and conditions before transcribing and hash-pinning rows. Keep maximum and minimum flow, characteristic length and diffuser classification explicit. Product naming alone does not establish its ADPI pattern category; resolve the manufacturer's classification and applicable room sensible load. Do not automatically use coil cooling allowance times SHF as the room load. Out-of-range lookups remain failures, not clamped endpoint values. A catalogue JSON hash verifies bytes, not the accuracy of transcription or engineering applicability.

When a lecture or design guide gives a typical VAV turndown or a worked room/supply-temperature example, compare it with the actual brief before using it. An explicit project minimum-flow requirement takes precedence over a generic typical value. Treat example temperatures/properties as assumed sensitivity inputs unless project applicability is established. Use fresh inherited allocation/lookup/schedule runs and hvac_compare to retain flow changes and infeasible sections; do not enlarge a catalogue or select the scenario merely to erase a failure. Preserve maximum/minimum-flow checks and unresolved room/ADPI conditions together.

For duct schedules, supply actual rectangular dimensions, explicit air properties and section-specific velocity/friction/aspect limits. `duct_schedule` recalculates supplied dimensions; use `duct_equivalent.select_sizes` only when a reviewed candidate set is available and retain rejected sizes. Source traceability, network flow conservation, geometry and native schedule reconciliation remain separate checks. Preserve course preferences separately from binding regulatory limits; distinguish straight plan flex distance from installed length.

For the reviewed TCF source vector extraction use adapters/pdf2plot/README.md and pinned scripts/bootstrap_pdf2plot.py / scripts/extract_tcf_vectors.py. Preserve six disjoint native LINE paths, source tick/speed labels, unchanged upstream log export and independent reconstruction. Extracted points remain research-only until source/digitization/interpolation uncertainty and operating applicability are resolved; CSV precision checks are not fan-performance accuracy. scripts/check_tcf_interpolation.py reopens the native source and analytically bounds physical-linear versus native log-log segment interpolation; keep this separate from endpoint/source/manufacturer uncertainty and operating-point sensitivity. A small interpolation difference alone cannot release a curve. For research-only operating sensitivity use scripts/run_tcf_curve_research.py; it reopens source points, uses unrounded native coordinates and bounds chord interpolation with independent lower/upper fan solves. Keep synthetic duty/viscosity/K explicit. Pending manufacturer/source/installation uncertainty keeps wrapper calculated_checks_pass=false; never promote endpoint calculation success to product/design acceptance.

For real fan intake, inspect sources/products/tcf-bc-sw-122.json and docs/PRODUCT_INTAKE.md. It is research, not a numeric solver catalogue. Require construction-class speed limits, source/uncertainty-checked numerical points, installation/stable-region applicability and separate real motor electrical evidence before product acceptance. Use fan_mechanical_limits depends_on on rectangular_fan_selection with record/pdf/basis for the reviewed source-specific maximum-speed check. Require it as a downstream pass prerequisite; unknown class stays pending and overspeed fails. Independent pinned-PDF extraction rejects changed record limits. For mechanical-aware ranking declare catalogue mechanical record/pdf/classes with complete candidate coverage per docs/RECTANGULAR_FAN.md. Overspeed excludes a candidate; better-preference unknown class keeps selection pending, while lower-preference unknown does not override a confirmed preferred choice. Selected handoff reconstructs mechanical eligibility. Chart speed lines alone cannot authorize a class. Preserve unresolved quantities rather than digitizing by eye into exact points.

For finite fan-curve comparison use rectangular_fan_selection with an earlier native rectangular producer and sourced catalogue, per docs/RECTANGULAR_FAN.md. Preserve every candidate rejection, declared preference/lexical tie order, exact same route/terminal/K and selected saved rerun. No feasible candidate blocks downstream review. To consume the chosen curve use rectangular_fan_operating_point depends_on on rectangular_fan_selection with no project/curve. Preserve selected_input source/artifact/native checks and fresh candidate/ranking/operating reconstruction; do not trust status flags or rewritten hashes. This selects a curve scenario, not authenticated vendor hardware, electrical power or full Hong Kong acceptance.

For a single level rectangular path with a supplied fixed-speed fan TOTAL-pressure curve, use bsa.rectangular_fan or workflow rectangular_fan_operating_point with explicit project/curve. Read docs/RECTANGULAR_FAN.md. Preserve bounded interpolation/root/flow/velocity/domain checks and saved rerun. Static curves, inferred density/speed correction, electrical power from air power are unsupported. A depends_on on rectangular_network_binding or rectangular_model_design inherits exact saved duct-path geometry/study, rejects replacement inputs and rechecks source/native correspondence before solving; fan equipment itself remains unbound. Free-flow operating results do not replace original design airflow in HK rules. Native fan/product/control/full acceptance remains pending.

For level rectangular straight/finite-90-degree-bend chains, read docs/RECTANGULAR_ELBOWS.md and use rectangular_network_binding. Omit aggregate minor_k when a bend is present; require per-piece sourced excess K above centreline Darcy friction. Preserve exact saved arc length, section-roll/opposed-normal joints and native dimension/K/port checks. No circular fitting coefficient is inferred. Catalogue bend redesign remains unsupported; curved sheets have scoped native evidence in docs/RECTANGULAR_ELBOWS.md; real K/stations, fabrication and full acceptance remain pending.

To propagate rectangular catalogue selection into native source-defined straight ducts, use rectangular_model_design with project/model/binding/catalogue/geometry. Source each option's wall thickness separately; preserve route/K assumptions and rejected spatial choices. Require stable identities, fixed endpoints and fresh native-bound pressure reconciliation. Read docs/RECTANGULAR_AIR_NETWORKS.md; this does not establish physical branch junctions, fan selection, clashes or Hong Kong acceptance.

For source-model bound rectangular straight routes, use rectangular_network_binding rather than manually copying width/height/length into pressure inputs. Read docs/RECTANGULAR_AIR_NETWORKS.md: omit node elevations and segment dimensions/lengths, require exact source port-chain coverage, retain independent saved wall/port checks and pressure failures. It does not revise the model from a catalogue selection or resolve junction/fan/installation/regulatory acceptance.

After rectangular_network_design, use rectangular_network depends_on on that producer and omit project. The consumer reconstructs and verifies the selected source candidate before fresh pressure analysis; replacement inputs, no-feasible selection and changed artifacts block. See docs/RECTANGULAR_AIR_NETWORKS.md and selected-plan.json. This handoff is geometry-free and does not establish spatial, fan or regulatory acceptance.

For bounded rectangular duct sizing, use bsa.rectangular_design or workflow rectangular_network_design with project/catalogue per docs/RECTANGULAR_AIR_NETWORKS.md. Reuse the existing exhaustive finite search and save/rerun the chosen rectangular input. Require sourced width/height/roughness/options, a declared score and explicit fixed-route/local-K applicability across sizes. Preserve no-feasible and unsupported candidates; do not substitute the old circular network/model-binding tools for selected-network.json. Geometry, fan, acoustics/fire and Hong Kong acceptance remain separate.

For level prescribed-flow rectangular air trees, read docs/RECTANGULAR_AIR_NETWORKS.md and select bsa.rectangular_network or workflow kind rectangular_network. Require actual internal width/height, explicit sourced method_basis assertions and local-velocity fitting coefficients. Use actual rectangular area for velocity and hydraulic diameter for turbulent friction; never substitute round-equivalent area or circular laminar 64/Re. Positive Re<4000, nonlevel nodes and unknown applicability are unsupported. This adapter has no saved geometry or Hong Kong-rule binding; retain fan operating point, acoustics, fire/smoke and complete acceptance requirements separately.

When replacing synthetic fitting data with manufacturer inputs, read docs/PRODUCT_INTAKE.md and inspect the source-pinned record under sources/products. Keep nominal size, pipe OD, bore and fitting envelope separate. Equivalent pipe length cannot be inserted as K or converted to the current tee-face contract without sourced reference-pipe/velocity and pressure-station applicability. A research record with unresolved fields is not a tee_selection candidate.

For bounded bore/OD iteration, use workflow tee_selection with catalogue and docs/IFC_TEE_TRIAL.md. Each candidate supplies geometry and loss sources; common duty, placement, topology and solver acceptance cannot change to obtain a pass. Keep all candidate failures and require selected regeneration/re-solve. Selection follows declared preference, not inferred cost. No feasible candidate blocks delivery. examples/tee-trial/selection-plan.json hands the selected IFC/specs to tee_drawing and ifc_native; do not draw the original rejected model.

For sourced complete tee-face coefficients, `tee_pressure` budgets prescribed outlet flows and `tee_split` solves an interior split bracket at fixed total flow with adjustable source pressure. Both inherit an earlier tee_assembly and require basis; tee_split additionally requires control. Read docs/IFC_TEE_TRIAL.md. In split mode, the basis inlet pressure is available capacity and outlet target pressures are exact boundary values; original run/branch flow inputs are replaced. Constant coefficients need a declared interval applicability source. Optional coefficient_table supplies sourced, strictly ordered fraction/k_run/k_branch rows; interpolation replaces both constant K values and cannot extrapolate beyond the table. A bracketed table solution does not prove uniqueness; unbracketed endpoints do not prove absence of interior roots. No-root, residual, source-capacity, velocity and net-dissipation failures cannot release declared consumers, and checked consumers must use the same IFC producer. Neither mode automatically adopts Crane diagnostic coefficients or represents a pump-curve solution.

For the supported saved tee assembly, read docs/IFC_TEE_TRIAL.md and use workflow `tee_losses` with basis and depends_on on an earlier tee_assembly. Model and source specs are inherited; replacements are forbidden. The pinned fluids correlation diagnostic accepts either main-leg inlet, two positive prescribed outlet flows and sourced density/correlation assumptions. Retain signed coefficients referenced to combined inlet velocity and source-linked inlet/outlet GUIDs. Do not clamp negative run coefficients, treat K times dynamic pressure as terminal pressure, inject these directly into nonnegative local-velocity segment losses, or collapse finite ports to a zero-loss node. Full network balance, fitting friction/reference stations, product applicability and passive flow split remain unresolved. A passing diagnostic cannot satisfy a required hydraulic design.

For sourced thermal transport targets on circulation pipes, read docs/CIRCULATION_DUTY.md and use `bsa.circulation_duty`. Require explicit thermal power, density, specific heat, design temperature difference, flow direction and fluid applicability sources. Preserve native hydraulic and thermal-flow failures independently. Passing flow capacity does not prove heat exchanger performance, achieved temperatures, complete load coverage or regulatory conformity.

For zero-withdrawal pumped circulation read docs/HVAC_CIRCULATION.md and explicitly select `EPANET steady circulation graph`. Require a sourced fixed-head reference on one side connection, one fixed-speed pump and an explicit return path. Check zero net reference exchange and positive circulation along with native mass/energy/curve checks. The reference is not an expansion-vessel model; constant-property thermal duty and scoped saved-IFC/pipe-rule binding are supported by the adapters below; achieved temperatures, terminal controls and full HVAC acceptance remain pending.

For geometry-bound EPANET graphs, read docs/WATER_BINDING.md and use `water_coordination`/`bsa.water_binding` on the saved IFC. Omit all bound elevations/lengths/diameters from the hydraulic template. Require exact selected-system element, port and connection coverage using GUIDs, actual hollow profiles, reversible pipe ports and directed pump ports. Preserve signed per-piece flows and input/copied-IFC hashes. Coincident zero-loss nodes must be explicit. Straight-only routes may use sourced aggregate fitting K; finite elbow routes require the per-piece loss contract below. Finite separated node ports, unknown pieces and diameter changes cannot be silently collapsed. Whole-building scope, detailed fittings, physical coordination and visual/domain acceptance remain pending.

For branching water flow, parallel pipes, loops or pressure-dependent demand, read docs/WATER_GRAPHS.md and use `water_network`/`bsa.epanet` with the pinned optional water runtime. Keep static head metres distinct from old total-pressure Pa. Source routes independently from schematic coordinates; require explicit global PDA law, numerical budgets and full fixed-speed curves. Review native artifacts, reopened active input, signed flows, continuity, reservoir boundaries, independent pipe-energy residuals and pressure/delivery/velocity/pump targets. Source absolute/relative energy tolerances; never widen them to hide a failure. Review the declared legacy engine gravity/viscosity/unit conventions; relative viscosity <=0.001 is ambiguous and rejected. Preserve converged-but-failing cases. Never infer electricity from native default efficiency or claim a standalone graph is IFC-bound without the saved-model adapter. Actual products/routes, physical correlation applicability and domain acceptance stay pending.

Read docs/NETWORKS.md before interpreting pressures. Use `python -m bsa.network <project.json> --out <new-run>` or the `network` workflow adapter. Install the optional network dependency. Source every flow, internal diameter, route length, roughness, fitting K, fluid property and allowable velocity/pressure. Do not derive a route length from unrelated coordinates or manufacture a regulation table value.

This adapter supports only connected directed trees with prescribed withdrawals, constant-density Newtonian fluid and fully filled circular sections. It rejects transitional Reynolds numbers and loops. Do not map a closed chilled-water loop, partially filled drain, pressure-dependent sprinkler network or rectangular laminar duct into it merely to obtain a result.

The pressure contract is total (static plus velocity), common-reference, with elevation potential separate. Convert a supplied static requirement only when velocity/basis are justified; otherwise retain it as unresolved. Level air examples do not validate vertical ambient/stack pressure treatment. Use fittings K referenced to each local segment velocity. Do not confuse a Darcy factor with a Fanning factor.

Review segment calculations and node margins, source-required pressure and critical path. Failed targets must remain failed or trigger a versioned design iteration. A passing budget does not prove passive flow splitting, balancing, a fan/pump operating point, motor electrical power, cavitation, acoustics or code compliance. Keep these gates explicit.

For geometry-linked work, read docs/NETWORK_BINDING.md and use the `network_coordination` adapter or `bsa.network_binding`. Keep elevations, length and internal diameter out of the network input; derive these from explicitly bound model ports and source-backed diameter properties. Require connected straight axis-aligned port-centre chains and saved IFC reconciliation. Do not derive circular diameter from an envelope width. The standalone synthetic network fixtures remain independent unless explicitly bound.

Keep IDs aligned with actual schedules and models. Geometric binding does not prove circular product solids, junction shape, fitting K, clashes, balancing or professional acceptance. Preserve those gates separately.

For bounded sizing/design iteration, read docs/NETWORK_DESIGN.md and use `network_design` or `bsa.network_design`. Require a sourced finite catalogue and explicit allowed options for every segment, objective and search bound. Keep demands/routes/K/limits fixed under a sourced size-invariance assumption; never relax acceptance to make a choice pass. Preserve the baseline, all failed/error candidates and the selected rerun. No feasible option means report failure and request revised source/design constraints. A finite-catalogue material-score optimum is not a cost/carbon estimate or full engineering optimum. Explicitly update/reconcile BIM after sizing; do not infer outside dimensions from internal diameters.

For authored-model iteration, read docs/NETWORK_MODEL_DESIGN.md and use `network_model_design`. Require a shared canonical project UUID and separately sourced outside-envelope catalogue. Preserve world endpoints and original model data; retain space-containment rejection reasons before hydraulic ranking. Verify saved IFC internal/outside dimensions, stable device/port IDs and the model-derived pressure rerun. This supports fixed straight centrelines and bounding envelopes, not automatic rerouting, fitting resizing or collision acceptance.

For a fixed-speed liquid pump curve, read docs/PUMPS.md and use `pump_operating_point`/`bsa.pump` only with an explicit single-terminal fixed-total-pressure/free-flow assumption. Preserve the full source curve and separately declare a positive solver bracket; never cross an unsupported Reynolds transition or extrapolate. Review residual/flow bounds, capacity, upper-bound velocity and selected rerun. Source the equal pump-port elevation basis and fluid applicability. Only explicitly combined wire-to-water efficiency permits an electrical-input estimate; keep pump-only efficiency, nameplate rating, starting current and the separate electrical project distinct. Branch flow, controls, NPSH and complete acceptance remain pending.

To carry a passing pump estimate into a new electrical scenario and IFC properties, use docs/PUMP_ELECTRICAL.md. Bind actual source-port/pump GUIDs and the electrical device explicitly, replay source data and preserve the baseline load/hardware. Do not copy the operating estimate over the canonical design input or infer motor rating/PF from hydraulic power.

For candidate planar rerouting read docs/ROUTE_SEARCH.md. `route_model` compiles declared finite-grid paths with finite bends into hollow IFC and pressure inputs; `route_optimize` additionally selects minimum dissipative pressure at fixed bore and prescribed flow. Require sourced obstacles, grid, OD, bore, radius, containing space, elevation and separate excess-over-centreline-friction K values. Retain the length baseline and failed targets. Use a downstream `ifc_clash` task with reviewed actual contact-port GUIDs and sourced exclusion regions; search rectangles do not prove saved IFC obstacle correspondence or self-clearance. The example coordination plan checks represented pipe pieces only. Broader spatial, product, native drawing and visual acceptance remain separate.

Use workflow kind `circulation_duty` with project/basis and downstream `requires_pass` gates for thermal transport. Known downstream water_network/circulation_duty consumers must use identical hydraulic input bytes. Verify workflow integrity; this does not bind IFC, equipment heat transfer or regulatory scope.

For finite elbows in saved EPANET routes, read the finite circular elbow section of docs/WATER_BINDING.md. Require fitting_sources and exact piece_losses coverage on every affected route, omit template aggregate minor_k, and verify saved K metadata. Only supported source-parametric metre-based 90-degree hollow elbows qualify; physical node/fitting applicability and complete installation acceptance remain pending.

For a supplied finite single-pump circulation catalogue, use bsa.circulation_pump_design and docs/CIRCULATION_PUMP_DESIGN.md. Require sourced curves/preferences, thermal targets and pipe-rule bases. Keep baseline and every rejection; select only a combined pass and rerun it. No feasible candidate means no selection. Do not infer efficiency, extend a curve, or treat standalone screening as an updated IFC pump design.

Pump catalogue screening is workflow kind circulation_pump_design with catalogue, thermal_basis, rule_basis, pack, sources, and either project or depends_on referencing earlier water_coordination. The inherited mode rechecks the saved IFC/native bundle and derives the exact network before screening; omit project. Both modes preserve source/catalogue hashes. Use water_network with depends_on on screening and omit project to inherit its verified selection. A gate alone with unrelated explicit input does not establish correspondence.

To record a screened curve back onto a saved circulation IFC, use bsa.selected_pump_ifc and docs/SELECTED_PUMP_IFC.md. Screening must use the exact water_binding producer input. It preserves original files, writes curve provenance to the bound pump GUID and rebinds a revised template. Workflow kind selected_pump_ifc takes depends_on referencing screening that inherited water_coordination; template, binding and catalogue are inherited automatically. Follow it with ifc_circulation_checks for fresh revised-model thermal/rule results and ids_check for declared information requirements. Real pump shape, motor, NPSH, clash and full acceptance remain pending.


Inherited screening requires a passing baseline by default. For intentional iteration, set allow_failed_baseline: true only on circulation_pump_design inheriting water_coordination and follow docs/SELECTED_PUMP_IFC.md. The adapter rechecks saved geometry/native hashes and reevaluates raw results; only pressure/delivery/velocity target failures qualify while numerical, engine and curve checks must pass. Original failure and aggregate execution_pass remain false; explicit requires_pass on the baseline still blocks search. A passing revised selection permits new IFC and fresh checks, not retrospective baseline acceptance. For no-feasible results retain every rejection and obtain a justified revised catalogue or design constraint; never extrapolate a curve or relax targets solely to obtain a pass.


For a sourced one-duty/one-standby tank-transfer design, use bsa.plumbing_pump_set / workflow kind plumbing_pump_set and docs/HK_PLUMBING_PUMPS.md. Each role solves its own route/curve at the common receiving boundary and must meet the same target alone; do not sum standby flow. Keep each input hash and role failure. This is an explicit sequential-operating design mode, not proof of installed redundancy, controls, parallel operation or IFC identity.

For fresh prescribed-flow analysis of an existing or metadata-revised straight hollow IFC route, use workflow kind ifc_network with project/model/binding and exactly one ifc or depends_on. It reuses source reconstruction, saved profile/port reconciliation and the existing pressure solver. Read docs/IFCMCP_TRIAL.md. Require same-model downstream drawing gates; retain failed targets. This adapter excludes elbows and does not infer products, pump curves or full compliance.


For load-to-duct iteration use docs/AIR_ALLOCATION.md: classified allowance/heat-balance inputs plus a hash-bound interpreted metre polygon produce conserved terminal demands. Nearest-centre service cells are a stated design assumption, not room sensible loads or ADPI lengths. Use inherited `terminal_throw` and `duct_schedule` inputs rather than manually copied flows. A tree grouping must assign every terminal exactly once to a leaf. `duct_schedule` candidate sizing retains all supplied options and chooses by area/perimeter within limits; a design grid is not manufacturer stock or a coordinated physical envelope. Failed or empty selections block downstream work. Candidate dimensions, local losses, fan selection and installed geometry have separate evidence requirements.

For existing single-line drawings use docs/DUCT_SHEET.md only when fixed centrelines are appropriate. Bind every section to actual source LINE geometry and five distinct prior TEXT cells, pin the exact passing schedule, then update into a new file. The command does not place new routes or produce native acceptance. Verify the freshly saved DWG, exact schedule and actual PDF, correcting observed label/line conflicts before recording scoped visual acceptance. Re-run physical coordination when selected dimensions change even if single-line centrelines do not move.

Before ADPI criterion selection read docs/ADPI_BASIS.md. Pin edition and exact product/category correspondence alongside room-load and installation conditions. Do not silently combine older manufacturer pattern terminology with newer handbook categories or substitute a favourable table for unresolved applicability. The current terminal adapter remains a bounded throw/ratio calculator, not an ADPI approval engine.

For source-scoped ADPI ratio screening, follow docs/ADPI_BASIS.md and `python -m bsa.adpi_review <workflow> <settings> --out <new-review.json>`. It inherits one passing terminal lookup and hashes the actual criterion document. Supply explicit verified/unknown facts for room load, product category, lengths, installation and edition. Unknown facts stay pending and rejected applicability stays inapplicable; `all_ratios_within_scope` is not an ADPI prediction. Keep `ADPI_verified=false`. Use package `--adpi-settings` to collect the review automatically, without inventing source/installation evidence to populate facts.
