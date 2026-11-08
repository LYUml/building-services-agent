# Saved IFC spaces to annual analysis

The `annual_energy_ifc` workflow adapter joins editable IFC authoring to actual annual OpenStudio/EnergyPlus analysis. Geometry comes from saved IFC solids and world placements rather than a second set of dimensions in a calculation template. This does not import a complete thermal/HVAC model from arbitrary BIM.

```powershell
.venv/Scripts/python -m pip install -e ".[energy,bim]"
.venv/Scripts/python -m bsa.workflow execute examples/thermal-ifc-plan.json --out runs/thermal-ifc --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python -m bsa.workflow verify runs/thermal-ifc
```

The plan authors `thermal-ifc/bim.json`, then binds the resulting saved IFC using `thermal-ifc/binding.json` and the geometry-free `thermal-ifc/project.json` annual template. An existing source IFC can replace `depends_on` with an `ifc` path relative to the plan. All original plan inputs are hashed. Missing engine or failed upstream producer leaves the thermal task pending.

Standalone usage is `python -m bsa.thermal_binding <template.json> --binding <mapping.json> --ifc <model.ifc> --weather <weather.epw.gz> --out <new-directory> --energyplus <engine.exe>`.

## Geometry and identity contract

The binding requires a source statement, explicit `north_axis_deg` (EnergyPlus Building North Axis, 0 inclusive to 360 exclusive) and `spaces` entries containing `guid`, unique thermal `id` and `source`. Every saved IfcSpace must be mapped exactly once. Duplicate GUIDs in the model or mapping are rejected. Names, area properties and authoring JSON dimensions do not determine extracted geometry.

IfcOpenShell 0.8.5 evaluates saved space geometry in SI world coordinates, including nested placements and declared metre/millimetre units. Each supported space must be an actual closed axis-aligned rectangular solid: eight corners, boundary-plane triangles, consistent reciprocal mesh edges, full face areas and the matching volume. A bounding box alone is insufficient. Deformed or rotated spaces are rejected. The prepared annual schema then rejects overlaps and partial-face contacts and checks reciprocal OpenStudio shared-face identities/areas. This implementation supports box geometry with corner-only triangulation; it can reject geometrically equivalent boxes containing additional tessellation vertices. Arbitrary footprints, curved spaces, Boolean cavities and partial-face subdivision remain pending.

The explicit north-axis setting is applied to the saved OpenStudio building. It is not inferred from IFC TrueNorth, projected/geographic CRS or site metadata. The caller must establish the appropriate orientation and applicability; this adapter does not georeference models. Existing non-IFC annual models can optionally declare `building.north_axis_deg`; their legacy default remains zero.

## Source and output checks

Outputs retain an unchanged source `model.ifc`, `geometry-binding.json` with GUID/zone/geometry/unit/orientation evidence, `bound-project.json`, a full nested `annual` run and `thermal-binding.json` with original input hashes and output inventory. The prepared project's per-space source includes the saved IFC GUID and hash. Native annual extraction requires exact authored zone, ideal-load-system and light identities with complete hourly calendar coverage. Model properties are not rewritten with invented areas or capacities.

The synthetic example contains 8/5/4 m wide spaces, all 6 m deep and 3 m high: 102 m² total, three zones, two shared-face pairs, and a declared north axis of 30 degrees. Independent always-on lighting totals for 2025 are 10722.24 / 5361.12 kWh at 12 / 6 W/m². These are lighting electricity; ideal supplied heating/cooling remain thermal quantities.

Constructions, windows, thermal boundary classifications, gains, schedules, ventilation, HVAC/plant, IFC distribution equipment and actual weather applicability are not imported automatically. A generic spatial envelope does not prove a real thermal boundary. Existing uniform synthetic constructions, adiabatic exposed floors, always-on lights and ideal air loads remain explicit assumptions. Geometry/annual numerical success does not establish engineering or visual acceptance. See [annual engine limits](ANNUAL_ENERGY.md), [native completion diagnosis](ENERGY_COMPLETION.md) and [upstream attribution](../THIRD_PARTY.md).
