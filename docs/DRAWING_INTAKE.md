# Source drawing intake

`bsa.cad_intake` preserves source bytes and inventories model-space entities before geometry is used in design. It accepts DXF directly and DWG through an explicit local AutoCAD 2027 Core Console executable. DWG is copied into a new run folder; a full-path guard encloses DXFOUT. Core Console never attaches to the GUI session. Source and isolated DWG copy hashes must remain unchanged.

```powershell
python -m bsa.workflow execute examples/drawing-intake/plan.json --out runs/drawing-intake
python -m bsa.cad_intake source.dwg --selection reviewed-selection.json --out runs/dwg-intake --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe'
```

Inventory-only use may omit selection. `drawing_intake` workflow tasks use `drawing` plus optional `selection` relative paths. Both files join integrity records. A DWG task without an AutoCAD path stays pending. The DXF example works without AutoCAD.

The inventory records layers, units, type counts, handles and supported top-level LINE, LWPOLYLINE, CIRCLE/ARC, TEXT/MTEXT and INSERT data. Polyline vertices are converted from OCS to WCS via ezdxf. Block attributes are listed, but nested block geometry, external references, proxies and other unsupported entities are explicitly unresolved. No explosion, repair, unit conversion or source save is performed. Any detected DXF audit error/fix requires separate review. Paper-space layouts and viewports are not interpreted.

Measurements require a reviewed selection with the exact source drawing SHA256, a known LINE dimension and explicit area handles/IDs/provenance. Supported INSUNITS are inches, feet, millimetres, centimetres and metres; unitless/unhandled units block measurement. Header scale must agree with the independent known dimension within its stated tolerance. A changed drawing requires re-review and selection rebinding, even if handles survive.

Area uses selected simple, horizontal, closed, straight, zero-width LWPOLYLINE boundaries. Self-intersections, touching/nonplanar boundaries, curves and open outlines are rejected. Coordinates are recorded in world metres and area in square metres with exported DXF hash/handle evidence. Room meaning, gross/net area, wall offsets and holes are never inferred. An inventory is not a semantic building model; use source review before transferring a measured area into common project data.

The L-shaped millimetre fixture has independently known area `6*2 + 3*2 = 18 m2`. Actual AutoCAD export tests preserve its native source and reproduce this area. They do not prove arbitrary DWG fidelity, original drawing quality, base/overlay integration or plot acceptance. Those gates remain pending.

Upstream references: [ezdxf LWPOLYLINE coordinate contract](https://ezdxf.readthedocs.io/en/stable/dxfentities/lwpolyline.html) and [Autodesk DXF output API reference](https://help.autodesk.com/cloudhelp/2026/ENU/OARX-ManagedRefGuide/files/OARX-ManagedRefGuide-Autodesk_AutoCAD_DatabaseServices_Database_DxfOut_string_int_DwgVersion.html). The tested adapter uses the native DXFOUT command and records its actual command log; the API reference is not a claim that this adapter uses .NET. Existing ezdxf attribution/license applies; no additional library is vendored.
