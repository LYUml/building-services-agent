# Source-bound HVAC equipment plan and schedule

`ifc_equipment` connects the checked HVAC analysis IFC to a metre DXF envelope plan and CSV equipment schedule. Existing isolated `ifc_native` then saves/reopens an actual AutoCAD DWG and plots a fixed-scale A4 PDF. The plan shows sourced generic equipment boxes and thermal-space outlines, not manufacturer or installation detail.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/hvac-drawing-plan.json --out runs/hvac-drawing --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
.venv/Scripts/python -m bsa.workflow verify runs/hvac-drawing
```

The source-linked plan runs model → actual PTAC analysis → equipment drawing → native sheet. Drawings depend on a passing `annual_energy_ifc` producer with saved HVAC device mappings. No engine leaves analysis/drawing/native stages pending; no AutoCAD leaves only native delivery pending. Failed analysis cannot silently produce a passing equipment drawing.

## Source and geometry contract

Settings contain `source`, `annotation_height_m` and `tags`, each with exact device `guid` and a unique ASCII `tag`. All bound HVAC devices must be covered; duplicate/omitted callouts fail. The standalone command is `python -m bsa.ifc_equipment <analysis.ifc> --report <thermal-binding.json> --settings <settings.json> --out <new-directory>`.

The reader verifies the analysis IFC hash and every recorded artifact in the producer's complete inventory, resolving paths within the producer directory. The new IFC result properties must agree with the binding report. It reads actual IFC shapes in SI world coordinates; the shared strict-box check verifies eight corners, boundary-plane triangles, reciprocal mesh edges, face areas and volume. It rejects deformed, rotated, curved and other unsupported shapes rather than drawing their bounding rectangles as exact outlines. Thermal spaces use the same check. Standalone use needs the complete producer run, including native SQL; the selected committed evidence archive is not a complete producer bundle.

The plan uses IFC world X/Y in metres. The equipment and space geometry is verified rectangular envelope geometry; space outlines do not imply architectural wall thickness. No true-north/georeferencing direction is invented. Other IFC elements are explicitly listed in `excluded_elements`; they are not silently treated as drawn HVAC equipment.

## Drawing and schedule

`equipment.csv` and `equipment.json` retain full GUIDs, equipment/space/system identity, actual origin/size, source, thermal cooling/heating kW, supply L/s, baseline/variant simulated annual electrical kWh and baseline maximum hourly electrical kW. The drawing shows short callouts above equipment, full GUID references alongside the plan, and the same equipment table. Per-device peaks are not assumed coincident across devices. Modeled annual/peak electricity is distinct from nameplate or feeder design values.

Every room/device edge, leader, callout, GUID and equipment-table cell carries IFC GUID XDATA where applicable. Reopening the emitted DXF checks its geometry/text/layers against the in-memory source, complete reference-edge coverage and identities. Only LINE/TEXT entities are used for compatibility with the existing native adapter; equipment edges are not disguised as pipe centrelines.

Native sheet settings retain source/window/scale/reference GUID/tolerance fields and add `reference_layer: BSA_EQUIPMENT_REFERENCE` and `drawing_name: equipment`. Each device has exactly one bottom X edge on that layer; other edges have the equipment layer. The native adapter rejects a sheet window that excludes the computed equipment geometry or annotation extents before writing in AutoCAD. Text extents are an automated precheck, not a replacement for actual PDF inspection.

The native adapter verifies active isolated document paths before writes, saves `equipment.dwg`, independently reopens/exports it and reconciles all model handles, counts, geometry, text, layers and GUID XDATA. It plots `sheet.pdf` and measures the reference edge in PDF physical units. In the synthetic 1:100 example, the saved 0.9 m device edge should print at 9 mm; tolerance is explicitly 0.1 mm. DXF success and physical reference success alone do not establish sheet readability.

The final example PDF is rendered with Poppler and inspected separately. During development, that review found header/callout crowding and an overlong room label; the layout was corrected and reprinted. The retained hash-bound review covers this example's clipping, label/table readability and layout only. Native JSON keeps automated visual acceptance pending; a separate review does not certify product geometry, installation, code or engineering acceptance.

## Limits

One sheet, axis-aligned rectangular boxes and a finite equipment table are supported. Arbitrary footprints/products, multistorey overlays, hidden lines, automatic collision-free annotation for arbitrary datasets, multi-sheet pagination, dimensions/installation symbols, ports/duct routing, installation access and full engineering acceptance remain pending. Oversized content requires a new sourced layout/window/scale or future pagination, not clipping or guessed dimensions. Existing IFC space/device/rating, actual engine and material/operation gates still apply.

The implementation reuses the already attributed IfcOpenShell 0.8.5, ezdxf 1.4.5, AutoCAD 2027 native wrappers, pypdf and Poppler runtime; no new dependency or upstream source is bundled. See [HVAC identity binding](HVAC_DEVICES.md), [native CAD limits](IFC_DRAWINGS.md) and [attribution](../THIRD_PARTY.md).
