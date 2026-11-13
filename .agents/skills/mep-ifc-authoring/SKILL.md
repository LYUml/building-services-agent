---
name: mep-ifc-authoring
description: Create and revise source-linked IFC4 MEP envelopes, straight circular or rectangular duct walls, finite elbows and scoped tee assemblies with spaces, systems, ports, native geometry checks and scoped CAD drawings. Use for open BIM authoring and saved IFC drawing workflows.
---

# IFC MEP authoring

For a single composed tagged-source delivery command, use
source_network_tag_pipeline per docs/SOURCE_NETWORK_TAG_PIPELINE.md. Require
fresh host-selected output, complete finite tag coverage and native/source
review; independently verify the package and inspect its actual PDF. This
starts from existing source-native delivery/schedule, not an arbitrary brief.

For finite projected-network tag studies, use source_network_tags per
docs/SOURCE_NETWORK_TAGS.md. Require complete GUID/tag coverage, independent
graphic replay and saved-base preservation. Keep source ancestry/native/plot
acceptance separate; preview/solver success is not engineering acceptance.
Use source_network_tag_review to replay saved tags against common verified
schedule/delivery ancestry and native export/PDF. Keep actual visual inspection
in a separate source-hashed receipt; complete engineering remains pending.

For model-linked component/port/flow-path schedules, use source_network_schedule
per docs/SOURCE_NETWORK_SCHEDULE.md after verified source fitting analysis.
Keep GUID-keyed identities, inherited versus measured classification, typed
lengths, absorbed sections and null/signed losses. Schedule generation alone
does not place N-tags; use the tagged-source pipeline for drawing placement.
Do not carry tags across changed identity sets without review.

For closed GUID-linked source-network outlines, ifc_native now supports scoped
planar zero-width LWPOLYLINE contours per docs/NATIVE_NETWORK_CONTOURS.md. Require
actual save/reopen/export, unchanged geometry/identity and fixed-scale PDF review.
Keep standalone visual-review receipts separate from producer pending states;
this does not accept installation detail, products or complete engineering.

For an already verified complete source network, source_network_drawing exports
GUID-linked editable XY silhouettes per docs/SOURCE_NETWORK_DRAWING.md. Keep
source scale/elevation/gauge assumptions and bounded numerical cleanup explicit.
DXF/preview success does not establish DWG reopening, plot or installation
acceptance. Preserve all original requirements and source models.

For actual material-cap matching and separately assumed outside-interface
clearance studies on the source compound network, use interface_contacts per
docs/INTERFACE_CONTACTS.md. Identify physical pairs by IFC GUID, never display
names. Preserve the raw no-waiver result, source-bound numerical mask choices,
nonvacuous proof scope and all physical/product/installation review. Fresh
source/cap/proof replay is required; study pass is not design acceptance.

For an explicitly declared adjacent three/four-arm compound construction, use
source_compound_junction and compound_junction per docs/COMPOUND_JUNCTION.md.
Require exact original source coverage, existing elbow-cap identity, explicit
absorbed sections/profile revision, retained-straight budgets and native
station/branch/material/bore checks. This is a new isolated construction scenario;
do not clear old failed models, new network coordination, product/loss or design
acceptance from the candidate alone.

Use source_compound_network for the separate verified integration. Only explicitly
absorbed source bodies/links may be replaced; preserve prior tee/cross trims and
all requirement IDs. Require actual saved native cap/geometry/link checks and a
single represented directed tree, then repeat raw clash/clearance with the source
policy. Zero intersections is not pressure/product/installation acceptance.

For partial integration of verified source_cross_candidates, use
source_cross_network per docs/SOURCE_CROSS_NETWORK.md. Reconstruct parent trims,
preserve distinct tee/cross consumption, verify native cross cap/roll/flow and
all same-file links, then rerun raw clashes. Retain blocked nodes; native
topology success does not complete physical/network/engineering acceptance.

For original four-arm multi-branch nodes, use source_cross_candidates and the
native rectangular_cross/rectangular_cross_transitions adapters per
docs/SOURCE_CROSS_CANDIDATES.md. Cover every source node, inherit the verified
parent straight budgets and blocked tees, and reject unsupported/opposed-ray or
overrun cases. Isolated cross candidates do not repair the parent network until
trimmed, connected and independently rechecked with all raw clash findings.

For partial integration after source_tee_candidates, use source_tee_network per
docs/SOURCE_TEE_NETWORK.md. Require independent source/component replay, both-end
straight trims, native cap/section-roll agreement and exact saved same-file links.
Keep blocked/multi-branch nodes explicit and run full raw clash analysis on the
new model; a successful append or schema check cannot clear coordination.

For unequal source tees after a verified elbow selection, use source_tee_candidates
per docs/SOURCE_TEE_CANDIDATES.md with explicit construction/method choices. Keep
both-end blocked nodes and unattempted multi-branch obligations. Local native
assemblies do not repair/trim/accept the original network until a verified merge.

For source-backed equal-section elbows with explicit alternative radii, use
bsa.elbow_radius_selection per docs/ELBOW_RADIUS_SELECTION.md. Preserve original
candidates/source constraints, verify native outputs and run separate coordination.
No feasible radius combination means no authoring; geometric fit is not installation approval.

Circular elbows now use compact native IfcTriangulatedFaceSet storage per
docs/IFC_MESH_STORAGE.md; legacy polygonal meshes remain readable. Preserve
exact source coordinates/indices and full native/bore/volume/EXPRESS checks.
Do not lower geometric resolution, waive checks or infer viewer/DWG acceptance
from the smaller file or a successful network-only reconciliation.

