# Building Services Agent

需求文档 → 可追溯项目数据 → CAD/BIM → 工程计算与仿真 → 校核 → 交付。

An agent workspace and deterministic engineering tools for reusable MEP workflows. The AI reads requirements and orchestrates tools; calculation engines compute results. Unknown inputs stay unknown.

## Run the first vertical slice

```powershell
.venv/Scripts/python -m pip install -e .
bsa validate examples/office-electrical/project.json
bsa run examples/office-electrical/project.json --out runs/office
.venv/Scripts/python -m unittest discover -s tests -v
```

The synthetic office example produces traceable circuit calculations, an editable DXF device overlay, a drawing preview, an HTML report, and input/output hashes. It is a demonstration, not the completed coursework or a certified design. No old project files are copied or modified.

## Use with an agent

Open this repository as the workspace. Ask the agent to use `$building-services-design` with your brief and original drawings. Project skills are in `.agents/skills`. The intake skill creates a requirement matrix before design; domain skills select the appropriate authoring and analysis tools. This repository uses the host agent's reasoning; it does not require or hide a separate paid model API.

## Current evidence and limits

[Candidate route search](docs/ROUTE_SEARCH.md) now derives planar finite-grid pipe paths around sourced rectangular obstacles, with explicit finite-radius bends and conservative outside-wall clearance. A separate compiler carries the searched route into source-bound hollow IFC/ports and pressure calculations. Fixed-bore prescribed-flow pressure optimisation retains the length baseline, derives a per-bend loss objective and reopens the selected native IFC; low-supply failures remain explicit. Full spatial coordination, broader optimisation, native drawings and engineering acceptance remain pending.

An explicit obstacle stage now appends sourced footprint/height boxes to a separate IFC copy while preserving original entities. The selected synthetic route and obstacle passed actual six-element material/100 mm clearance checks; a deliberately moved obstacle produced a detected solid overlap. Real obstacle completeness, product applicability, native drawings and full acceptance remain pending.

[Saved route annotation auditing](docs/SAVED_ROUTE_AUDIT.md) now checks actual DXF leaders and source-linked labels independently of the planner's status claims. Injected false-success plans, crossings, self-intersections, changed labels, coverage gaps and hidden/nonplotting annotation flags are rejected, including raw paper-space markers that the reader would normalize; native pipe and printed/visual gates remain separate.

[An independent vertical elbow riser](docs/ELBOW_RISER.md) now reuses the source-linked geometry/pressure/clash/native pipeline with different dimensions, coordinates, gravity and namespace. It exposed a leader crossing missed by the first example; conservative annotation routing now checks OD/prior-leader avoidance and saved DXF paths. Actual insufficient-supply failures block downstream output. Product and full installation acceptance remain pending.

[Planar route drawings](docs/IFC_ROUTE_DRAWINGS.md) now carry source-checked finite elbows and straight walls into true-arc/OD-outline DXF, GUID-linked schedules, independently reopened AutoCAD DWG and fixed-scale A4 PDF. Actual world bounds catch shifted solids with unchanged ports; inspected-sheet evidence remains separate from full installation acceptance.

[Finite circular elbows](docs/CIRCULAR_ELBOWS.md) now connect source-parametric hollow IFC4 walls and exact arc references to directed tree pressure calculations. Saved geometry and excess-K reconciliation preserve physical bend length; independent laminar pressure and tamper checks cover the synthetic route. A source-linked coordination workflow also checks the same saved IFC, both outside-joint clearances and unwaivable material overlaps, with curved-bore and intrusion regression controls. Product, viewer and installation acceptance remain pending.

