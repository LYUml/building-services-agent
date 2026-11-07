# IFC MEP models

```powershell
.venv/Scripts/python -m pip install -e ".[bim]"
.venv/Scripts/python -m bsa.bim examples/mep-ifc/project.json --out runs/ifc-electrical
.venv/Scripts/python -m bsa.workflow execute examples/mep-ifc/plan.json --out runs/ifc-workflow
```

IfcOpenShell 0.8.5 creates IFC4 files; the EXPRESS rule executor imports pytest internally, so the optional dependency set includes the tested pytest 9.2.0. There is no dependency on Blender, Revit or a hidden model service for this adapter.

## Source data

Required project fields are name, sources, geometry_scope (`axis-aligned bounding envelopes`), spaces, systems and devices. Connections are optional. See the two explicit synthetic examples in examples/mep-ifc.

- Spaces: unique id, origin_m, size_m and source. Origins are world-coordinate minimum corners; sizes are positive metre dimensions. All spaces belong to one nominal storey; there is no real-world georeferencing or multi-storey placement in this slice.
- Systems: id, predefined_type and source. The adapter supports a small explicit set of IFC distribution-system enum values. Devices must refer to an existing system and space.
- Devices: id, IFC class, origin_m, size_m, space, system and source. Optional electrical_kw is input electrical power, not cooling capacity. The model stores ID/source/scope and supplied electrical input as properties. Shapes are editable IFC mesh envelopes, not manufacturer geometry or swept round pipe sections. Allowed classes are listed in bsa/bim.py. Devices must lie inside their declared rectangular space.
- Ports: per-device id, local offset_m, SOURCE/SINK direction and source. Connections name `device.port` endpoints and source. A port may be used once. Connections must go from source to sink between distinct devices in one system. These are logical relationships; separation of endpoints does not create a routed cable or pipe.

Current schema is intentionally explicit about its representation limits. It does not support rotated equipment, arbitrary floor boundaries, cross-system coils, bidirectional ports, actual circuit protection objects, physical cable paths or system sizing. Declaring an IFC class does not prove a product's technical specification.

## Verification

After writing model.ifc, a separate read checks IFC4 attributes and EXPRESS rules, then the geometry engine tessellates devices to compare world-coordinate bounds against input within 1e-7 m. It also checks metre units, device/space counts, exact system membership, input properties, port identities/directions/world positions and exact connection endpoints. Source JSON hash must stay unchanged. schema-validation.json preserves diagnostics and bim-verification.json preserves checks, IFC hash and unresolved gates.

The electrical and ventilation IFC examples were both executed through a source-quoted workflow. Their fixture data is independent of the older three-light CAD example; automatic reconciliation between those different scenarios is not claimed. Device shapes, IFC syntax and relationships are checked. No BIM viewer visual review, clash validation, physical route validation, operating performance or regulation compliance has been claimed.
