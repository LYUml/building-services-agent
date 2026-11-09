# Revit adapter and MOOSAS reference review

Reviewed 2026-11-09 at the user's request. Revit is a planned native authoring/delivery adapter alongside AutoCAD and IFC; performance engines and jurisdiction rules remain independently replaceable. Revit installation is not adapter acceptance.

## Local evidence and adapter sequence

Latest read-only Windows UI observation still finds Revit at Home and a separate DIALux project window with an unsaved marker. No foreground activation, click, model open or add-in registration was performed. The displayed Autodesk `Samples/Snowdon Towers Sample Plumbing.rvt` is now copied into ignored `runs/revit-sample-inventory-v1/plumbing-test.rvt` (40,624,128 bytes); source and copy SHA256 match, with attribution/hash recorded in that run's `source.json`. A read-only manifest/request was prepared at `runs/revit-sample-inventory-v1/command`, targeting the actual copied RVT rather than the earlier nonexistent empty test model. This is a real-model test fixture, not native execution evidence or an engineering basis. The Autodesk sample is local-only and is not redistributed. Loading the current adapter, opening this copy, capturing inventory and verifying source preservation remain pending desktop coordination.

The [official DynamoMCP guide](https://primer2.dynamobim.org/12_ai_tools/1-what-is-dynamo-mcp) describes Autodesk Assistant as the entry point, with no standalone interface. Its advertised graph-query/run tools therefore do not establish an external agent connection to the bundled package. Preserve manual graph execution as the pending local verification path; do not infer a public HTTP/stdio endpoint from the installed DLLs.

Inventory preparation v2 rejects unsaved modifications before native API access and hashes the saved RVT before/after collection. Generated reports include the RVT and inventory-script hashes; these identify disk bytes, not proof of complete model semantics. Five document rejection controls passed outside Revit, and generated embedded code compiles. Native execution remains pending. The graph at `runs/revit-inventory-graph-v2/inventory.dyn` supersedes v1 for the planned test. Desktop control again detected DIALux over the intended Revit click and refused input; desktop timing has been asked asynchronously, with no further GUI actions until resolved.

`scripts/prepare_revit_inventory_graph.py --model runs/revit-native-v1/test.rvt --out runs/revit-inventory-graph-v1` now prepares a manual-run PythonNet3 Dynamo graph with the original inventory code embedded and hashed. It requires an expected repository-local RVT path, refuses an existing output directory, and creates inventory.json exclusively when run inside Revit. It performs no model edits. Preparation, embedded Python compilation and three path/output rejection checks passed; Dynamo loading and native inventory execution remain unverified. The named test RVT has not yet been created. The local bundled Core_Python.dyn was inspected only for JSON schema (no example code copied); bundled PythonNet3Engine metadata is version 1.4.8.0. UI execution was deferred when Revit window metadata and captured DIALux imagery disagreed during concurrent desktop activity; no coordinate actions were taken against that mismatched capture.

Live startup on 2026-11-09 reached the Revit 2027.3 Home screen, labelled EDUCATION (NON COMMERCIAL), with Models Open/New controls visible and no authentication action needed. No model was opened or edited, and no add-in was installed. This verifies application startup only, not model/API access or the broader licence entitlement. The running session was left open. Local RevitAPI.runtimeconfig.json specifies net10.0 with Microsoft.NETCore.App, WindowsDesktop.App and AspNetCore.App 10.0.0; the inventory script now records this configuration and its hash. Candidate bridges targeting net8.0 need actual compatibility verification, not an assumed match to the Revit release number.

`scripts/inspect_revit.ps1 -Out runs/new-revit-inventory.json` performs reproducible read-only installation checks without launching Revit or changing client configuration. The executed inventory found DynamoMCP 0.5.6.0 (Dynamo engine 4.2), but no Public MCP executable at the three documented installation paths and no running Revit process. This bounded path check does not exclude a custom installation elsewhere.

Official [setup documentation](https://help.autodesk.com/cloudhelp/ENU/ADSKMCP-RevitMcp/files/ADSKMCP_RevitMcp_setting_up_revit_mcp_server_html.html) specifies a separate add-on and a running model. It names 2027.2, while an Autodesk forum response says 2027.2 and later; compatibility with installed 27.3 remains to be verified. Obtain the entitled installer through [Autodesk Account Extensions](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-download-the-Revit-MCP-server.html), not an assumed bundled executable. No account access or installation was performed.

The reviewed [official tool table](https://help.autodesk.com/cloudhelp/ENU/ADSKMCP-RevitMcp/files/revitmcp_tools.html) covers active context, queries, element data, parameter edits and experimental views/sheets/schedules/IFC export. It does not list native duct/pipe/connector creation. Therefore MCP installation alone cannot satisfy our MEP-authoring milestone. Evaluate a narrowly scoped API bridge for that gap. Its room-boundary tool simplifies nonlinear segments, so those outputs must not silently replace curved geometry in analysis.

Read-only filesystem inspection found `C:/Program Files/Autodesk/Revit 2027/Revit.exe` and `RevitAPI.dll`, both file version 27.3.0.28. No Revit session was opened, add-in installed, document edited or licence availability established.

Autodesk's [September 2026 announcement](https://forums.autodesk.com/t5/revit-api-forum/revit-mcp-server-tech-preview-launch/td-p/14262015) describes Read, Trusted-Write and Experimental MCP capabilities. Evaluate official availability and supported operations first. The independent [rui-branco/revit-mcp](https://github.com/rui-branco/revit-mcp) MIT bridge is another research candidate, not an installed or verified integration. App Store publication alone does not make a third-party bridge Autodesk-authored.

The [Revit External Events API](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API/files/Revit_API_Developers_Guide/Advanced_Topics/Revit_API_Revit_API_Developers_Guide_Advanced_Topics_External_Events_html.html) describes requests raised for execution in Revit's valid API context. Verify the actual bridge's API-context handling and document identity before writes.

Implementation acceptance sequence:

1. Read active document identity, units, levels, spaces, MEP categories, families/types, connector/system data and stable element identifiers. Detect linked versus editable objects.
2. Map those objects to source-linked project data; keep Revit internal units and project display units distinct. Preserve analysis/model correspondence through a saved mapping.
3. On a new synthetic project, create a bounded system with actual Revit MEP objects and connectors, not only generic solids. Verify transactions, rollback and saved reopening.
4. Generate a view, schedule and sheet; reconcile element counts/identities and inspect actual PDF/DWG exports.
5. Recompute supported performance/rules after revisions; preserve product, installation and professional checks. Native RVT acceptance requires actual Revit readback, not IFC export success alone.

## Independent Revit bridge source check

Inspected `rui-branco/revit-mcp` at commit `0a99726d2fc95f71c24b373cbd74bda0d5e907d8` (MIT, copyright Rui Branco). Selected source hashes are in `docs/evidence/moosas-review/revit-mcp-source-review.json`; the checkout is local under ignored tools, not installed or executed. The local dotnet host returned no installed SDKs.

The advertised `revit_create_pipes` endpoint routes to `DirectShapeEndpoints.CreatePipes`: it builds cylinders per route segment and passes them to DirectShape construction. Category may fall back from PipeCurves to GenericModel. It does not create native Plumbing.Pipe objects or MEP connectors. Its default radius must not become an assumed engineering diameter. This endpoint is unsuitable for our native system/connectivity acceptance despite its tool name.

The ExternalEvent queue is a useful reference for valid API-context execution. It distinguishes a request abandoned before execution from a timeout after execution started; our future caller must read back state before retrying an uncertain write. The package also auto-installs by default (`REVIT_MCP_NO_AUTO_INSTALL=1` opts out), and advertises dialog dismissal. Do not launch it casually as a read-only probe or import those defaults into the user session. Evaluate query/export and transaction plumbing separately from the missing native MEP authoring. No source implementation has yet been copied into this repository.

## MOOSAS source details

### Native airflow interoperability probe

`scripts/probe_moosas_airflow.py` exercises the pinned upstream's synthetic JSON-network fixture through MoosasAFN project generation, then CONTAM only if generation succeeds. The fixture is attributed to the Apache-2.0 upstream test; its dimensions, volume, opening coefficients and solver defaults are interoperability inputs, not an engineering design or Hong Kong basis. The script requires a clean exact upstream commit and a fresh repository-local workspace, retains executable/input/output hashes and raw process diagnostics, and uses a bounded child process without modifying application-control settings.

Actual run `runs/moosas-airflow-probe-v1` produced network.json, but Windows refused to launch MoosasAFN.exe with WinError 4551 (Application Control). No CONTAM project was produced and CONTAM was therefore **not attempted**; its present runtime availability remains unknown. Evidence is `docs/evidence/moosas-review/airflow-runtime-probe.json`. Geometry exchange remains independently verified; native airflow simulation, result parsing, conservation checks and sourced opening/pressure/temperature binding remain pending. Do not infer an airflow opening from geometric space contact or adopt the upstream automatic leakage coefficient as measured input.

```powershell
.venv/Scripts/python scripts/probe_moosas_airflow.py --upstream tools/moosas-review --out runs/new-moosas-airflow-probe
```

### Executed ordinary-IFC loading trial

Follow-up: explicitly invoking the upstream internal geometry bridge also failed on the same IFC (`No geometry could be extracted from IFC`); its traversal excludes IfcSpace geometry. Evidence: `geometry-bridge-trial.json`.

A separate original adapter now reuses BSA's saved-solid box validator and MOOSAS's model/space/surface and XML/GEO APIs: `scripts/moosas_space_exchange.py`. Actual three-space export and reload preserve source GUIDs, all face vertex sets (to 1e-9 m), areas 48/30/24 m2, 3 m heights, closedness and input hashes. An omitted-space mapping fails before export. Evidence: `space-exchange.json` and `space-exchange-negative.json`. This is successful bounded geometry exchange, not ordinary upstream IFC-loader acceptance or a simulation-ready thermal model. Perimeter planes are space envelopes, not asserted physical wall constructions; shared/interzone boundary semantics, north-axis/georeferencing, materials, gains and HVAC remain unresolved.

The follow-up per-space audit independently constructs the six expected boundary vertex sets from the saved IFC extraction, and checks each reloaded space's floor, ceiling and four wall identities/coordinates. The positive v3 exchange passes (`space-boundary-exchange.json`). An executed control swaps one wall reference between two reloaded spaces while retaining their GUIDs, areas, heights and all global geometry; both affected spaces are now rejected and the third remains valid (`boundary-ownership-control.json`). This closes a correspondence gap that aggregate geometry/count comparisons could miss. The control changed only in-memory objects, not the saved positive artifacts. Surface winding, adjacency and thermal-boundary classification remain separate requirements.

The v4 exchange additionally reuses `bsa.thermal_geometry` to reject overlapping/partial-face box arrangements and derive whole-face contacts. Each interface records both space GUIDs, boundary surface IDs, axis and area; both reloaded surface vertex sets must coincide. Actual Office/East and East/Annex contacts each preserve 18 m2 (`space-contact-exchange.json`). Four pure geometry tests cover reversed ordering, horizontal and stacked face identities, overlap/partial-contact rejection, separated boxes and edge-only contacts. These tests are independent of the blocked energy runtimes. The contact records deliberately do not assign thermal boundary conditions, physical partitions or airflow openings; those need additional sourced inputs and simulation-specific binding.

The isolated optional dependencies are rdflib 7.1.4 and pyparsing 3.2.3, installed under ignored `tools/moosas-exchange-deps` with their distribution notices retained; the repository environment was not upgraded. The sparse pinned upstream checkout now includes its db/template directory and licence. Its bundled library.json lacks the version 5 field required by its current reader, so default XML reload fails. The wrapper explicitly selects an empty version-5 catalogue during geometry-only reload and restores the module setting afterward; it does not change upstream files, fabricate a GB/HK template, or execute analysis. Upstream Apache-2.0 attribution remains to KLEGB/MOOSAS and its authors; adapter code is original.

```powershell
.venv/Scripts/python -m pip install --target tools/moosas-exchange-deps --no-deps rdflib==7.1.4 pyparsing==3.2.3
.venv/Scripts/python scripts/moosas_space_exchange.py --ifc runs/moosas-ifc-trial-v1/source/model.ifc --binding examples/thermal-ifc/binding.json --upstream tools/moosas-review --deps tools/moosas-exchange-deps --out runs/new-moosas-exchange
```

Pinned upstream was checked out under ignored `tools/moosas-review`, without installing its dependency set or fetching bundled simulation engines/templates. Its IFC module imports successfully with the existing repository Python dependencies. A fresh native `bsa.bim` run of `examples/thermal-ifc/bim.json` produced a schema-checked IFC4 containing three spaces and two distribution elements, with metre units and source preservation checks passing.

Actual `loadIfc` execution returned zero spaces, zero faces and zero walls without raising, while reporting `ifcHasSpaces=True` and `ifcLoadMode='space'`. The source bytes stayed unchanged. Inspection of `_legacy_loadIfc_direct` explains this specific case: elements/spaces lacking its MOOSAS property set are skipped, and empty output does not trigger the exception-based fallback. This proves an incompatibility for our ordinary synthetic space IFC, not that all upstream IFC inputs fail. Its round-trip format and geometry bridge need separate evaluation.

`scripts/probe_moosas_ifc.py` now repeats this diagnostic against the exact clean pinned checkout and records original space GUIDs plus loaded counts. Executed evidence is `docs/evidence/moosas-review/ifc-loader-trial.json`; the mismatch is retained as failure, never promoted to simulation readiness. Count equality alone would still not prove identity, geometry, units, boundaries or thermal fidelity. Existing BSA source-validated thermal extraction remains the available geometric binding; do not route generic IFC automatically through this MOOSAS loader. No upstream source was patched, vendored or redistributed, and no simulation was run.

```powershell
.venv/Scripts/python scripts/probe_moosas_ifc.py --upstream tools/moosas-review --ifc runs/moosas-ifc-trial-v1/source/model.ifc --out runs/new-moosas-ifc-probe.json
```

### Native plumbing reference and inventory preparation

Reviewed [Thaynabarreiro/revit-hydro-designer](https://github.com/Thaynabarreiro/revit-hydro-designer/tree/c08b5a0f12e40110e230338fce3e55c6781f302b) at the linked commit (MIT, copyright Thayna Barreiro). Source hashes are retained in `revit-hydro-source-review.json`. Its `tools/m6g_rede_final.py` uses native Pipe.Create and NewElbowFitting/NewTeeFitting, making it a closer authoring reference than the DirectShape bridge. However, its initial transaction deletes all project PipeCurves/PipeFitting elements, and connection fallback counts success without a final topology readback. Do not execute that script in a user model or inherit those acceptance semantics. Its NBR calculation assumptions are not Hong Kong regulatory evidence. No upstream implementation was copied or run.

Added original `scripts/revit_inventory.py` as a read-only callable for a valid Revit API context: `inventory(doc, expected_saved_path)`. It rejects missing/mismatched document paths and family documents before importing the API. It returns native pipe identities, types, system identities, lengths/diameters and connector references, converting internal lengths through UnitUtils. References may include logical links and do not prove physical connection; linked-model contents, fixtures, ducts and full system acceptance are outside this first inventory. The caller controls serialization; the module opens no files and starts no transactions. Python syntax was checked locally; actual Revit invocation, binding compatibility and saved-model comparison remain unverified. This is preparation, not an available production adapter.

Pinned [KLEGB/MOOSAS](https://github.com/KLEGB/MOOSAS/tree/dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c), develop commit `dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c`. Current README describes a standalone MoosasPy core, not only SketchUp integration. Reviewed modules separate geometry transformation, model I/O and simulation; explicit coupling connects energy/airflow workflows. Shared results retain native command/workspace diagnostics. Apache-2.0 is the root licence; bundled engines/templates have additional notices to review before reuse. Selected source hashes are retained in `docs/evidence/moosas-review/source-manifest.json`; source snapshots remain local, not vendored or executed.

Our application of these ideas:

- Keep Revit, AutoCAD and IFC bridges outside the calculation/rule core.
- Build an explicit common space/system model with source provenance and separate simulation requests/results.
- Give each engine a replaceable execution interface and retain actual failure diagnostics; never equate an empty command list with completed simulation.
- Use saved scenario inputs/results to compare revisions. MOOSAS template values are not Hong Kong regulatory evidence or user project facts.

Compatibility is unresolved: current MOOSAS docs target EnergyPlus 26.1 IDF input, while this repository's verified stack uses OpenStudio 3.11/EnergyPlus 25.2. Do not silently upgrade or pass files across incompatible adapters. First reuse candidates are geometry-to-space transformation, model exchange and airflow coupling, subject to isolated version-pinned tests. This review establishes architectural direction, not working integration or full MEP-system authoring by MOOSAS.
