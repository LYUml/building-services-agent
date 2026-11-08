# Source-declared opaque constructions

The annual and saved-IFC annual adapters accept explicit material layers, with source reconciliation after saving and reopening OSM. This replaces the legacy fixed mass layer and uniform insulation assumption; it does not establish material/product applicability or a complete envelope/HVAC design.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/thermal-materials-plan.json --out runs/thermal-materials --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python -m bsa.workflow verify runs/thermal-materials
```

The plan reuses the unchanged IFC authoring and explicit GUID/north-axis mapping in `examples/thermal-ifc`. Only the annual template changes to `examples/thermal-materials/project.json`. It keeps the same geometry, weather, constant setpoints and baseline/variant lighting comparison. All example layers are explicitly synthetic, not manufacturer data or measured building materials.

## Input contract

Replace `building.envelope_r_m2k_w` with `building.opaque_constructions`; the two schemas are mutually exclusive. Four roles are required: `exterior_wall`, `roof`, `floor` and `interzone`. Each assembly contains `source` and one to ten `layers`, ordered outside to inside.

Every layer requires `name`, `source`, `type`, `roughness`, `thermal_absorptance`, `solar_absorptance` and `visible_absorptance`. A `massive` layer additionally requires `thickness_m`, `conductivity_w_mk`, `density_kg_m3` and `specific_heat_j_kgk`. A `resistance` layer instead requires `resistance_m2k_w`; it contributes no heat capacity. No implicit optical-property defaults are accepted for explicit layers. Inputs must be finite numbers; booleans are rejected.

Range/roughness validation follows `Material` and `Material:NoMass` in the inspected official EnergyPlus 25.2.0 `Energy+.idd`, SHA256 `5f71380fdeb7d2456dbfb71913b90c40f87e109051c62c44f08577451974f44f`. Thickness/conductivity/density are positive, specific heat is at least 100 J/kgK, resistance layers are at least 0.001 m²K/W, thermal absorptance is greater than zero and at most 0.99999, and solar/visible absorptance are between zero and one inclusive. Roughness is one of the six engine choices. The actual SDK setters and engine can reject combinations beyond these individual field checks. This basis is engine input syntax, not a regulation or physical validation of supplied values.

## Assignment and verification

Exposed walls, roofs and floors receive their role's assembly. Exposed floors remain adiabatic under the current geometry contract; a floor material does not introduce ground coupling. Every matched interzone pair receives the shared assembly. The lexically first zone receives the listed order (from the peer toward that zone); the other receives reversed order. This also applies to stacked floor/roof pairs. One shared assembly currently covers all interzone faces: separate partition/slab products, per-surface assemblies, glazing, cavities, bridges, moisture and ground models remain pending.

Saved-model QA compares material types, every physical/optical value, roughness, layer count/order, construction/layer source features and input names. Final annual OSM is reopened again after weather/run-period translation. Missing/replaced layers or changed sources fail the audit. Each surface is recorded with zone, type, boundary, area, role, reverse-order flag and assigned construction. Both peer surfaces are included in the interzone area total.

The audit separately reports series layer resistance `sum(thickness/conductivity) + sum(resistance)` and areal heat capacity `sum(thickness*density*specific heat)` for massive layers. The inverse layer resistance is labelled **layer conductance**, not an assembly U-value including surface films. The synthetic exterior wall gives 2.3 m²K/W; the roof gives 3.2 m²K/W; the shared assembly has 111500 J/m²K. Saved IFC geometry supplies areas, not these material properties.

The 102 m², three-space example has 138 m² exterior wall, 102 m² roof, 102 m² adiabatic floor and 72 m² interzone surface area (both sides counted). Actual complete-calendar baseline/variant EnergyPlus runs retain the independently expected lighting electricity 10722.24 / 5361.12 kWh. Heating/cooling outputs remain supplied thermal energy, not plant electricity. Native diagnostics and all source/geometry/annual checks remain in force. Geometry, layers and numerical success do not certify real construction, applicability, comfort or engineering acceptance.