[Annual EPW analysis](docs/ANNUAL_ENERGY.md) executes complete hourly calendar years with OpenStudio/EnergyPlus, explicit multi-space box geometry and reciprocal shared-face/zone-key checks, weather hashes/site checks, monthly/annual reconciliation and unmet-zone-time targets. Attributed Chicago TMY3 data makes the synthetic example reproducible; thermal supply and lighting electricity stay separate. [Native completion diagnosis](docs/ENERGY_COMPLETION.md) now explains the inspected executable's unwritten SQL flags through pinned source/binary evidence while rejecting actual failures and unknown exceptions. [Saved IFC-space binding](docs/THERMAL_BINDING.md) now derives box geometry from actual solids and placements with complete GUID coverage and explicit north axis. [Explicit opaque layers](docs/THERMAL_MATERIALS.md) now replace fixed synthetic mass defaults with sourced role assemblies and saved property/order/provenance audits. [Weekly operation](docs/THERMAL_OPERATION.md) adds sourced lighting/equipment/occupancy, fixed scheduled outdoor air, saved-profile audits and independent hourly/annual electricity/count checks. [Actual fixed-size PTACs](docs/THERMAL_HVAC.md) now replace ideal loads with sourced DX/electric-heat/fan components, saved-curve/topology audits and native electricity reconciliation. [Saved HVAC equipment binding](docs/HVAC_DEVICES.md) now checks device/system/space GUIDs and ratings and creates a property-only analysis IFC with source-bound operating results. [HVAC equipment drawings](docs/HVAC_DRAWINGS.md) now carry verified device geometry/results through a GUID-linked plan/CSV to reopened native DWG and physically checked A4 PDF. [Sourced thermal windows](docs/THERMAL_WINDOWS.md) now add explicit exterior rectangles/glazing, saved geometry/net-area audits and native hourly solar/heat-gain/loss accounting. Real building/plant applicability remains pending.

[EPANET water graphs](docs/WATER_GRAPHS.md) solve steady loops, parallel pipes and pressure-driven demand through pinned WNTR 1.5.0 / EPANET 2.2. Signed flows, static heads, source pump intersections and converged target failures are retained. Independent scalar friction/minor energy residuals and reservoir boundaries detect errors that preserve mass balance. [Saved IFC water binding](docs/WATER_BINDING.md) now derives hollow-pipe dimensions, chain lengths and node elevations through GUID/topology mappings, with reversible ports and signed per-piece results. Static-head graphs remain distinct from older total-pressure tree bindings; actual products, fittings, physical coordination and full acceptance stay pending.

The electrical slice implements load aggregation, design current and conditional cable/protection/voltage-drop checks, plus a DXF overlay. Cable ampacity, factors, mV/A/m and limits are explicit sourced inputs, not embedded regulation tables. [Conditional TN fault verification](docs/ELECTRICAL_FAULTS.md) now checks supplied hot loop, total-clearing, standalone capacity and CPC let-through bounds; missing source guarantees stay pending. Actual source/code applicability, selectivity and full protection acceptance remain unresolved. Separate adapters below provide IES photometry, IFC, energy and network analysis; a successful tool run is not full design acceptance.

Native conversion and source-drawing intake use tested AutoCAD 2027 adapters. [Supported base overlays and fixed-scale A4 plots](docs/CAD_OVERLAY.md) now preserve checked source geometry and verify a reference line's physical PDF scale. Arbitrary drawing fidelity, full sheet standards and engineering acceptance remain pending. See [roadmap](docs/ROADMAP.md), [project format](docs/PROJECT_FORMAT.md), and [upstream attribution](THIRD_PARTY.md).

[Orthographic IFC drawing sets](docs/IFC_VIEWS.md) now combine plan/elevation views with explicit end-on pipe symbols, preserving true/projected lengths and GUIDs. The water-ring workflow extends through three reopened native DWGs and fixed-scale PDF sheets; complete installation detail and engineering acceptance remain pending.

## Native AutoCAD example

```powershell
.venv/Scripts/python -m bsa.native_cad runs/office/devices.dxf --out runs/native-office
$env:BSA_TEST_AUTOCAD='1'
.venv/Scripts/python -m unittest discover -s tests -v
```

Requires a licensed local AutoCAD 2027 installation at the default path (or pass `--exe`). Core Console runs on generated copies in isolated processes, never attaching to the GUI session. The adapter saves DWG, reopens it in a second process, checks CIRCLE/TEXT geometry, layers, labels and metre units, then plots a padded fit-to-page PDF. It refuses output overwrite. `native-verification.json` keeps visual review pending until a separate actual image inspection is recorded. This restricted overlay workflow does not yet merge existing base drawings, produce fixed-scale sheets or validate all CAD entity types.

