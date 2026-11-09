# Manufacturer fitting intake

Use a manufacturer record before replacing synthetic tee inputs. The first inspected record is [Victaulic No. 20 DN40](../sources/products/victaulic-no20-dn40.json). It is research input, not a selectable catalogue entry. Its official PDF is hash-pinned; printed pages 10 and 59 were visually reviewed after downloading and rendering. The PDF and full-page images remain in ignored `runs/manufacturer-intake-v1/`, not redistributed here.

## Data boundaries

Store published quantities with units and page locators. Preserve nominal designation separately from mating pipe OD, internal flow diameter and maximum fitting body envelope. A table's rounded metric column is a published value; do not replace it with a more precise-looking conversion of its inch column.

The current tee authoring adapter requires a constant internal radius and a simplified intersecting-cylinder outside wall. Port centre-to-end distances alone do not establish either radius or the physical groove/coupling shape. A coordination placeholder, if requested, must remain distinguishable from an actual manufacturer's solid and cannot pass product clearance acceptance.

For the pressure adapter, establish the pressure stations, flow direction, reference velocity, split range, Reynolds applicability and whether wall friction is included. An equivalent pipe length is not a dimensionless coefficient. The relation `K = f_D * L_eq / D` requires justified reference-pipe diameter, Darcy friction factor and velocity convention; it does not establish that the resulting coefficient meets our complete face-to-face tee contract. Changing the reference velocity requires a squared velocity ratio, with independently justified flow assignments. Do not invent those assignments from the words run and branch.

## Next integration decision

Obtain a compatible pipe/fitting bore specification and manufacturer hydraulic methodology or a separately justified design method before creating a real `tee_selection` candidate. Establish connection allowances and project service/pressure/temperature suitability separately. Hong Kong applicability must reference the actual project and rule pack; a manufacturer's catalogue is not regulatory approval.

The current record deliberately has null unresolved fields and no solver-ready K values. Existing synthetic regression fixtures remain mathematical controls. This intake is manual source review; no automatic manufacturer extraction, readiness gate or engineering acceptance is claimed.

## Native manufacturer block reuse

