# Fixed-size DX PTAC annual simulation

Optional `building.hvac` replaces ideal air loads with actual OpenStudio/EnergyPlus zone equipment: one single-speed air-cooled DX packaged terminal air conditioner, electric heating coil and cycling fixed-speed supply fan per thermal zone. Thermal delivery and native electrical consumption are extracted separately. Capacities and flow are explicit; this adapter does not autosize them or choose a real product.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/thermal-ptac-plan.json --out runs/thermal-ptac --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python -m bsa.workflow verify runs/thermal-ptac
```

The plan reuses saved IFC geometry, GUID/orientation binding, opaque layers and weekly operating inputs. `examples/thermal-ptac/project.json` adds explicit synthetic ratings and unity modifier curves. No measured/manufacturer performance, IFC PTAC product geometry, routed ducts or engineering acceptance is claimed. The source IFC provides spaces; it does not acquire new spatial HVAC equipment from this analysis adapter.

## Input contract

Use annual model `annual hourly EPW; explicit thermal spaces`. The exact HVAC fields are `model`, `source`, `curves` and `zones`. The model string is `single-speed DX PTAC; electric heat; cycling fixed-speed fan`. Each zone entry has its exact thermal `id`, `source` and:

| Input | Meaning |
|---|---|
| `cooling_capacity_w` | gross rated DX cooling capacity, thermal W, excluding supply fan heat |
| `cooling_cop` | gross rated DX cooling COP, excluding supply fan electricity |
| `cooling_shr` | gross rated sensible/total capacity ratio, 0.5 to 1 |
| `supply_flow_m3_s` | rated DX flow, PTAC cooling/heating supply flow and fan maximum flow |
| `heating_capacity_w`, `heating_efficiency` | electric coil thermal capacity and thermal/electric efficiency |
| `fan_pressure_pa`, `fan_efficiency` | fixed fan pressure rise and total efficiency |
| `motor_efficiency`, `motor_in_air_fraction` | motor heat accounting parameters |

Every thermal zone must be covered exactly once. Ratings must be finite and positive, except motor-in-air fraction can be zero; efficiencies/fractions cannot exceed one. SDK/engine checks still apply. No `Autosize` strings or implicit catalogue selections are accepted. This is annual-only; design-day sizing and generic system topologies remain pending.

Five sourced curves are required: `capacity_temperature`, `capacity_flow`, `eir_temperature`, `eir_flow`, `part_load`. Each has `source`, `coefficients`, `x_range` and `output_range`; temperature curves also require `y_range`. Temperature curves use six biquadratic coefficients in order `constant,x,x²,y,y²,xy`; X is coil-entering wet bulb, Y condenser dry bulb. Flow/part-load curves use three quadratic coefficients `constant,x,x²`. Modifier output is dimensionless.

Validation evaluates extrema at corners, edge stationary points and interior stationary points, rather than checking corners alone. Curves must remain positive across their supplied domains and within their declared output limits. Flow/part-load domains must include fraction one. The part-load curve covers exactly 0..1, remains within 0.7..1, is at least the load ratio, and equals one at full load within 1e-6. These are supported-adapter constraints, not validation of manufacturer fit quality. Rated normalization, actual operating-domain applicability and clipping effects require separate review; positive curves alone do not prove applicability. The example's unity curves are explicit synthetic assumptions, not real equipment curves.

Gross capacity/COP/SHR and curve semantics were checked against the inspected EnergyPlus 25.2.0 `Coil:Cooling:DX:SingleSpeed` data dictionary (same [pinned IDD hash](THERMAL_MATERIALS.md)). See the official [zone forced-air equipment reference](https://energyplus.readthedocs.io/en/stable/guides/input-output-reference/1.31-group-zone-forced-air-units.html) and [engineering reference](https://energyplus.readthedocs.io/en/stable/guides/engineering-reference/19.6-zone-equipment-and-zone-forced-air-units.html). Existing OpenStudio/EnergyPlus license attribution applies; no new upstream source/dependency is bundled.

## Authoring and saved-model checks

The adapter disables ideal air loads, adds explicit PTAC/coils/fan, sets draw-through fan placement and cycling mode (constant zero), and keeps equipment availability at one. No-load supply flow and all PTAC outdoor-air flows are zero. Outdoor air is supplied independently by the explicit simple ventilation/infiltration objects; it is not counted again in the PTAC mixer. Supply fan speed modifiers are explicit unity curves. The air-cooled DX crankcase heater is disabled and minimum compressor outdoor temperature is −100 °C as a synthetic broad-range modelling assumption, not a product operating limit recommendation.

After final OSM save/reopen, audits reconcile zone/equipment/component classes and names, source features, every declared rating, flow and mode, availability, condenser settings, and all performance-curve links/coefficient/domain/output/unit fields. Simple ventilation objects are allowed alongside the one actual PTAC in each zone; other equipment is rejected. Tampering with a curve link is detected even if the replacement curve has identical coefficients. The fan-mode day schedule has explicit discrete dimensionless 0..1 type limits to avoid a missing-limit SDK translation warning.

Engine ancillary/latent/rating defaults remain visible in OSM/IDF. Evaporator fan power defaults for standard rating calculations are not asserted as selected test/product values; this adapter does not accept or report SEER/EER compliance. Native economic escalation warnings generated by SDK defaults remain in diagnostics; no tariff, cost or economic claim is made.

## Native results and gates

Annual SQL now requires PTAC heating, cooling and electricity rates plus lighting and zone unmet-time series, with exact component identities, complete calendar, hourly units and monthly/annual reconciliation. Supplied thermal output is net delivery at the unit; it is not the gross DX coil output. The reported electrical PTAC total includes its DX coil, electric heat and supply fan. `summary.hvac` lists the same component contributions for reconciliation; adding them again to PTAC total would double-count. Separate simple ventilation fans and other electrical end uses remain separate.

Independent hourly checks verify PTAC total equals DX + heater + fan electricity, heater thermal output equals its electrical input times declared efficiency, and fan power equals design flow × pressure / total efficiency × native fan part-load ratio. Annual component sums must also match. The electric cooling COP is not assumed constant across the year from its rated value; curves and part-load operation govern the engine. Gross coil thermal output, unit thermal delivery and electrical input have separate meanings.

Source-declared maximum zone unmet hours remain a separate gate. A real engine completion can pass while the finite-capacity design fails. The controlled undersized-heater test completes natively but retains its failed unmet-time target and false design acceptance. A deliberately permissive input tolerance/target still needs source/applicability review; passing numerical checks never certifies sizing, comfort or code compliance.

Outputs retain OSM/IDF, logs/SQL/hourly CSV, source/engine/weather hashes, `metadata.hvac_audit`, `summary.hvac`, monthly/annual thermal/electrical metrics and baseline/variant comparison. The example changes only lighting density between cases, leaving equipment and operating conditions identical. Actual product selection/calibration, weather/domain applicability, detailed HVAC controls/ventilation, routed BIM/CAD equipment, other system types and full engineering/visual acceptance remain pending.