## Real energy-engine example

```powershell
.venv/Scripts/python scripts/setup_energy.py
.venv/Scripts/python -m bsa.energy examples/two-zone-energy/project.json --out runs/energy --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python scripts/probe_openstudio_mcp.py runs/energy/baseline/model.osm
```

Bootstrap is Windows x64 only, verifies the portable engine archive checksum and uses an inspected upstream MCP commit. It changes only this workspace. `pip install -e ".[energy]"` installs the optional SDK when an engine is already available.

The current energy adapter is a two-zone design-day workflow: OSM + IDF creation, shared-wall matching, real EnergyPlus execution, SQL results and baseline/variant comparison. All example inputs are synthetic. It reports coincident thermal peaks and simulated-period quantities separately from lighting electricity. It does **not** report annual kWh, EUI, plant electricity or a finished HVAC layout. Original input and engine/artifact hashes, translation warnings and simulation logs are retained. The MCP probe exercises upstream model reading; it does not claim upstream simulation execution.

## Brief-to-tools workflow

After a run, use `python -m bsa.workflow_status <plan.json> <run-directory>` for an integrity-checked task handoff: direct and upstream blockers, associated requirements, retained evidence and next review/correction actions. It preserves pending/failed states and never launches engines or approves a design.

Use `python -m bsa.workflow intake <brief.md> --out <new-intake.json>` to index source passages. The host AI then creates a quoted, source-linked plan and project data. `validate` checks the handoff; `execute` dispatches electrical/native-CAD/energy tasks and creates an evidence matrix; `verify` detects changed inputs or task artifacts. See [workflow contract and runnable combined example](docs/WORKFLOWS.md). The combined example has been executed against actual AutoCAD and EnergyPlus. Manual review remains pending, so it is not an accepted final design.

[Delivery review records](docs/DELIVERY_REVIEW.md) now pin every source requirement and the exact run, cite original artifacts/render attachments, and keep pass/fail/pending findings separate from execution. Stale data, omitted requirements and false Boolean facts fail the audit. The synthetic demonstration retains actual numerical/SVG review evidence while missing fault-protection inputs remain pending; review consistency is not engineering certification.

## PDF and Word requirements

[Document intake](docs/DOCUMENT_INTAKE.md) supports PDF page locators, Word body/table/header/note locators and optional offline OCR. Extraction gaps remain visible and require source review. Scanned/outlined text can be OCR-indexed, but recognition is never silently accepted as engineering data.

[Drawing intake](docs/DRAWING_INTAKE.md) inventories source DXF or isolated AutoCAD DWG exports without changing source bytes. Explicit hash-bound selections can measure straight horizontal polygons after an independent dimension check. Nested/unsupported geometry and semantic or visual acceptance remain unresolved.

## Editable IFC MEP models

[IFC authoring](docs/IFC_MODELS.md) creates source-linked IFC4 spaces, device envelopes, distribution-system membership and directed port connections. Electrical and ventilation examples have been generated, reopened and checked through the geometry engine and schema/EXPRESS validator. Use the `bim` workflow adapter or `python -m bsa.bim`. Detailed product geometry, physical routing and engineering acceptance remain pending.

## Duct and pipe pressure analysis

[Network calculations](docs/NETWORKS.md) aggregate prescribed flow through circular tree networks and report friction, fittings, elevation, residual total pressure and the critical path. The `network` workflow adapter has air and water examples with independent formula tests. Loops, operating-point selection, physical routing and domain compliance remain outside this adapter.

[Model/network binding](docs/NETWORK_BINDING.md) derives straight circular route lengths, node elevations and explicit internal diameters from model ports/properties, generates IFC and independently reconciles its saved geometry with the derived pressure input. Physical junction detail and full engineering acceptance remain pending.

[Conditional sizing and iteration](docs/NETWORK_DESIGN.md) retains an undersized baseline, evaluates every permitted finite-catalogue size combination, preserves failures and reruns the selected feasible network. It optimises the supplied length-weighted material score under fixed demand/route/K assumptions; it does not invent product data, prices or a fan/pump operating point.