For the optional native sheet after the shared water/pump/electrical handoff,
read docs/COUPLED_NATIVE_HANDOFF.md. Use the existing ifc_native consumer after
the exact passing drawing, with explicit host AutoCAD and source sheet settings.
Missing runtime or failed identity must block output. Require actual DWG reopen,
GUID/entity reconciliation, physical print-scale check and inspection of every
actual PDF page. Record visual review separately; never clear full installation
or engineering acceptance from the two-segment schematic.

For pump/electrical scenario properties read docs/COUPLED_HANDOFF_UNITS.md.
Use the source-replayed pump_electrical adapter and its typed explicit-unit native
checks. Never write copied operating kW/current onto a merely nearby element or
change global project units to reinterpret existing properties. Preserve original
STEP entities and the distinct baseline; property coupling is not electrical
system topology, real equipment or installation approval.

For a passing source-bound circular fan operation, use `circular_fan_metadata`
depending on `circular_fan_operating_point`; read
[calculated airflow state](../../../docs/CIRCULAR_FAN_METADATA.md). It replays
pressure/curve/selection sources and writes a new IFC copy with typed m3/s and Pa
scenario properties on exact body/port GUIDs. Preserve original design values and
units; calculated properties are not measured operation or native fan equipment.
Saved schema and unchanged geometry/relationships remain required. Do not pass
hand-copied flows or overwrite an existing scenario namespace.

For the initial modular native-authoring boundary,use module_authoring with
ifcopenshell.bim-authoring and a source-pinned authoring.ifc.bim request.
It reuses bsa.bim in a fixed subprocess and emits model-artifact/1;see
docs/MODULES.md and examples/modular-authoring-plan.json. Downstream spatial
modules inherit its verified IFC and require matching coordinate frames.
Scoped native checks are not visual/product/installation/design acceptance.
Only one authoring provider is verified;Revit/AutoCAD replacement is pending.

For drawings of a supported circular-profile common model,use ifc_views with
depends_on on module_authoring,then ifc_views_native. The source is resolved from
the verified model-artifact payload. See examples/modular-drawing-plan.json.
Native AutoCAD reopening and per-sheet scale checks must execute,then inspect
every actual merged PDF page. Existing pipe-only/profile/label restrictions and
hidden-line/fitting/equipment/hydraulic/installation gaps remain explicit.

For finite equal-section elbows in a source backbone,use bsa.duct_elbow_backbone
and docs/DUCT_ELBOW_BACKBONE.md. Declare every original elbow radius with its
classification/source and retain both-end section budgets. Do not shrink radii
or remove blocked corners to make the whole study appear feasible. Freshly
verify trimmed native cap stations,body geometry and actual same-file links;
retain all remaining source connection classes and raw clash findings. Partial
authored bends do not complete physical joints,pressure,products or installation.

For all straight sections of a passing native duct sheet,use bsa.duct_backbone_ifc
and docs/DUCT_BACKBONE_IFC.md. Supply classified elevation,wall gauge and explicit
nominal/internal interpretation;do not invent installed values. Inherit exact
source nodes/selected sizes/flows. The saved study has untrimmed walls and unlinked
ports;use existing clash checks to retain junction interference. No logical links
or shared-node exemption can replace physical fittings/trim. Final export removes
the internal coordination envelope and uses a named reference storey,not a real
room/thermal zone. Keep complete BIM,products,installation and pressure pending.

For source-flow/straight-friction checks on a saved duct_fitting_chain, route to
../mep-network-analysis/SKILL.md and docs/DUCT_CHAIN_ANALYSIS.md. Native connectivity
and inventory cannot clear missing fitting-loss/pressure scope. The source-bound
analysis remains pending and blocks required releases; it accepts no replacement
IFC, copied flows, air properties or lengths.

To merge the two source-bound fitting compositions and their fresh trimmed span
into one saved directed local system, use duct_fitting_chain with project in
docs/DUCT_FITTING_CHAINS.md. Require native source cap/port agreement, unchanged
source shape/property fingerprints, complete owned inventory, exact same-file
links, one system, connected material/independent volume and boundary-bore topology.
The actual seven-body model has16 ports,six interfaces and four external boundaries;
this is not the entire supply network. Use same-producer ifc_query for independent
official inventory with the isolated runtime. Preserve construction/elevation,
products, pressure and full assignment acceptance. Whole-model diagnostics do not
override the existing labelled preview's12-port budget or native drawing gates.

For a straight candidate between two source-bound tee/transition compositions,
use bsa.duct_fitting_span and docs/DUCT_FITTING_SPANS.md. Require the same native
source section and fresh endpoint/source-model checks. Deduct both fitting
reaches, independently match saved end-plane separation/section/roll and reject
overrun; no installed length or product allowance is inferred. Check saved native
wall/ports/mass and material intersections against both endpoint models. The
result has boundary ports in a separate IFC, not inter-file logical connections
or a merged system. Preserve installation/elevation/product/pressure acceptance.

