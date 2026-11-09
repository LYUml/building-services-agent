# Revit adapter and MOOSAS reference review

Reviewed 2026-11-09 at the user's request. Revit is a planned native authoring/delivery adapter alongside AutoCAD and IFC; performance engines and jurisdiction rules remain independently replaceable. Revit installation is not adapter acceptance.

## Local evidence and adapter sequence

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
