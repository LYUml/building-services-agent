# Revit adapter and MOOSAS reference review

Reviewed 2026-11-09 at the user's request. Revit is a planned native authoring/delivery adapter alongside AutoCAD and IFC; performance engines and jurisdiction rules remain independently replaceable. Revit installation is not adapter acceptance.

## Local evidence and adapter sequence

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

## MOOSAS findings

## Independent Revit bridge source check

Inspected `rui-branco/revit-mcp` at commit `0a99726d2fc95f71c24b373cbd74bda0d5e907d8` (MIT, copyright Rui Branco). Selected source hashes are in `docs/evidence/moosas-review/revit-mcp-source-review.json`; the checkout is local under ignored tools, not installed or executed. The local dotnet host returned no installed SDKs.

The advertised `revit_create_pipes` endpoint routes to `DirectShapeEndpoints.CreatePipes`: it builds cylinders per route segment and passes them to DirectShape construction. Category may fall back from PipeCurves to GenericModel. It does not create native Plumbing.Pipe objects or MEP connectors. Its default radius must not become an assumed engineering diameter. This endpoint is unsuitable for our native system/connectivity acceptance despite its tool name.

The ExternalEvent queue is a useful reference for valid API-context execution. It distinguishes a request abandoned before execution from a timeout after execution started; our future caller must read back state before retrying an uncertain write. The package also auto-installs by default (`REVIT_MCP_NO_AUTO_INSTALL=1` opts out), and advertises dialog dismissal. Do not launch it casually as a read-only probe or import those defaults into the user session. Evaluate query/export and transaction plumbing separately from the missing native MEP authoring. No source implementation has yet been copied into this repository.

## MOOSAS source details

Pinned [KLEGB/MOOSAS](https://github.com/KLEGB/MOOSAS/tree/dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c), develop commit `dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c`. Current README describes a standalone MoosasPy core, not only SketchUp integration. Reviewed modules separate geometry transformation, model I/O and simulation; explicit coupling connects energy/airflow workflows. Shared results retain native command/workspace diagnostics. Apache-2.0 is the root licence; bundled engines/templates have additional notices to review before reuse. Selected source hashes are retained in `docs/evidence/moosas-review/source-manifest.json`; source snapshots remain local, not vendored or executed.

Our application of these ideas:

- Keep Revit, AutoCAD and IFC bridges outside the calculation/rule core.
- Build an explicit common space/system model with source provenance and separate simulation requests/results.
- Give each engine a replaceable execution interface and retain actual failure diagnostics; never equate an empty command list with completed simulation.
- Use saved scenario inputs/results to compare revisions. MOOSAS template values are not Hong Kong regulatory evidence or user project facts.

Compatibility is unresolved: current MOOSAS docs target EnergyPlus 26.1 IDF input, while this repository's verified stack uses OpenStudio 3.11/EnergyPlus 25.2. Do not silently upgrade or pass files across incompatible adapters. First reuse candidates are geometry-to-space transformation, model exchange and airflow coupling, subject to isolated version-pinned tests. This review establishes architectural direction, not working integration or full MEP-system authoring by MOOSAS.