For a source-declared equal-section core tee with one to three separate centred
transition arms, use rectangular_tee_transitions with project in
docs/RECTANGULAR_TEE_TRANSITIONS.md. Bare arms must be explicit. Preserve saved
component/source hashes, owned stable ports, parent-relative frames, complete
inventory/system checks, material union/volume/topology and centre-bore checks.
For one local study on an existing native route, use bsa.duct_fitting_fit with the
exact arm-section binding; it freshly inherits source rays/nominal sizes and
retains overrun. Remaining centreline is not installed straight length. Keep
opposite-end fitting consumption, elevation/roll, product joints, sheet-normal
taper wall, loss and entire-project acceptance pending. Do not treat a local
source-placed software candidate as release of all real unequal tees.

For source-declared centred rectangular transitions, use rectangular_transition
with project in docs/RECTANGULAR_TRANSITIONS.md. Require explicit inside end
sections, section-plane wall offset, straight/taper lengths, upstream angle,
directions and sourced rigid placement. The helper's filled envelope is converted
to a native outer-minus-inner wall with stable owned ports and saved schema,
corners/stations, independent volume/moment/angle, closed-mesh and centre-bore
checks. This is not constant sheet-normal construction. Preserve product/joint,
loss, adjoining assembly, unequal-tee and actual project end-station acceptance;
the synthetic transition cannot complete the real differing-section tee layout.

For the explicitly source-declared equal-section rectangular tee plus three
butt-ended straight walls, use rectangular_tee_assembly with tee_spec and
assembly_spec in docs/RECTANGULAR_TEES.md. Require three positive sourced lengths
and retain inherited rigid frames, exact saved bodies/ports/system membership,
material union/independent volume and centre-bore probes. The actual synthetic
assembly and same-producer ifc_clash execute with explicit contact regions and
outside-region proofs. Do not reuse those QA tolerances as installation rules or
infer variable sections, product joints, losses or actual coursework acceptance.

For an explicitly sourced ideal equal-section sharp rectangular tee, use standalone bsa.rectangular_tee and docs/RECTANGULAR_TEES.md. Require dimensions, thickness interpretation/classification, rigid placement and three port directions; no product or coefficient defaults exist. It verifies saved native Boolean/prism geometry, stable owned port frames, material/bore topology and independent volume. This does not support variable-section takeoffs, production fabrication, pressure losses, adjoining assemblies or workflow release. Do not substitute this limited geometry for the different-section branches of a real supply tree.

For native hollow rectangular 90-degree bend geometry, use bsa.bim's explicit rectangular straight/elbow scope and docs/RECTANGULAR_ELBOWS.md. Require radial width, normal height, wall thickness, radius, signed perpendicular axes and actual arc-end ports; preserve native profile/revolution/arc/mass/centroid/port checks. Pressure binding supports sourced per-piece excess K with matched section rolls/opposed normals; no fitting K is inferred. Catalogue bend redesign remains unsupported; bend-plane curved DXF projection and independent saved-entity audit are implemented, with native curved-sheet reopening, independent exported-DXF audit and visual PDF checks executed for the synthetic lead/quarter/tail case (docs/RECTANGULAR_ELBOWS.md), while real fitting applicability/fabrication and full engineering acceptance remain pending.

When fan-power scope is required, combine same-producer rectangular_fan_regulations and ifc_clash in rectangular_drawing requires_pass. The executed synthetic native delivery in docs/HK_FAN_POWER.md retains failed/unknown rule branches without drawing folders. Drawing/native-export audits and actual PDF review remain mandatory; this still does not prove real fan selection, inventory or full installation acceptance.

Rectangular sheets now independently audit actual saved and AutoCAD-reopened/exported DXF entities against source-checked native bounds, axis endpoints and inside dimensions. Preserve complete geometry/text/GUID and raw model-space/visibility/plot checks; do not substitute a writer success flag or invented expected records. Approximate font boxes do not replace actual PDF review. See docs/RECTANGULAR_AIR_NETWORKS.md.

For a supported rectangular outer-envelope sheet use rectangular_drawing with a native rectangular producer, same-producer ifc_clash required gate, settings/sheet and explicit AutoCAD CLI path. It uses actual saved rectangular profiles and complete supported fan-envelope context, not circular size labels. Native reopen/scale checks and actual PDF review remain separate; end-on/unsupported elements reject. See docs/RECTANGULAR_AIR_NETWORKS.md. Do not label the diagnostic outline/notes as full installation drawings.

Gate rectangular selected-model delivery with ifc_clash depends_on on rectangular_model_design (or source-defined rectangular_network_binding). It reads the exact native producer model and checks artifact pins before/after; unknown/replaced/changed evidence cannot pass. Use sourced clash policy and actual represented context; synthetic fan envelopes are not physical fan selection or whole-building coverage. Keep downstream requires_pass and full drawing/engineering review separate. See docs/RECTANGULAR_AIR_NETWORKS.md.

For catalogue-selected rectangular straight model revision, use rectangular_model_design per docs/RECTANGULAR_AIR_NETWORKS.md. Require stable project_uuid and separately sourced wall thickness per option; reject outer-space failures before selection. Preserve baseline/rejections, fixed world endpoints and saved object/port GUIDs, then reauthor/reopen and repeat bound pressure. This supersedes standalone revision-pending notes for supported straight chains; clashes, bends/junctions, fabrication and full acceptance remain separate.

For source-defined rectangular straight duct chains bound to pressure analysis, use rectangular_network_binding with project/model/binding per docs/RECTANGULAR_AIR_NETWORKS.md. Omit duplicated numerical geometry; the adapter derives source dimensions/port lengths, independently verifies saved native wall profiles and reconciles directed saved ports before analysis. This extends standalone geometry support, but selected-catalogue model revision and finite bends/junction physics remain pending.

