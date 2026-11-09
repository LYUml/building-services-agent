# Official IfcMCP integration trial

The official IfcOpenShell project provides the server documented at https://docs.ifcopenshell.org/ifcmcp.html. The current published distribution name is **ifcopenshell-mcp**, while its Python module and executable are **ifcmcp**. The documentation's `pip install ifcmcp` spelling was not a working package endpoint during this review. Upstream source inspected at commit `6a5283ac797d2acc5ce2cbbde0fb544fea83f426` confirms the distribution name; this is a research snapshot, not a claim about the wheel build commit.

## Reproduction

Use a separate Python 3.12 environment so this 0.9.0 evaluation does not upgrade the established 0.8.5 engineering runtime:

```powershell
.venv/Scripts/python -m venv tools/ifcmcp-runtime
tools/ifcmcp-runtime/Scripts/python -m pip install -r docs/evidence/ifcmcp/requirements.lock.txt
tools/ifcmcp-runtime/Scripts/python scripts/probe_ifcmcp.py --model runs/hk-ifc-plumbing-v1/route/bim/model.ifc --out runs/new-ifcmcp-trial
```

Substitute an existing repository IFC path if the historical example run is unavailable. The probe invokes the upstream stdio server as a subprocess and closes it at the end. No user-level MCP configuration or application settings are changed. A client may use the isolated Python executable with arguments `-m ifcmcp`; the upstream server exposes editing/saving as well as queries, so the read-only nature of this trial is a property of the calls exercised, not an access-control claim.

## Observed evidence

The saved synthetic IFC4 route has 189 entities, one IfcPump and two IfcPipeSegment objects. Actual MCP initialization and a 25-tool inventory succeeded. Model loading, summary, class selections and spatial-tree retrieval returned successfully. Summary counts and selected STEP IDs/types/names match a direct reopening of the saved IFC. Queries before loading and after reset correctly returned errors. Original model SHA256 remained unchanged.

`docs/evidence/ifcmcp/trial.json` contains the protocol responses and seven explicit checks; server.log retains native server output. runtime.json records installed module hashes, package versions/license metadata and relevant published wheel hashes/URLs. requirements.lock.txt pins the observed Windows/Python 3.12 dependency set. No upstream implementation or binary is redistributed. The probe uses the official MCP Python client; it does not reimplement the protocol or IFC query engine.

The original trial verifies only query/session calls. The property-addition trial below additionally verifies one scoped API mutation. ShapeBuilder, native geometry/clash behavior, SVG/PNG drawing, rendering, IFC validation, arbitrary model performance and host-agent registration remain unverified. Query success is not engineering or regulatory acceptance. Keep current deterministic calculations and saved-model/drawing gates in place until those capabilities have independent evidence. The existing main runtime remains IfcOpenShell 0.8.5.


## Source-bound pump property addition

```powershell
tools/ifcmcp-runtime/Scripts/python scripts/ifcmcp_pump_properties.py --model runs/hk-ifc-plumbing-v1/route/bim/model.ifc --patch examples/ifcmcp/pump-properties.json --out runs/new-ifcmcp-edit
tools/ifcmcp-runtime/Scripts/python scripts/test_ifcmcp_properties.py
```

The original adapter reuses upstream ifc_docs, ifc_edit (pset.add_pset and pset.edit_pset), ifc_save, reset, reload and info calls. A patch explicitly names an existing IfcPump GUID, a new property-set name, source description and nonempty text properties. Source is a reserved provenance field. Existing sets cannot be overwritten; output is a new repository directory and original files remain untouched. This intentionally does not accept numeric equipment ratings or unit-bearing engineering values without a stronger typed contract.

The installed 0.9.0 server may return edit payloads as JSON text without structuredContent. It may also return MCP isError=false while the payload says ok=false. Both layers are inspected. IfcEdit's dictionary parameter coercion requires properties as a JSON string nested inside params; this is handled by the adapter without modifying vendor code. Native responses are retained even on failure.

