---
name: mep-ifc-mcp
description: Inspect saved IFC models and add source-backed pump text properties through the verified isolated official IfcMCP runtime. Use for IFC inventory and metadata handoff; route geometry, calculations and drawings to their verified domain tools.
---

# IFC queries and pump metadata through MCP

Use this repository's official IfcMCP integration for a saved IFC inventory or a new sourced text property set on an existing pump. Read docs/IFCMCP_TRIAL.md for the installed package names, version lock and observed protocol limitations. Run from the repository root using tools/ifcmcp-runtime/Scripts/python; keep the established .venv engineering runtime unchanged.

## Choose the operation

For an inventory, run:

```powershell
tools/ifcmcp-runtime/Scripts/python scripts/probe_ifcmcp.py --model <source.ifc> --out <new-run-directory>
```

Inspect trial.json, not merely process exit. Require protocol_checks_pass and source_unchanged. The report contains schema/entity counts, selected pumps/pipes and a spatial tree, with selection IDs/names checked against the saved model. STEP IDs are local to that file; use the actual GlobalId when preparing a modification. Empty selections can be valid inventories but cannot satisfy a requirement that equipment exists. Source absence, semantics and product truth remain separate findings.

For requested pump text metadata, prepare a source-backed JSON patch:

```json
{
  "guid": "<actual existing IfcPump GlobalId>",
  "pset": "<new project property-set name>",
  "source": "<document and page/section, or explicit scenario assumption>",
  "properties": {"ReviewStatus": "Pending review"}
}
```

Run:

```powershell
tools/ifcmcp-runtime/Scripts/python scripts/ifcmcp_pump_properties.py --model <source.ifc> --patch <patch.json> --out <new-run-directory>
```

The patch supports nonempty text values only; Source is reserved. Do not encode calculated equipment ratings as text to evade unit/rating contracts. Existing property sets are rejected rather than overwritten. Use the requested pump identity and scope; do not copy the synthetic example's GUID or source into another assignment.

Require all edit-checks.json checks: original entity records unchanged, only property entities added, relationship assigned solely to the requested pump, exact saved values, unchanged source hashes and schema. Preserve calls.json and the new model.ifc. A failed upstream edit may arrive with MCP isError=false and an inner ok=false; the provided adapter handles both. Do not issue raw save calls with an empty path, which would overwrite the loaded file.

## Route the rest of the assignment

The inventory is also registered as workflow kind ifc_query with requirements plus either ifc or depends_on on an earlier IFC producer. Supply --ifcmcp-python explicitly to the workflow CLI. Read docs/IFCMCP_TRIAL.md for the positive minimum-count contract; missing runtime remains pending and unmet counts fail. The property editor remains standalone; neither tool implies a live host MCP registration. Keep source/run reports with the assignment. New or changed physical equipment, curves, systems, geometry, dimensions and operating conditions need the existing source-bound authoring/calculation adapters and fresh downstream checks.

Use ../mep-ifc-authoring/SKILL.md for supported geometry and drawings; ../mep-network-analysis/SKILL.md for hydraulics; ../mep-delivery-check/SKILL.md for acceptance. This machine's IfcMCP 0.9.0 OpenCascade DLL is blocked by application control, so its plot/render/geometry claims are not an available drawing path. Do not retry blocked binaries or change policy as a routine task. Existing query/property evidence remains valid independently. Neither successful metadata mutation nor a complete inventory approves engineering design or Hong Kong compliance.

For workflow inventory prerequisites, inspect inventory_source_bindings. Supported downstream IFC readers must use identical explicit file bytes or the same inherited producer, including through intermediate prerequisites. Query a deliberately revised model again; do not borrow an earlier model's passing inventory. This correspondence check does not prove arbitrary downstream behavior or geometry correctness.