For axis-aligned hollow rectangular straight ducts, use bsa.bim with the explicit rectangular scope/body_shape in docs/RECTANGULAR_AIR_NETWORKS.md. Require independent internal width/height/thickness and a matching outer envelope with end-face-centre ports. Saved profile/metadata/placement and native through-bore, connected wall, mass and port-axis checks are executed. Sharp corners only; bends/transitions/junctions and selected-network hydraulic binding remain unsupported. Do not call an envelope box a hollow duct or infer fabrication/installation acceptance from this geometry check.

Cable route text placement now uses whole ezdxf text boxes and the saved/native-export auditor checks bounded outward dimension regions, text/text and text/LINE/ARC-box interference. Preserve exact source dimension graphics and notes; don't bypass a crowded-layout failure by trusting a writer flag or widening physical tolerances. Font boxes are approximate and ARC-box rejection is conservative; actual native PDF review remains required. The --quarter-turn synthetic case is executed at an explicitly chosen 1:25 scale (docs/CABLE_ROUTE_DRAWINGS.md).

The verified cable route drawer/auditor now also supports lead-quarter-tail geometry. Preserve the incoming start and its separate axis/OD/dimension graphics; independent auditing must reject an omitted lead. The native scale reference remains the tail's unique BSA_CABLE_AXIS LINE, while the lead uses BSA_CABLE_LEAD_AXIS with the same cable GUID. The synthetic runner accepts --lead 1.2 together with --route --include-obstacles; fixed-scale sheet fit, same-model checks, native readback and actual PDF review remain mandatory. See docs/CABLE_ROUTE_DRAWINGS.md; prior three-piece refusal notes are historical.

Cable route delivery now audits actual saved DXF entities through bsa.cable_route_audit against already source-checked geometry: true arc/OD/straight, dimensions/notes, IFC identities and model/plot visibility flags. Workflow repeats the audit on AutoCAD's reopened/exported DXF. Never supply invented expected geometry or treat writer flags as audit evidence. Preserve actual PDF, crowded-layout, font and installation review separately; see docs/CABLE_ROUTE_DRAWINGS.md.

For source-box context in cable_route_drawing, optionally declare obstacles with the same sourced inventory used for native append. bsa.obstacle_projection checks exact native box identity, provenance and saved bounds; complete physical cable/box coverage is mandatory in this mode. The drawing shows actual projected rectangles and omitted-axis depth intervals, not fabricated coplanar obstacles. Projection overlap never replaces same-model 3D coordination; inspect the actual PDF and retain full installation review. The synthetic runner supports --route --include-obstacles.

For a selected single continuous quarter-plus-tangent cable's planar geometry drawing, use docs/CABLE_ROUTE_DRAWINGS.md and bsa.cable_route_drawing. It first requires the saved electrical IFC reader's native checks, then emits true ARC/LINE axes, OD outlines and nonassociative LINE/TEXT dimensions with the actual cable GUID. Reject nonplanar/oblique projections. Workflow cable_route_drawing inherits an IFC-derived study, explicit exact same-model IFC/binding, settings/native_settings, and mandatory bend plus coordination pass gates; it rechecks study/check artifacts before native output. bsa.ifc_native accepts BSA_CABLE_AXIS for fixed-scale native reopening/plotting. List omitted elements and review actual PDF; technical pass is not coordinated installation acceptance. Standalone output carries no workflow release authorization.

For the scoped continuous cable reader see docs/CABLE_CONTINUITY_TRIAL.md. One quarter revolution with an outgoing tangent extrusion and optional incoming tangent extrusion is supported, with exact independent composite Axis pieces and native UNION checks. Require saved connected-solid/analytic checks, endpoint port normals, source anchors and true full length. Include the composite line in bend-limit coverage. Synthetic fixture modes quarter-straight and straight-quarter-straight require exact tangent_extensions_m and, for the latter, lead_extensions_m maps. Composite primitives are authored in a common local frame and source-rigid-placed together; retain the initial rotated NotManifold failure and verified fix. run_continuous_cable_demo.py --lead 1.2 exercises the three-piece numerical path. Physical route drawing now supports both scoped planar forms with independent saved/native-export audits and same-model workflow gates; full multi-bend/product/installation acceptance remains pending.

For supplied manufacturer CAD geometry, read docs/PRODUCT_INTAKE.md. `bsa.cad_block` extracts an explicitly identified named definition using native AutoCAD; `bsa.cad_sections` measures sourced circular annular samples in its local frame. Keep sampled CAD bore measurements separate from manufacturer specifications and hydraulic inputs. End samples do not prove interior connectivity or minimum passage. Preserve vendor licensing and keep restricted source/derived geometry local.

`bsa.cad_ifc` converts a selected single CAD solid into a separate unconnected tessellated IFC fitting. It explicitly compensates native STL relocation and checks original native volume/bounds/centroid, mesh closure and saved IFC triangles. Supply source units, project namespace and conversion tolerances. `predefined_type` defaults to JUNCTION; explicitly select CONNECTOR for the connector path. Nested connector shells require the sourced cavity contract in PRODUCT_INTAKE.md, including count and numerical containment/volume tolerances. This body has no inferred ports or system placement and is not compatible with the source-parametric tee_assembly contract. Saved IFC passage/clash and viewer checks remain required for their respective claims.