Actual saved-model evidence is in docs/evidence/ifcmcp-edit/native-trial.zip. After adding review/provenance text to the synthetic booster, all 189 original STEP entity records remained identical. Only property entities were added, their relationship targets exactly the requested pump, and all saved values match the patch. Original source hashes and schema remain unchanged. The new file was reset/reloaded over MCP and independently reopened through IfcOpenShell. Regression execution also checks an existing-set overwrite and reserved-source override are rejected before output creation.

These checks prove a scoped metadata operation, not equipment truth, geometric authoring, new-model hydraulic validity, native drawings or regulatory conformity. Host registration and broader mutation remain pending. Use actual source-backed patch text for real assignments; the example is explicitly synthetic.


## 2D plot trial: blocked by host application control

```powershell
tools/ifcmcp-runtime/Scripts/python scripts/probe_ifcmcp_plot.py --model runs/hk-ifc-plumbing-v1/route/bim/model.ifc --cairo tools/freecad-1.1.4/FreeCAD_1.1.4-Windows-x86_64-py311/bin --out runs/new-ifcmcp-plot
```

Actual floorplan and elevation calls on the saved synthetic route both failed. Windows Code Integrity events 3077/3033 identify `ifcopenshell_geometry_kernel_opencascade.dll` from the isolated 0.9.0 runtime as failing the host signing policy. No PNG or SVG was created, and no visual acceptance is claimed. The input hash remained unchanged. Error responses, event messages, blocked binary SHA256 and the dependency lock are retained in docs/evidence/ifcmcp-plot.

The upstream MCP plot tool always generates PNG before saving an optional SVG, so this interface needs raster dependencies even for an SVG output path. CairoSVG 2.8.2 and Pillow 12.0.0 were installed only in the isolated environment. Cairo loaded successfully through cairocffi's documented CAIROCFFI_DLL_DIRECTORIES mechanism using the existing hash-verified official FreeCAD distribution's bin directory. The observed block occurred later in the separate IfcOpenShell OpenCascade geometry kernel. No blocked binary was substituted, repackaged or bypassed; no application-control settings were changed.

Do not route required drawings to this unexecuted geometry path. Existing verified native drawing adapters remain available in the established 0.8.5 engineering environment; query and text-property MCP capabilities retain their separate evidence. A future plot retry needs an authorized runtime/environment in which the geometry kernel can load. That prerequisite does not block unrelated project development.


## Requirement-linked inventory workflow

Task kind `ifc_query` accepts `requirements` plus exactly one of explicit `ifc` or `depends_on` referencing an earlier supported IFC producer. Pass the runtime path with `python -m bsa.workflow execute ... --ifcmcp-python tools/ifcmcp-runtime/Scripts/python.exe`. Runtime paths are execution configuration, not executable instructions accepted from brief content.

The requirements JSON has exactly `source` (nonempty provenance text) and `minimum_counts` (one or both of IfcPump/IfcPipeSegment, each a positive integer). For example: `{"source":"Synthetic inventory requirement","minimum_counts":{"IfcPump":1,"IfcPipeSegment":2}}`. The adapter calls the existing official-client query script, verifies protocol/source correspondence and pinned versions, then checks saved-model class counts. It retains IFC/contract/script/interpreter hashes and a protocol report hash in ifc-query.json.

Missing runtime or failed upstream IFC leaves the task pending. Unmet counts fail and explicit requires_pass consumers are blocked. Positive counts establish only class inventory, not equipment suitability, unique role assignment, geometry, completeness of the brief or compliance. A prerequisite alone does not prove arbitrary downstream consumers use the same IFC; declare the intended source/dependency explicitly. The inherited positive case, missing runtime, two-required/one-present failure, downstream blocking, source changes and forbidden simultaneous explicit/inherited sources have actual regression evidence in test_ifc_query_workflow.py.
