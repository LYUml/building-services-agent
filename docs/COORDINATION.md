# Shared electrical data across calculations CAD and IFC

```powershell
.venv/Scripts/python -m pip install -e ".[bim]"
.venv/Scripts/python -m bsa.coordination examples/office-electrical/project.json --geometry examples/office-electrical/geometry.json --out runs/coordinated
.venv/Scripts/python -m bsa.workflow execute examples/office-electrical/coordination-plan.json --out runs/coordinated-native --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe'
```

The electrical project JSON is the single source of device identity, XY centre, electrical input kW, power factor, circuit membership and circuit properties. The geometry companion supplies only missing spatial data: source descriptions, spaces, device class, bounding-envelope dimensions and minimum Z elevation. Its device fields are exactly id/space/z_m/size_m/ifc_class/source; repeated XY, power or circuit values are rejected. Device ID sets must match exactly.

Electrical CAD points are device centres. IFC envelope origins are minimum corners, so the bridge subtracts half width/depth from electrical XY. It does not shift the common coordinate reference or infer an installation height. Geometry inputs must explicitly declare `xy_reference: electrical device centre`.

## Output reconciliation

The adapter compiles an attributed IFC input, generates saved electrical calculations/DXF and IFC, then independently reopens their artifacts:

- Exact IFC device IDs and system/circuit sets match common data.
- IFC world-coordinate envelope XY centres match electrical/CAD points.
- IFC electrical kW/PF, circuit IDs, phase, breaker, demand factor, nominal voltage and source properties match common inputs.
- Saved calculation circuit membership, phase/source, connected kW/VA, demand VA and design current match common inputs. IFC kW/VA sums reconcile to those circuits.
- DXF circle positions and full device/circuit labels match the same data, including label positions.

coordination.json records input/output hashes, checks and unresolved gates; coordinated-devices.csv is an ID/IFC-GUID/circuit/value schedule. A test revises device identity, XY, power/PF and circuit properties and verifies propagation. Tampering with saved calculation VA or IFC power is detected. A calculated target failure remains an execution failure even when cross-artifact identity reconciliation itself succeeds.

## Native output and limits

`electrical_coordination` is a workflow adapter with project and geometry input paths. An optional later `native_cad` task may depend on it; it reads the generated nested electrical/devices.dxf, saves/reopens DWG and plots PDF with the existing native verifier. This gives a chain of checks from common input to DXF/IFC/calculations, then DXF to native DWG. It does not compare every possible DWG/IFC attribute or prove visual/design acceptance.

The synthetic three-light coordinated example was executed through actual AutoCAD 2027; its latest PDF was rendered and visually inspected with complete labels and margins. The manual engineering review task remains pending. IFC is still an explicit envelope representation without a BIM-viewer visual gate; no real building bottom drawing, routed cable, manufacturer solid, photometry or fault protection has been accepted. Other domains still use their separate input contracts; a universal cross-discipline model is not claimed.