For a converted CONNECTOR with actual source POINT nodes and a LINE axis, use workflow `connector_ports` with `depends_on` on `cad_ifc` and an explicit source-node/placement basis. It inherits the producer, preserves cavities and tessellation, and creates two model ports. Use the resulting producer for `ifc_query`, `ids_check` with `examples/ids/cad-connector-provenance.ids`, and `ifc_preview`. Never reinterpret CAD node separation as installed pipe-end gap or reuse the three-port junction adapter. The nodes do not establish bore, gasket, external connection or hydraulic applicability; require separate installation evidence and geometric joint checks.

Use `bsa.product_ports` for the separate source-anchored three-port placement path in PRODUCT_INTAKE.md. Select actual CAD LINE endpoints, linked same-source passage probes and sourced rigid placement/grouping. Require outward support-plane and probe coverage checks, saved port/provenance/world-body reconciliation and the fresh saved-IFC passage/wall checks. It preserves stable product/port/group IDs but does not establish physical coupling compatibility, external pipe connections or hydraulic readiness.

For a requirement-linked manufacturer chain, use workflow kinds `cad_ifc` then `product_ports`, followed by `ifc_query` and `ids_check` on the placed producer. The official MCP inventory supports fitting, port and logical-system minimum counts; `examples/ids/cad-product-provenance.ids` checks information presence only. A pre-placement inventory requires a fresh post-placement query with `refresh_inventory: true`. Read PRODUCT_INTAKE.md for the source contracts and runtime options.

For a sourced junction/connector pair, use workflow `product_alignment` with `junction_from` on `product_ports`, `connector_from` on `connector_ports`, and a sourced alignment basis. It composes actual saved bodies through upstream IfcOpenShell asset append; it does not establish an installed joint or hydraulic connection. Inspect `model_alignment_pass`, `calculated_checks_pass` and overlap-component locations separately. An inventory of either input does not cover the combined model; use a fresh same-producer inventory boundary before downstream delivery.

If placement passes but mesh overlap fails, use workflow `alignment_native` with `depends_on` on the alignment and an explicit AutoCAD runtime to investigate. It derives the relative transform and original DWGs from the saved source chain. Do not add the failed alignment to the diagnostic's `requires_pass` unless deliberately blocking investigation; ordinary release consumers must retain their pass gates. Native clear plus mesh fail remains a failed comparison requiring review. Do not widen thresholds or infer installed pipe-end spacing to make it pass. Native support requires equal declared units and a proper rigid rotation; full three-dimensional relative rotations are passed through, while mirrors/scales are rejected. Read the final workflow sections of docs/PRODUCT_INTAKE.md for schemas and evidence.

For standalone native investigations use `bsa.cad_joint`, which compensates DWG INSBASE and verifies the actual insertion and body properties. Never manually equate INSERT coordinates with a geometry transform. `bsa.cad_sections` retains primitive inventories even when a mixed section fails annulus classification; a retained circle is not automatically a bore. Preserve both native and tessellated findings and restrict conclusions to the measured scope.

Use workflow `ifc_preview` with an explicit element `guid` and either inherited `depends_on` or an explicit `ifc` to generate four fixed body/port views. Gate it through the relevant `requires_pass` checks. Inventory and IDS prerequisites must select the same model, including transitive prerequisites. Inspect the actual PNG and retain a separate source/PNG-hash-bound review; successful generation leaves visual review pending. Preview arrows are illustrative, omitted elements are listed, and projected-triangle artifacts prevent treating it as a complete BIM-viewer, hidden-line drawing or installation review.

For explicitly chosen internal clearance paths, `bsa.cad_passage` checks native solid/cylinder intersections after verifying the actual probe bounds/volume. Require a positive wall-control intersection and preserve blocked passage results. Clear probes alone do not establish that they connect the intended ports, determine minimum bore or validate hydraulic coefficients. Use the local model frame and declared drawing units; read PRODUCT_INTAKE.md for the exact scope and executed controls.

For a single equal-bore hollow tee with three butt-ended straight stubs, use `tee_assembly` in docs/IFC_TEE_TRIAL.md, not the envelope BIM adapter. `examples/tee-trial/plan.json` and `placed-plan.json` are synthetic software fixtures. Supply sourced tee/pipe dimensions and a canonical project_uuid; optional sourced rigid placement uses origin_m and a right-handed 3x3 rotation. Keep all 13 product/port GUIDs stable for revisions. Require saved wall/bore/volume, placement, world endpoint, port topology and material-intersection checks. Use tee_drawing inheriting tee_assembly for the local X/Z outside-outline diagram and GUID schedule, then ifc_native; examples/tee-trial/drawing-plan.json gates both on a same-model tee_split check. Inspect the actual printed PDF after native reopening. The path still lacks a multi-tee schema, manufacturer joint detail and general network solution. For coefficients, use ../mep-network-analysis/SKILL.md; do not claim placement support in this separate adapter changes the envelope adapter's limits.

For tee_selection delivery, tee_drawing inherits the selected producer and verifies catalogue/source/artifact correspondence before resolving its model/specs. Preserve selected_paths checks; no replacement spec or IFC is permitted. The labelled local diagram contains T1/P1/P2/P3 callouts and model-derived overall/reach dimensions. LINE/TEXT dimensions are not associative CAD DIMENSION entities: regenerate after model revisions. Read actual PDF pixels and keep geometric dimensions distinct from installation allowances.