The [official software library](https://www.victaulic.com/resource-software/) provides CAD and STEP content under its own license, not an open-source license. A local trial downloaded the IPS AutoCAD 3D package, identified the target instance by its handle, block name and attributes, then extracted its named definition with native WBLOCK. No manufacturer DWG, DXF, PDF preview or model-derived geometry is redistributed. Source URLs/hashes and a limited execution summary are in [the trial record](evidence/manufacturer-block/trial.json).

Reusable original adapter:

```powershell
.venv/Scripts/python -m bsa.cad_block path/to/library.dwg path/to/selection.json --out runs/new-block
```

The selection JSON requires `source`, `drawing_sha256`, `insert_handle`, `block_name`, `insunits`, and a nonempty `attributes` mapping. Obtain the handle and actual values from `bsa.cad_intake`; match them to the source document before selection. Hash mismatch, missing identity, wrong units/attribute values, duplicate tags, nested references and xrefs reject. Output must be a new directory inside this repository. The adapter does not download content or grant redistribution rights.

AutoCAD runs on isolated copies and verifies the active path before writing. A second native process reopens the extracted DWG. Checks cover unchanged input bytes, drawing units, entity type/layer counts and attribute definitions. These are **structural checks, not ACIS shape equivalence**. Output uses the block definition coordinate system; source instance translation, rotation, scale and attached attribute overrides are not baked into it. Instance attributes are retained separately in the report.

The actual target extracted successfully. An additional native MASSPROP probe and fit-to-page isometric wireframe PDF review were performed locally; the tee is visible without clipping. Those are diagnostic observations, not a scaled installation drawing or proof of bore connectivity. The existing idealized IFC tee adapter cannot ingest the manufacturer's ACIS solid yet. Next work is verified solid/port interpretation and model placement, alongside hydraulic methodology; do not overwrite the unresolved product fields with inferred values from a block label.

## Native circular-section measurement

`bsa.cad_sections` now uses AutoCAD's existing SECTION/EXPLODE operations on isolated source copies, then reads the actual generated boundaries with ezdxf. It does not implement another solid kernel. Supply a source-hashed DWG, explicit model-space solid handle, drawing units, positive metre tolerance and independently located axis-aligned cutting planes:

```powershell
.venv/Scripts/python -m bsa.cad_sections source.dwg section-basis.json --out runs/new-sections
.venv/Scripts/python scripts/test_native_cad_sections.py --out runs/new-section-controls
```

Basis fields are `source`, `drawing_sha256`, `solid_handle`, `insunits`, `tolerance_m`, `sections`. Each section has `id`, `source`, `plane` (XY/YZ/ZX) and `centre_drawing_units` (three coordinates in the source definition frame). The point defines both the cutting plane and the expected circular centre. Source the sampling position; a point near an end face is not the face itself. The actual circle centres are transformed from OCS to WCS before checking position and normal. Radius, wall thickness and centre are reported in metres.

An accepted sample must produce exactly one new REGION and exactly two concentric circular boundaries on its reserved diagnostic layer. A miss cannot accidentally explode an old entity. Extra loops, noncircular boundaries, wrong normals/centres/units and unresolved wall thickness reject. Input DWG and basis hashes are checked again after execution. Diagnostic files can contain the proprietary source geometry and must remain local under its applicable license.

Three actual tee samples, each 0.05 drawing inch inward from the observed centreline endpoints, yielded annular sections. See [execution evidence](evidence/manufacturer-block/sections.json). This establishes local model openings only: it does not prove a continuous passage through the junction, the minimum bore, physical tolerances, connection compatibility or a manufacturer-guaranteed internal diameter. Accordingly the product record's unresolved bore field remains null, and the pressure/IFC adapters do not automatically consume these measurements.

Native controls create an independent hollow cylinder with known dimensions, a filled cylinder and a non-intersecting plane. The annulus returns the expected dimensions; the other cases reject for their actual geometry. Separate unit controls cover OCS conversion, nonconcentric circles, wrong planes/units/locations and ambiguous inputs. These checks are not full product or drawing acceptance.

## Native passage clearance probes

`bsa.cad_passage` uses native CYLINDER and INTERSECT on isolated copies of a selected single model-space solid. Each probe's actual native MASSPROP volume and bounding box must agree with the specified cylinder before its Boolean result can be accepted. Before/after DXF exports must contain two solids and then zero or one respectively. Zero means no volumetric material intersection at the native kernel's tolerance; tangential contact and arbitrarily thin defects are not certified.

```powershell
.venv/Scripts/python -m bsa.cad_passage source.dwg passage-basis.json --out runs/new-passage
```

The basis has exactly `source`, `drawing_sha256`, `solid_handle`, `insunits` and `probes`. Each probe has `id`, `source`, `role`, `start`, `end`, `radius`; all coordinates/radii use the declared **drawing units**. Role is `passage` (must be clear) or `wall_control` (must intersect). At least one of each is mandatory. Coordinates, direction and radius are source-declared diagnostic choices, not automatically inferred port locations. Output contains native measurement evidence and input/artifact hashes. A blocked passage or ineffective wall control produces `passage_checks_pass: false` and CLI exit 2; source/engine/geometry-evidence errors raise instead. Failed calculated checks remain recorded.

Probe verification uses eight-decimal native output, an absolute volume tolerance of 1e-7 drawing-units cubed plus relative 1e-7, and absolute bound tolerance 1e-7 drawing units. Probe volumes at or below 1e-7 are rejected as unresolved. These are diagnostic numerical checks, not manufacturing tolerances. Native Booleans do not acquire a user-defined defect-detection tolerance from these values.

The real tee trial found no material intersection for the specified main and branch cylinders and a nonempty intersection for the deliberately offset wall cylinder. Evidence is in [passage trial](evidence/manufacturer-block/passage.json). Their overlapping positions support a bounded clear route in this model; the tool does not automatically prove that arbitrary probe sets connect, reach the intended ports or remain inside the intended fluid space. It does not search maximum radius or establish all interior geometry. The manufacturer bore guarantee and hydraulic inputs therefore remain unresolved.

An independent known filled cylinder fails the passage check. A deliberately misplaced wall control inside the actual tee bore fails the overall check despite the clear passage probes. Unit controls reject wrong or missing native mass properties, bounds, control roles and invalid inputs. Source/derived vendor geometry remains local; the public trial record contains only limited measurements and provenance.

## Native body to IFC

`bsa.cad_ifc` now converts an explicitly identified single CAD junction solid into a separate, unconnected IFC4 `IfcPipeFitting` with an `IfcTriangulatedFaceSet`. It reuses AutoCAD STLOUT, ezdxf's binary STL loader, IfcOpenShell and Manifold3D; install the existing pinned `tee` extra. It preserves the local source-definition coordinates in metres and a namespace-derived product GUID. There are no inferred ports, system connections, hydraulic dimensions or project placement.

```powershell
.venv/Scripts/python -m bsa.cad_ifc source.dwg conversion-basis.json --out runs/new-cad-ifc
```

The exact basis fields are `source`, `drawing_sha256`, `solid_handle`, `insunits`, `project_uuid`, `id`, `linear_tolerance_m` and `relative_volume_tolerance`. The source identifies the intended junction; this is not automatic product classification. Supply numerical tessellation tolerances before execution. The real trial used 20 micrometres for bounds/centroid and 0.1% relative volume; these are model-conversion tolerances, not product dimensional tolerances or regulatory limits. A stricter failing comparison remains failed.

The initial negative-coordinate STL trial exposed automatic relocation into positive coordinates. The adapter therefore measures original native volume, bounds and centroid, explicitly moves the isolated solid so its minimum coordinates are one drawing unit, exports at FACETRES 10, and reverses that recorded translation after loading the STL. Original source/copy files remain unchanged. Units, binary STL length, one connected closed positive-volume mesh and all three native geometry statistics must reconcile before writing IFC.

After saving, the actual IFC is reopened through IfcOpenShell's geometry engine. Closed mesh, volume, bounds and centroid are checked again, along with the exact saved coordinate/index correspondence to the imported triangles. These checks establish a bounded tessellated conversion; they do not prove pointwise equivalence to every curved native face or preserve CAD editing history. The emitted IFC cannot be substituted into the source-parametric `tee_assembly` solver contract.

The actual manufacturer trial produced 4,762 triangles and passed native/STL/saved-IFC comparisons; separate IFC schema/EXPRESS validation reported zero statements. Wrong declared units and excessively strict tessellation tolerances rejected before IFC output. Known-cube, translated/wrong-scale, missing native metadata and open-mesh unit controls pass. See [conversion evidence](evidence/manufacturer-block/ifc.json). Source and converted vendor geometry remain local. Saved-IFC passage/clash checks, viewer review, ports and system integration remain separate next steps.

## Source-anchored model ports and placement

`bsa.product_ports` now places a verified conversion and adds three reversible model ports plus a logical service group. It preserves the source tessellation and fitting GUID. The namespace from the conversion also supplies stable port and group GUIDs. This is a model connection interface; physical groove/coupling compatibility and an external connected network remain unverified.

```powershell
.venv/Scripts/python -m bsa.product_ports runs/conversion placement-basis.json --out runs/new-placed-product
```

The basis contains exactly `source`, `placement`, `system_name`, `passage_basis`, `ports`. Placement uses the existing sourced rigid origin/rotation contract. The passage path resolves relative to the basis file and must identify the same CAD hash, solid and units as the conversion. Each port has `id`, `source`, `line_handle`, `endpoint` (start/end) and `passage_id`. Choose source CAD model-space LINE endpoints deliberately; their outward frame axis is the direction from the other endpoint. The port must lie on the linked passage-probe axis/span and the outward support plane of the converted body, within the declared conversion tolerance. This bounded interface excludes recessed mouths or shapes whose other parts extend beyond a selected mouth in its outward direction.

The producer's inputs/artifact hashes are rechecked, then the actual source body is reconciled to native mass properties. This catches a shifted body even if its artifact hash is updated. After saving the placed IFC, the adapter reopens it to check unchanged local tessellation, world geometry, actual port frames/identities/provenance and service-group membership. Mass-property integration is centred locally to avoid cancellation at distant project coordinates.

The source-linked passage and positive wall probes are repeated against the saved **world-coordinate IFC mesh**, with 128-sided probe cylinders and a 1e-12 cubic metre intersection threshold. These are bounded polygonal clearance checks, not exact analytic cylinders, a minimum-bore search or full-system clash acceptance. Failed passages retain a false result and CLI exit 2. The original native probe result alone cannot satisfy this saved-body check.

The real vendor body passed a synthetic translated/compound-rotated placement and all three saved IFC probes. An internal junction-centre anchor and a rehashed shifted producer mesh were rejected. A second placement retained all five product/port/group GUIDs; actual schema/EXPRESS validation reported zero statements. See [placement evidence](evidence/manufacturer-block/ports.json). Project coordinates and service grouping are synthetic demonstration choices, not an installed project or manufacturer service assignment.


## Requirement-driven execution

Workflow kinds `cad_ifc` and `product_ports` now compose the verified adapters. A task pair is:

```json
[
  {"id":"convert","kind":"cad_ifc","drawing":"source.dwg","basis":"convert.json"},
  {"id":"place","kind":"product_ports","depends_on":"convert","basis":"place.json"}
]
```

Embed these tasks in a source-linked workflow plan, mapping **each** task to a quoted brief requirement. All files must lie within the plan directory. The placement basis references its passage basis relative to itself; that nested input is also hashed by the workflow. Pass `--autocad` to `python -m bsa.workflow execute`. Ports inherit the earlier conversion directory; replacement producer/IFC paths are rejected. Missing engines remain pending; failed conversion prevents port execution. Generic IFC consumers must target `place` to inspect the revised model. Domain consumers still enforce their own supported geometry contracts.

Local actual-vendor execution at `runs/manufacturer-workflow-v1/run` passed both stages and workflow integrity. Four workflow tests cover missing engine, failed producer, input mutation, replacement/wrong dependency and nested-path escape; four existing inventory gate tests also pass. Geometry and local source inputs are not redistributed. Execution and byte integrity do not establish physical joint, hydraulic, viewer or regulatory acceptance.


## Upstream model information checks

The official isolated IfcMCP inventory now supports positive minimum counts for `IfcPipeFitting`, `IfcDistributionPort` and `IfcDistributionSystem`, alongside pumps and pipes. The protocol trial reconciles selected entity identities/names and the complete exact-class count map against the saved IFC parser. Counts establish model inventory, not connected network topology.

After `place`, add an `ifc_query` with `depends_on: "place"` and a sourced inventory requirements file; supply `--ifcmcp-python tools/ifcmcp-runtime/Scripts/python.exe`. Then add `ids_check` with `depends_on: "place"`, `requires_pass: ["inventory"]`, and `ids` pointing to a local copy of `examples/ids/cad-product-provenance.ids`. That original project IDS requires nonempty CAD source fields on fittings and anchor fields on every applicable port. It is a presence contract, not a verification of source truth or statutory requirements. The geometric adapter independently checks exact anchor values.

If a pre-placement inventory was required, run the post-placement query with `refresh_inventory: true`. The old inventory cannot certify the revised producer; referencing the old model after refreshing also rejects.

Actual local four-stage execution at `runs/manufacturer-audit-v1/run` passed: one fitting, three ports, one logical distribution system and 19 IDS checks. Independent synthetic controls reject a minimum of four ports, one missing anchor field, an empty model and stale producer correspondence. Restricted vendor IFC remains local. See `docs/evidence/manufacturer-block/information.json` for limited execution evidence.


## Saved IFC visual preview

Install the pinned `preview` extra and run:

```powershell
.venv/Scripts/python -m bsa.ifc_preview <saved.ifc> <element-GlobalId> --out runs/new-preview
```

The standalone tool reopens one represented element with IfcOpenShell 0.8.5, extracts its world-space mesh and attached port placements, and uses Matplotlib 3.11.2 for four fixed orthographic views. No triangle decimation is applied. `preview.json` binds source and PNG hashes, records world coordinates/axes, lists omitted elements and keeps visual review pending. Axis arrows have an illustrative length derived from body extent; they do not encode flow or physical connectors. Display coordinates are world-axis offsets from the explicitly reported centre. Legends abbreviate names to 32 characters; full names/GUIDs remain in JSON. At most 200000 triangles and twelve ports are supported.

Actual source-placed vendor tee rendering was inspected at `runs/manufacturer-preview-final/preview.png`: body, mouth regions and three numbered axes are visible, and annotations are readable without observed page clipping. The separate limited review is in `docs/evidence/manufacturer-block/preview-review.json`; vendor imagery remains local. Facet raster artifacts and projected triangle sorting remain visible limitations, so this is not an independent interactive BIM-viewer or full interior/installation review. An independent millimetre-unit, rotated and translated solid/port fixture verifies world-metre extraction and omitted-element reporting; missing port placement rejects.


### Workflow preview and review boundary

The preview is also workflow kind `ifc_preview`. Example final task:

```json
{"id":"preview","kind":"ifc_preview","depends_on":"place","guid":"<actual 22-character GlobalId>","requires_pass":["information"]}
```

Map it to a quoted brief requirement like every other task. Supply exactly one `depends_on` on an IFC producer or explicit `ifc`, plus the actual selected element GUID. Unexpected fields and replacement input combinations reject. Missing/failed upstream producers or required checks prevent execution. The preview's transitive inventory and IDS prerequisites must use the same producer or identical explicit file bytes; a different model cannot borrow those passes. This IDS correspondence enforcement is scoped to the preview consumer, not a new blanket guarantee for every existing adapter.

`pass` means the image was generated. `preview.json` still says visual review pending, and the workflow never promotes that to design acceptance. Inspect the actual PNG and preserve a separate source/PNG-hash-bound review. The actual five-stage manufacturer run at `runs/manufacturer-delivery-v1/run` passed with both inventory and IDS bound to `place`; actual PNG inspected. The restricted image/model remains local, while `docs/evidence/manufacturer-block/delivery.json` records limited evidence. Independent synthetic execution confirms a missing IDS property blocks preview creation, and source-binding controls reject both direct and transitive mismatched models.


### Local report navigation

Every new workflow index now groups artifacts under their source requirement, retaining the exact acceptance target, source locator, executed scope and pending acceptance status. Expand Task artifacts to open relative model, calculation, log and preview links. Each link displays the recorded artifact hash; failed tasks may retain diagnostic files and are explicitly not approved deliverables. The page needs no external assets or JavaScript and can be opened locally. Keep the run directory structure intact.

The generated index is itself included in workflow artifact hashes, so `workflow verify` detects subsequent page mutation. This is accidental-change detection against a local manifest, not a signed or tamper-proof record. Historical runs retain their original manifests. Actual five-stage regeneration, browser layout/navigation and integrity passed at `runs/manufacturer-delivery-v1/run-report-v2`; limited review evidence is in `docs/evidence/manufacturer-block/report.json`.


## Physical connection research boundary

Two additional limited source records are now pinned: `sources/products/victaulic-style77-dn40.json` and `victaulic-ogs-roll-dn40.json`. Official documents [06.04](https://assets.victaulic.com/assets/uploads/literature/06.04.pdf) and [25.01](https://assets.victaulic.com/assets/uploads/literature/25.01.pdf) were downloaded and their relevant tables/notes visually reviewed. Actual 06.04 is Rev Y (September 2026); search summaries still returned Rev X, so indexed summaries were not used as the version authority. Full PDFs and rendered pages remain local.

This research changes the next implementation step: do not simply append a plain hollow cylinder to each tee port. Build an explicit pipe-end/joint contract containing both saved element/port identities, chosen pipe specification, preparation evidence, selected installed offset/rotation, motion demand, gasket/service basis and coupling orientation. Source geometry measurements and project assumptions must remain separate. The new records are reference data, not a complete compatibility evaluator.

The movement table must not become an automatic installed-gap value. Likewise, the groove's minimum groovable wall must not become a pressure-design thickness, and a reference groove depth must not override the controlled groove diameter. Neither the pipe-end table nor the CAD tee end alone establishes full joint fit. Model actual groove/housing/gasket interfaces or keep them explicitly unverified. Preserve finite separation when later connecting the hydraulic network; the existing coincident-node shortcut is not a validated representation of this joint.

Next evidence needed: applicable installation instructions; actual mating pipe and groove measurements; gasket/service selection; actual coupling geometry; saved joint placement and clash checks. Only after those are available should this researched product enter an automatic joint-authoring or selection path. No product, hydraulic or Hong Kong compliance flag was promoted by this research.


### Actual coupling CAD intake

The already pinned official IPS archive contains Style 77. Source-selected DN40 block `CPLG_1.5 (40)_77` (INSERT C6, size/style attributes) was extracted using existing native WBLOCK and independently reopened. Units, definition structure and source preservation passed. Restricted source/extracted geometry remains under `runs/coupling-cad-v1`.

Its one selected ACIS entity exports to three Manifold-decomposed components: one positive and two negative signed volumes. This may represent enclosed cavities, not three physical parts or a bad vendor model. The current one-boundary conversion contract correctly stops before IFC creation. Do not remove the component check or discard negative shells to force a pass. Next work must validate nested-shell containment/orientation and reconcile native material volume and cavity preservation in saved IFC.

`cad_ifc` basis now optionally accepts `predefined_type` as `JUNCTION` (legacy default) or `CONNECTOR`. The saved value is checked. An independent original native annulus executed successfully as CONNECTOR; this does not validate conversion of the actual complex coupling. Three-port `product_ports` rejects CONNECTOR inputs. A synthetic enclosed-cavity test retains the current rejection until a supported contract is implemented. Limited evidence is in `docs/evidence/manufacturer-block/coupling-cad.json`.


### Supported nested connector cavities

`cad_ifc` CONNECTOR conversion now optionally accepts `cavity_contract`:

```json
{"source":"<evidence and numerical applicability>","count":2,"containment_margin_m":0.000001,"volume_tolerance_m3":1e-12}
```

One positive connected boundary and the declared 1–8 negative boundaries are required. The adapter reverses each negative shell into a positive cavity, dilates it by an axis-aligned cube of half-size `containment_margin_m`, and requires the expanded cavity to remain inside the outer volume within the declared Boolean volume tolerance. Expanded cavities must not overlap above that tolerance. Subtracting the cavities must reproduce the input material in both directional differences and volume accounting. These are numerical mesh proofs, not exact analytic CAD containment or physical-part identification. Large tolerance choices require project justification.

The saved IFC is independently remeshed through the existing IfcOpenShell runtime and checked under the same contract, alongside native volume/bounds/centroid reconciliation and exact stored source triangles. Single-boundary legacy behavior remains the default; no automatic cavity-count inference promotes a model to acceptance. Three-port junction placement still rejects connectors.

Actual Style 77 DN40 conversion now passes with two enclosed negative shells, and saved IFC schema/EXPRESS validation is clean. The generated fixed-view PNG was inspected. Two deliberately bounded native CAD cavity probes (0.3 mm radius, 1 mm length) are clear, with a separate positive wall control; these corroborate local void locations only. An earlier smaller probe was rejected by the existing native volume-resolution floor; tolerances were not relaxed. Independent cube controls reject exterior, crossing, touching, insufficient-margin, overlapping, wrong-orientation and wrong-count cases. Evidence: `docs/evidence/manufacturer-block/coupling-cavities.json`. Restricted CAD/IFC/images remain local. Full joint/pipe/gasket compatibility and engineering acceptance remain pending.


## Source-node connector placement

`python -m bsa.connector_ports <cad-ifc-producer> <basis.json> --out runs/new-connector` is a separate standalone adapter for a verified CONNECTOR. Basis fields are `source`, sourced rigid `placement` (same schema as product_ports), `axis_line_handle`, and exactly two `ports`. Each port has `id`, `source`, `point_handle` and `axis_endpoint` (`start` or `end`). Both handles must identify model-space POINTs on the chosen LINE segment; nodes must be distinct, ordered and point in opposing axis directions. Do not use this path to invent nodes where CAD lacks them.

It inherits the full conversion bundle, rechecks source/native geometry (including the declared nested cavity contract), preserves tessellation, applies rigid placement and creates two stable model ports with `BSA_ConnectorAnchor` source metadata. Saved world geometry, port frames/IDs/provenance, type and absence of external connections are checked. `placed-connector.ifc` and `connector-ports.json` retain source hashes and unresolved engineering conditions. Workflow registration and automatic physical-joint assembly are not yet implemented.

Actual Style 77 source LINE 6D and POINTs 75/71 executed successfully under a synthetic rotated/transformed placement. Their source separation is 0.762 mm. This is CAD node spacing, **not a selected installed pipe-end gap**; duplicated POINTs exist at the same source positions and are rejected if selected as the two opposing anchors. All ten saved checks, schema validation, revision identity stability and the actual duplicate-position rejection passed. Independent unit controls cover opposite axes, off-axis/out-of-span nodes, paper-space nodes and wrong entity types.

The actual placed PNG was inspected. Preview marker/axis artists now explicitly overlay the opaque body, so interior nodes remain visible; this is diagnostic annotation, not hidden-line visibility. Almost coincident nodes cannot be dimensionally judged from the full-body view. Continue to use numerical source coordinates, and do not infer gasket contact, bore clearance, pipe compatibility or hydraulic connectivity from these model ports. Limited evidence: `docs/evidence/manufacturer-block/connector-ports.json`.


### Connector workflow handoff

The connector adapter is now workflow kind `connector_ports`, taking `id`, `kind`, `depends_on` on an earlier `cad_ifc`, and `basis` (optional description/requires_pass). Source conversion is inherited; replacement IFC/producer inputs are rejected. Missing engines or failed conversion leave placement pending. The saved producer artifact is `placed-connector.ifc`.

Follow placement with `ifc_query` requiring one fitting/two ports, then `ids_check` using `examples/ids/cad-connector-provenance.ids`, then `ifc_preview`. All three consumers must target the placed producer. A pre-placement inventory requires a fresh inventory boundary after placement. The connector IDS checks every applicable port's POINT/axis provenance presence, not the truth of node installation semantics or exact component counts; use the inventory contract for minimum counts.

Actual five-stage execution, source/artifact integrity and 16 information checks passed at `runs/connector-workflow-v1/run`; actual PNG inspected. Missing/failed producer, replacement inputs, stale model correspondence and a missing axis-source field are covered by independent controls. Limited evidence: `docs/evidence/manufacturer-block/connector-workflow.json`. Physical joint assembly remains pending.

### Combined model-node alignment

Official I-100 revision H installation research is pinned in `sources/products/victaulic-style77-installation.json`. Printed pages 52 and 149 were rendered and inspected; the DN40 nominal end-separation upper value is 1.6 mm, whereas the separately pinned 06.04 Rev Y product table gives 1.5 mm. Keep both source values distinct. Neither proves that the CAD POINT spacing of 0.762 mm represents selected installed pipe ends. The handbook requires aligned mating components, appropriate separation and gasket placement between grooves; it does not identify our CAD nodes. Do not resolve the failing overlap by guessing an offset, rounding these publications together, or broadening a numerical tolerance. Source CAD node semantics and detailed joint geometry remain the next evidence needed.

`python -m bsa.product_alignment <junction-placement-folder> <connector-placement-folder> <basis.json> --out runs/new-alignment` reuses IfcOpenShell 0.8.5 `project.append_asset` and `geometry.edit_object_placement`. It requires intact passing source bundles, one product per bundle, metre units and distinct root identities. The exact basis fields are `source`, `target_port_guid`, `connector_port_guid`, `roll_degrees`, `alignment_tolerance_m` and `overlap_volume_tolerance_m3`. Port origins coincide and Z axes oppose; roll is an explicit scenario input. No installed gap is inferred and no IfcRelConnectsPorts relationship is asserted.

The reopened `alignment.ifc` is checked for retained identities, unchanged junction geometry/ports, transformed connector mesh/ports and connector anchor metadata. Manifold3D computes actual saved material intersection without contact exemptions. `alignment.json` separates `model_alignment_pass` from `calculated_checks_pass`; overlap above the declared numerical threshold makes the CLI exit 2 while retaining diagnostic artifacts. This standalone adapter is not yet a workflow task.

The actual No.20/Style77 trial aligned two products and five ports, passed schema/EXPRESS validation, but retained 2.6501259e-9 m3 material overlap against a 1e-12 m3 threshold. Thus calculated checks **fail**. The approximately 2.65 mm3 mesh overlap needs investigation against tessellation accuracy and manufacturer joint detail; it is neither waived nor treated as definitive physical interference. See `docs/evidence/manufacturer-block/alignment.json`. Restricted geometry and renders remain local.

Alignment reports now localize every connected overlap component in the target port frame: local Z is its outward axis, bounds are in metres, and maximum radius is computed from the intersection mesh vertices. The actual rerun retained one component spanning Z = -15.875 mm to approximately zero and reaching radius 24.130 mm. The overlap is therefore not localized solely to the end plane; inspect the native sealing-land/groove region and CAD dimensional fidelity before selecting a remedy. No offset or tolerance was changed. Component volumes reconcile with the total; an independent rotated/translated box verifies the coordinate transformation and an empty-solid control verifies no-overlap output. Evidence: `docs/evidence/manufacturer-block/overlap-localization.json`.

Native AutoCAD SECTION sampling 6.35 mm inward from the aligned node gives tee OD 48.260 mm and bore 40.894 mm. The corresponding connector section contains one coaxial circle of radius 24.130 mm plus four arcs and 32 lines; it correctly fails the two-circle annulus contract. The equal sampled radii support investigation of tessellation at coincident analytic boundaries, but do not prove full-joint compatibility or the cause of all overlap. No mesh failure was waived. `cad_sections` now retains `boundary-inventory.json` before annulus classification, including circle coordinates/radii, primitive counts and source/export hashes. Actual native rejection preserves that diagnostic artifact; five section tests pass. Limited measurements: `docs/evidence/manufacturer-block/native-joint-sections.json`. Source DXFs stay local.

### Native joint Boolean comparison

Actual isolated AutoCAD `INTERSECT` at the same model-node alignment produced zero remaining solids. A radial +0.254 mm control produced one intersection solid (approximately 194.596 mm3). Before each Boolean, both solids were present; native connector volume, transformed centroid and full bounds were independently checked against its source mass properties, and exported units/audits plus original copied-DWG hashes were verified. Evidence and artifact hashes: `docs/evidence/manufacturer-block/native-joint-intersection.json`.

Two discarded attempts are retained locally: the first misread uniform-scale/attribute prompts; the second omitted source INSBASE compensation. The connector DWG has INSBASE=(0,-0.015,0) inch. With rotation -90 degrees about Z, insertion at (2.75,0,0) produces the intended geometry translation (2.765,0,0). In general the insertion point must account for the rotated/scaled base point; never equate INSERT coordinates with a body transform. Native post-insertion bounds and centroid detected the wrong transform before any acceptance claim. Disable attribute prompting for this diagnostic insertion and inspect actual command output.

The successful native comparison supports a tessellation-related explanation of the small mesh overlap, within the native kernel's tolerance. It does not prove exact mathematical zero intersection or installation compatibility. The existing mesh report remains failed; no generic contact exemption or enlarged threshold has been added. A reusable cross-engine adjudication contract, node-to-installed-end semantics, gasket details, physical topology and hydraulic integration remain pending. This was a scoped experiment using generated scripts in isolated copies, not yet a general native joint CLI.

Preview both saved elements with `python -m bsa.ifc_preview <alignment.ifc> <junction-guid> --include <connector-guid> --out runs/new-combined-preview`. Repeat `--include` for additional represented elements within the existing triangle/port budget. Included/omitted identities and combined bounds are recorded. The actual four-view PNG was inspected; overlapping node labels prevent dimensional joint assessment. Physical connections, gasket/pipe compatibility, network calculations and regulatory acceptance remain pending.
