# Revit adapter and MOOSAS reference review

Reviewed 2026-11-09 at the user's request. Revit is a planned native authoring/delivery adapter alongside AutoCAD and IFC; performance engines and jurisdiction rules remain independently replaceable. Revit installation is not adapter acceptance.

## Local evidence and adapter sequence

Read-only filesystem inspection found `C:/Program Files/Autodesk/Revit 2027/Revit.exe` and `RevitAPI.dll`, both file version 27.3.0.28. No Revit session was opened, add-in installed, document edited or licence availability established.

Autodesk's [September 2026 announcement](https://forums.autodesk.com/t5/revit-api-forum/revit-mcp-server-tech-preview-launch/td-p/14262015) describes Read, Trusted-Write and Experimental MCP capabilities. Evaluate official availability and supported operations first. The independent [rui-branco/revit-mcp](https://github.com/rui-branco/revit-mcp) MIT bridge is another research candidate, not an installed or verified integration. App Store publication alone does not make a third-party bridge Autodesk-authored.

The [Revit External Events API](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API/files/Revit_API_Developers_Guide/Advanced_Topics/Revit_API_Developers_Guide_Advanced_Topics_External_Events_html.html) describes requests raised for execution in Revit's valid API context. Verify the actual bridge's API-context handling and document identity before writes.

Implementation acceptance sequence:

1. Read active document identity, units, levels, spaces, MEP categories, families/types, connector/system data and stable element identifiers. Detect linked versus editable objects.
2. Map those objects to source-linked project data; keep Revit internal units and project display units distinct. Preserve analysis/model correspondence through a saved mapping.
3. On a new synthetic project, create a bounded system with actual Revit MEP objects and connectors, not only generic solids. Verify transactions, rollback and saved reopening.
4. Generate a view, schedule and sheet; reconcile element counts/identities and inspect actual PDF/DWG exports.
5. Recompute supported performance/rules after revisions; preserve product, installation and professional checks. Native RVT acceptance requires actual Revit readback, not IFC export success alone.

## MOOSAS findings

Pinned [KLEGB/MOOSAS](https://github.com/KLEGB/MOOSAS/tree/dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c), develop commit `dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c`. Current README describes a standalone MoosasPy core, not only SketchUp integration. Reviewed modules separate geometry transformation, model I/O and simulation; explicit coupling connects energy/airflow workflows. Shared results retain native command/workspace diagnostics. Apache-2.0 is the root licence; bundled engines/templates have additional notices to review before reuse. Selected source hashes are retained in `docs/evidence/moosas-review/source-manifest.json`; source snapshots remain local, not vendored or executed.

Our application of these ideas:

- Keep Revit, AutoCAD and IFC bridges outside the calculation/rule core.
- Build an explicit common space/system model with source provenance and separate simulation requests/results.
- Give each engine a replaceable execution interface and retain actual failure diagnostics; never equate an empty command list with completed simulation.
- Use saved scenario inputs/results to compare revisions. MOOSAS template values are not Hong Kong regulatory evidence or user project facts.

Compatibility is unresolved: current MOOSAS docs target EnergyPlus 26.1 IDF input, while this repository's verified stack uses OpenStudio 3.11/EnergyPlus 25.2. Do not silently upgrade or pass files across incompatible adapters. First reuse candidates are geometry-to-space transformation, model exchange and airflow coupling, subject to isolated version-pinned tests. This review establishes architectural direction, not working integration or full MEP-system authoring by MOOSAS.