For finite circular 90-degree elbows read docs/CIRCULAR_ELBOWS.md. Require explicit bore/outside/radius/centre/signed axes and actual end-face ports. The Body is a source-parametric tessellated wall with a separate exact circular Axis, not an analytic swept Body. Keep native oriented-mesh, bore, independent volume and source-index checks. Constant-density directed tree routes may derive physical arc length and explicitly sourced excess-over-centreline-friction K per piece; reject aggregate K duplication. Saved EPANET routes support these finite elbows through docs/WATER_BINDING.md; broader fittings, product and viewer acceptance remain unresolved; require a separate saved-model clash check.

The finite elbow `examples/circular-elbow/coordination-plan.json` now runs saved-IFC clash checking after the pressure binding. Source new contact regions and clearances for each actual project; never inherit this synthetic policy as a code rule. Require full geometry/solid coverage and both nonempty outside-to-full clearance proofs for the two example joints. Regression controls must reject unchanged-port wall intrusion and a close bore obstacle while accepting a small object inside the empty curved bore. The numerical example does not establish product, viewer or installation acceptance.

Read docs/IFC_MODELS.md. Use `python -m bsa.bim <project.json> --out <new-run>` or the `bim` workflow adapter. Install the optional `bim` dependencies first. Input examples are under examples/mep-ifc.

Every dimension, origin, device class, containing space, system and connection must come from source data or an explicit scenario assumption. The adapter uses SI metres and axis-aligned bounding envelopes at minimum-corner origins; do not pass centre coordinates or assume actual manufacturer shape. Device rotations, arbitrary routing and multi-system equipment are unsupported. Do not synthesize their results through this adapter. Reversible water pipes may explicitly use SOURCEANDSINK on both connected ports; require both saved relationship arcs and preserve the separate pump inlet/outlet directions. Mixed directed/bidirectional connection pairs remain unsupported.

For actual straight round wall bodies, read docs/CIRCULAR_GEOMETRY.md. Opt into the explicit mixed geometry scope and `body_shape: straight circular wall`, with separately sourced internal/outside diameters and opposite end-face-centre ports. The saved IFC must pass hollow-profile, oriented connected mesh/bore, annular volume, bounds and outward-port-axis checks. Preserve the distinction between an analytic IFC wall and its approximate QA mesh, and between this generic straight body and manufacturer/fitting geometry. Never infer a circular body or wall parameter from electrical ratings or a single bounding dimension.

Keep equipment IDs consistent with the calculations and CAD used in the same actual project. The separate synthetic IFC examples are not automatically reconciled with the earlier three-light CAD dataset. Preserve source descriptions and electrical input kW; never label thermal capacity as electrical input.

Port connections represent explicit logical topology, not a routed or sized pipe/cable. Provide local port offsets and source-to-sink or two explicitly bidirectional directions. Read bim-verification.json and schema-validation.json after native IFC reopen. They check entity counts, source properties, space/system membership, world-coordinate envelope bounds, metre units, port direction/placement and connection endpoints. Schema/EXPRESS validity does not prove physical feasibility, performance or code compliance. For saved hollow water routes, use docs/WATER_BINDING.md and `water_coordination`; bind actual GUIDs, cover the entire selected system and source zero-loss node and aggregate-K idealizations. Never collapse a finite separated-port fitting into a coincident node.

Inspect the model in a BIM viewer and record artifact-hash-bound visual evidence before claiming visual acceptance. Keep detailed shape, clash/routing, system performance and domain compliance pending until actually verified. Do not claim RVT fidelity from an IFC result.

For saved-model coordination read docs/CLASH.md and use `ifc_clash`/`bsa.clash` with sourced thresholds and explicit contact rules. Require complete geometry/solid coverage, review both intersection and clearance findings, and never waive a solid overlap because ports are connected. Legacy pair-minimum exceptions leave other zones pending; outside_regions mode requires both conservative outside-to-full proofs. Neither mode certifies connector/product compatibility. Unrepresented, rejected or unverified geometry prevents a pass; numerical checks do not replace the BIM-viewer and engineering gates.

For revisions, supply a canonical `project_uuid` to keep class/input-ID object and device/port GUIDs stable. Retain that namespace for the same project and use a new UUID for an independent project. Do not promise stable relationship/representation IDs or byte-identical IFC files. For geometry-linked network sizing, use docs/NETWORK_MODEL_DESIGN.md with explicit outside dimensions; it preserves source endpoints and checks the new saved IFC against selected calculations while keeping product and visual gates pending.

For segment schedules or projected pipe/duct diagrams, read docs/IFC_DRAWINGS.md and use `ifc_drawing` on the saved producer IFC. The adapter checks direct hollow profiles against metre metadata and directed ports, preserves GUID links in the DXF and lists omitted equipment classes. Inspect unsupported-segment errors and the preview; do not present centreline projection, analytic wall volume or successful DXF reload as an installation drawing, material takeoff or native/printed acceptance.

For coplanar routes containing finite elbows, read docs/IFC_ROUTE_DRAWINGS.md and use `ifc_route_drawing` with saved IFC, original source model and drawing settings. Require full physical-piece coverage, actual world bounds alongside hollow-wall/port checks, and true circular arcs with OD outlines. The old straight-only adapter does not acquire fitting coverage. Reject unsupported units/planes rather than flattening geometry. Use `ifc_native` with a sourced straight reference and a window enclosing all arcs/labels, then inspect the actual PDF separately. Generic OD outlines do not establish manufacturer, support/joint, BIM-viewer or full installation acceptance.