[Model-aware sizing](docs/NETWORK_MODEL_DESIGN.md) now applies explicit outside-envelope sizes to a new IFC revision while preserving source endpoints. Space-contained choices feed sizing; saved model bounds, stable device/port identities and model-derived pressure are checked. Product geometry, clashes and complete engineering acceptance remain pending.

[Straight circular wall solids](docs/CIRCULAR_GEOMETRY.md) opt into actual hollow IFC profile extrusions with independent inner/outside diameters. Native mesh topology, bore, annular wall volume, bounds and outward port axes are checked, including after sizing. Other equipment remains explicit envelopes; fittings, materials, clashes and full acceptance are pending.

[Saved IFC coordination](docs/CLASH.md) adds triangle clearance queries and Manifold3D Mesh64 solid intersections. It detects aligned overlap/full containment and distinguishes a tube's empty bore from its bounding box. Sourced contact exceptions remain visible and cannot waive solid overlaps; incomplete geometry and broader product/engineering acceptance stay pending.

[Independent water-riser reuse](examples/water-riser/README.md) runs a new synthetic source-linked brief through unchanged electrical, IFC sizing and clearance adapters: two vertical hollow pipe bodies, gravity pressure, four catalogue choices, retained failures and an editable electrical overlay. The separate water/electrical assumptions and pending drawing/product/engineering gates remain explicit.

[Saved IFC schedules and diagrams](docs/IFC_DRAWINGS.md) derive hollow-segment dimensions, true lengths and directed endpoints from saved native profiles/ports, then generate a GUID-linked CSV and projected centreline DXF. Unsupported segments fail coverage; omitted equipment and native/installation drawing gates remain explicit. The water-riser delivery plan includes this adapter.

The water-riser `native-plan.json` adds isolated AutoCAD save/reopen, complete model entity/IFC GUID reconciliation and an actual 1:50 A4 PDF reference check. The synthetic PDF has been rendered and visually reviewed; this verifies the diagram's scoped native delivery, with equipment/fittings and complete installation drawing standards still pending.

[Pump operating points](docs/PUMPS.md) now solve a supplied fixed-speed curve against a single fixed-pressure terminal line, using model-derived pipe dimensions and recomputed friction. Source curve/bracket limits, convergence, design-flow/velocity checks and a selected rerun are retained. Explicit combined wire-to-water efficiency permits an electrical-input estimate; the electrical project is not automatically revised or accepted. Real product/NPSH/control and branched/looped systems remain pending.

[Pump/electrical binding](docs/PUMP_ELECTRICAL.md) now carries that estimate into an explicitly bound operating scenario and saved pump IFC properties. Source replay, actual pump/connected-port identity, body-centre XY, unchanged baseline hardware/original IFC entities and saved properties/schema are checked. The eight-task coupled example rechecks/draws the revised model; baseline loads, other devices and motor/protection acceptance remain distinct.

## Shared electrical data

[Coordinated generation](docs/COORDINATION.md) now feeds the same device/circuit data into calculations, DXF and IFC. A geometry companion only adds explicit dimensions, heights and spaces. Reopened artifacts are reconciled; the workflow can send the resulting DXF through native AutoCAD save/reopen/plot. No separate power, PF, XY or circuit copy is maintained in geometry inputs.

## Real photometric engine

[Lighting analysis](docs/LIGHTING.md) runs official Radiance against sourced IES files, computes direct/reflected sensor illuminance and checks a higher-quality verification run. A synthetic fixture has been checked against the inverse-square/cosine law and maintenance scaling. Arbitrary geometry, glare/daylight and full lighting acceptance remain pending.

[Shared lighting binding](docs/LIGHTING_BINDING.md) now reuses electrical/CAD/IFC fixture IDs and positions in Radiance, with explicit photometric offsets and nominal IES/electrical watt checks. The combined synthetic workflow has executed optical analysis and native AutoCAD conversion; physical and visual acceptance remain pending.