Inspect `annotation-layout.json` and the actual sheet as well. Outward OD stubs and conservative OD/prior-leader obstacle checks must reconcile to the saved DXF. An unproven bounded search is a drawing failure, not permission to revert to a crossing leader. Graphic margins are derived from text height and must not be treated as engineering clearances. Use docs/ELBOW_RISER.md for the independent negative-quadrant elevation and its failed visual/low-supply controls; do not inherit its scenario inputs as measured project data.

For saved annotation QA read docs/SAVED_ROUTE_AUDIT.md. Require `independent_saved_audit` after DXF reopen; it checks actual linked lines/text, source anchors, obstacle/pair/self intersections and dimensions without trusting planner flags. Require linked annotation visibility flags to pass, including raw paper-space markers before reader normalization and on/thawed/plot-enabled layers. Layer locking is permitted. Use `bsa.route_drawing_qa` to recheck an existing native export against actual source IFC/model/settings and the layout record. Flags do not prove visible pixels; the audit does not replace full native body identity, glyph/legend inspection or PDF review.

For native delivery of that diagram, use `ifc_native` with an explicit sheet window/scale and reference IFC GUID, supplying the local AutoCAD path through the workflow CLI. Check the independent DWG reopen geometry and complete model/XDATA identity audit, then inspect the actual PDF and keep a hash-bound visual record. A numerically correct reference length does not establish equipment/fitting detail or complete sheet acceptance.

For a three-axis model, read docs/IFC_VIEWS.md and use `ifc_views` plus `ifc_views_native`. Source two/three distinct axis planes, unique GUID callouts, symbolic end-on size and each sheet's nonzero reference/window/scale. Require every segment in every view and a nonzero axis somewhere; do not drop end-on segments or treat symbol size as bore. Inspect all merged PDF pages after native reopen/per-page scale checks and keep a separate source-bound review. Hidden lines, overlaps, finite fittings/equipment and complete installation sheets remain pending.

For electrical devices already defined in the common electrical schema, prefer the coordination adapter documented in COORDINATION.md instead of retyping electrical values into a separate BIM project. It converts centre XY to minimum-corner envelope origins, propagates circuit/power/PF/source properties and checks saved IFC against DXF and calculations. Its companion geometry must explicitly supply dimensions and elevation; none are inferred from electrical ratings.

For saved PTAC equipment identity and property-only simulation results read docs/HVAC_DEVICES.md and examples/hvac-equipment-plan.json. Require explicit device/system/space GUID mappings, complete selected unitary-equipment coverage, native body containment and matching saved thermal/flow/efficiency properties. Reopen OSM to verify linked GUIDs; preserve every original IFC entity and source bytes when appending result properties to analysis.ifc. Simulated annual/peak electricity is not nameplate or feeder design power. Preserve failed calculated checks and false design acceptance. Device bounds are not product/clash/port/routing/visual acceptance.

For source-bound HVAC envelope plans/schedules, use docs/HVAC_DRAWINGS.md and examples/hvac-drawing-plan.json. Require the checked analysis IFC and full producer artifact bundle, exact device callouts and strict rectangular native shapes. Generate GUID-linked equipment.dxf/CSV, then use ifc_native with equipment reference layer/name and a sourced sheet window/scale. Reject clipped extents, reopen the actual DWG and inspect the actual plotted PDF separately. Short reference edges do not prove label/table quality; simulated electrical peaks are not nameplate/feeder ratings. Omitted elements, detailed products/ports/ducts and installation/engineering acceptance stay explicit.


For selected circulation-pump curve properties, use docs/SELECTED_PUMP_IFC.md and workflow kind selected_pump_ifc depending on inherited circulation_pump_design. Reuse the bound source model; preserve original files and stable pump/port GUIDs. Reopen and rebind the new selected-model.ifc against its selected-template.json; the resulting physical hydraulic input must match the screened selection. This is a property revision, not a manufacturer geometry replacement. Route combined checks and IDS to this new producer, not the pre-selection model. Any geometry or installation drawing still needs the actual saved-model clash/clearance and native/visual gates.


For saved-model inventories or a new text property set on an existing pump, ../mep-ifc-mcp/SKILL.md provides the verified official MCP path and source-preservation checks. That isolated runtime is not a geometry-authoring substitute: local OpenCascade loading is blocked, while queries and scoped metadata saves have separate evidence. Do not treat unchanged original entity records as verification of new geometry or equipment truth.

For straight electrical cable envelopes read docs/THREE_PHASE_IFC.md. Workflow three_phase_ifc inherits an exact passing three_phase study and accepts explicit saved ifc/binding inputs. Circular extrusions have executed native correspondence and tamper tests; the retained swept-disk fixture fails mandatory solid checks. Do not equate placed cable ports/bus anchors with connected electrical equipment. Gate the same-study schematic explicitly through requires_pass; conductor selection, bends, physical connectivity, protection and viewer acceptance remain separate.

For geometry-driven electrical input revision use bsa.three_phase_ifc_project (docs/THREE_PHASE_IFC.md): derive a new snapshot from saved straight cable lengths, preserve baseline electrical data/source kinds, recheck the derived project against native IFC, and optionally recompute. Do not describe tolerated baseline length mismatch as baseline correspondence success or reuse its old numerical result. Use workflow three_phase_ifc_project for registered derivation and a fresh solve; connected electrical installation remains pending.

For a model-driven study in a plan, declare three_phase_ifc_project with baseline project, saved ifc and binding, and supply --three-phase-python at execution. It must pass geometry and new numerical targets before consumers proceed. three_phase_regulations, three_phase_ifc and three_phase_drawing inherit the derived project/study pair; no replacement inputs. Require same-producer rule gates before drawing. See docs/THREE_PHASE_IFC.md and the existing Hong Kong runner --ifc-driven; synthetic conditional passes do not prove full assignment or code acceptance.

For explicit saved electrical connection graphs use bsa.three_phase_topology or workflow three_phase_topology (docs/ELECTRICAL_IFC_TOPOLOGY.md), reusing actual IFC4 nested ports and relationships. The separate author_three_phase_topology_fixture.py creates sourced synthetic common-node board boxes only. Preserve full selected-system/port coverage, unique nesting ownership and exact directed relationship counts; positions alone do not prove links. Physical terminals, internal busbars, individual conductors, protection and installation acceptance remain pending.

For electrical model revisions, retain exact IFC and geometry-binding identity across derived numerical producer, geometry/topology checks and drawing gates. Matching coordinates/graph do not make separate revisions interchangeable. Identical byte copies are supported; altered bindings require a deliberate fresh producer/check chain. Current delivery verifies three_phase_model_bindings, preserving pending physical and engineering acceptance.

For solid round quarter-circle cable envelopes use docs/CABLE_QUARTER_BENDS.md and quarter_cable, with standard IfcRevolvedAreaSolid, independent exact three-point ArcIndex, true arc length, proper rigid 3D frame and outward end-port Z normals. The synthetic author supports --body-kind mixed-revolution with explicit quarter_bends source data. Do not route these solid envelopes into hollow pipe/bore/loss adapters. Unsupported angles, profiles or composite paths must remain unresolved rather than be approximated by chords.

Before claiming a cable bend meets selected product requirements, use docs/CABLE_BEND_LIMITS.md and its saved native product/source/condition checks. Geometry validity and R>a do not establish a manufacturer minimum. Product metadata edits are model revisions, so preserve source documents and rerun the intended same-model study/gates. The read-only command will not populate metadata or infer a radius datum. Full product selection and installation acceptance remain pending.

Workflow three_phase_bend_limits now registers the declared bend comparison on the same numerical producer and exact IFC/binding bytes. Source/condition metadata must belong to that revised model; regenerate the model-derived study after edits and require the check before drawing. Failed or unknown limits block release. The repeatable runner adds synthetic source-backed fixture metadata only, not manufacturer-approved hardware.

Use ifc_obstacles for explicit source-linked metre-IFC4 obstacle boxes without inventing water-route input data. It reuses obstacle_boxes, preserves original STEP entity records and validates saved box solids. The combined model is a revision: refresh its electrical binding and numerical study before three_phase_coordination/drawing gates. Preserve contact/overlap/coverage failures; no broad cable-joint waiver is added. Read docs/CABLE_COORDINATION.md for tested scope and source assumptions.

For source-defined concept massing without equipment, use the explicit concept-space scope in docs/CONCEPT_SPACES.md and scripts/run_public_massing.py. Require sourced storeys, gross-footprint basis and native saved geometry/provenance checks. Never add fake MEP to satisfy input requirements or equate space boxes with thermal zones, net area, facade/window geometry or completed building design. Keep all original brief obligations and performance/delivery gates pending until implemented and verified.

For a unified concept BIM task, optionally supply concept_layout settings with exact source, window_wall_ratio and layout=centered-equal-fraction. The saved-IFC handoff is inventoried under the task concept-layout directory. See docs/CONCEPT_SPACES.md. This is draft geometry only; retain source obligations, material/glazing and native simulation/delivery checks.

For native concept facade revisions use bsa.concept_facade per docs/CONCEPT_SPACES.md with exact original concept IFC/source/layout and explicit sourced thickness decisions. It creates real void/filling relationships and preserves original records. Require reopened through-hole topology/corner/volume checks and source identity; window bodies remain envelopes, not rated glazing/frame products. Do not infer thermal boundaries or completed architecture; standalone workflow inheritance and full performance/delivery remain pending.

Native facade is now a registered concept_facade workflow kind: depends_on must identify earlier concept bim with concept_layout; basis supplies explicit thickness decisions. Do not supply replacement model/project/layout. Downstream supported IFC consumers inherit facade.ifc. Retain artifact pins and scope restrictions; this supersedes the earlier standalone-only limitation. See docs/CONCEPT_SPACES.md.

For source-bound concept facade material cuts and all-storey native sheets, use bsa.concept_section per docs/CONCEPT_SECTIONS.md. Require matching native facade/original geometry/layout/thickness plus explicit cut/text/scale decisions. Preserve actual mesh-plane/polygon/analytic-area checks and independent saved/native-export audits. Native DWG release requires AutoCAD reopen and actual PDF review; DXF-only stays native_reopen_pass=false. These are concept sections with no completed room program/MEP/products/site north, not full architectural/installation acceptance.

Native concept sections are now registered as concept_section with an earlier concept_facade depends_on and sourced drawing basis. Original model/layout/thickness are inherited; replacement/runtime fields reject. Missing --autocad stays pending without drawings, and a false native-reopen result fails. Retain native producer pins and actual PDF review; this supersedes the standalone-only note. See docs/CONCEPT_SECTIONS.md.
