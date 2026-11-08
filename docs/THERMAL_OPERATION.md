# Weekly internal gains and simple outdoor air

Optional `building.operation` replaces the annual adapter's always-on lighting and absent people/equipment/outdoor-air inputs with explicit sourced weekly data. The same inputs work with directly declared boxes and saved-IFC space binding. Design-day adapter use is rejected because this weekly contract does not define special design-day schedules.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/thermal-operation-plan.json --out runs/thermal-operation --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python -m bsa.workflow verify runs/thermal-operation
```

The example reuses the sourced opaque layers, saved IFC geometry and GUID/north-axis mapping from earlier examples. Its operating values remain explicitly synthetic; they are not surveyed occupancy, measured leakage, selected fan products or ventilation compliance.

## Input contract

The exact operation fields are `source`, `outdoor_air_model`, `lighting`, `equipment`, `people`, `infiltration` and `ventilation`. Set `outdoor_air_model` to `fixed scheduled design flow; no wind/stack`. Each group requires `source` and `weekly_fraction`: all seven full English lowercase weekday names, each with 24 finite fractions between zero and one. Index zero covers 00:00–01:00; the engine reports that hour with end label 1. Interpolation is disabled. Calendar dates use the explicitly declared simulation year, including February 29. Weather header weekday, DST, holidays, special days and seasonal exceptions do not override this contract.

| Group | Required additional inputs |
|---|---|
| lighting | `fraction_radiant`, `fraction_visible`; return-air fraction is explicitly zero |
| equipment | `watts_per_m2`, `fraction_radiant`, `fraction_latent`, `fraction_lost`; remainder is convective |
| people | `people_per_m2`, `activity_w_per_person`, `fraction_radiant`, `sensible_heat_fraction`; activity is constant per person |
| infiltration | `air_changes_per_hour` at the declared full-flow condition |
| ventilation | `flow_m3_s_per_m2`, `type` (`Natural`, `Intake`, `Exhaust`, `Balanced`), `fan_pressure_rise_pa`, `fan_total_efficiency` |

Nonnegative finite physical inputs, positive activity/efficiency, fractions within zero to one and nonnegative remaining heat fractions are required. Natural ventilation requires zero fan pressure. Each saved thermal space receives the same per-area/per-volume inputs and weekly profiles; spaces have independently derived areas and volumes. Per-space operating overrides remain pending.

The saved model uses People, ElectricEquipment, SpaceInfiltrationDesignFlowRate and ZoneVentilationDesignFlowRate objects. The simple airflow equation has constant coefficient one and all temperature/wind coefficients zero, so it is explicitly scheduled design flow rather than an empirical weather-driven prediction. Ventilation uses Outdoor density basis, indoor/outdoor temperature limits −100 to 100 °C, minimum temperature difference −100 K and maximum wind speed 40 m/s. These deliberately broad engine control limits are part of this adapter contract and are checked after reopening. They are not recommended operating settings or occupant comfort limits.

For `Intake`/`Exhaust`, the simple fan power follows flow times pressure divided by efficiency. `Balanced` models equal intake/exhaust fans, doubling that fan electricity; `Natural` has none. Intake/balanced fan heat is handled by the engine. These are EnergyPlus simple ventilation semantics, not a full air-handler/fan-curve/duct model. See the engine's [airflow input/output reference](https://energyplus.readthedocs.io/en/latest/guides/input-output-reference/1.17-group-airflow.html) and [infiltration/ventilation engineering reference](https://energyplus.readthedocs.io/en/stable/guides/engineering-reference/8.3-infiltrationventilation.html). No upstream source code or new dependency is vendored.

## Saved model and result checks

After final annual OSM save, the adapter reopens it and checks each space/zone object count and link, physical inputs, explicit source features, fan/flow coefficients and every hourly fraction for all seven weekdays. Changing an occupancy density, fan pressure, source feature or daily profile fails this audit. Material, geometry and native completion checks remain independent.

SQL extraction requires exact authored zone/equipment identities, hourly reporting frequency, calendar/year/interval/units, complete ordered series and finite nonnegative values. Lighting, equipment power, occupant count and simple fan energy are checked independently for each zone and each hour, with annual integrals checked separately. A changed hourly distribution can fail even if its annual total is unchanged. The declared year, not a guessed number of weekdays, determines analytic totals. Lighting uses the existing sourced energy/rate tolerances; equipment/fan use the same tolerances; occupant-count comparisons use 1e-6 persons/person-hours numerical tolerance.

Infiltration and ventilation mass flow are retained in kg/s and integrated to kg. Their scheduled on/off behavior is checked per zone. Mass depends on the engine's air-density calculation; the tool does not claim equality to a guessed fixed-density mass flow. A positive nominal flow/profile requires positive native mass flow; a zero setting/profile requires zero within 1e-10 kg/s. Native logs/warnings remain visible. This is a numerical/coverage gate, not measured airflow validation.

Outputs add `metadata.operation_audit`, `summary.operation` and `operation-hourly.csv`. CSV distinguishes native units: equipment W, people count, fan energy J per hour and outdoor-air kg/s. Heating/cooling supplied thermal kWh, lighting electricity, equipment electricity, ventilation fan electricity and person-hours remain separately labelled. The tool does not add thermal demand to electrical energy or infer plant electricity/COP.

The 102 m² synthetic example operates at full fraction for ten hours on weekdays and half fraction for four hours on Saturdays, with Sundays off. In 2025, 261 weekdays plus 52 Saturdays give 2714 equivalent full-load hours. Expected lighting electricity is 3321.936 / 1660.968 kWh at 12 / 6 W/m²; equipment is 2214.624 kWh at 8 W/m²; occupancy is 22146.24 person-hours at 0.08 persons/m²; balanced simple fan electricity is 69.207 kWh at 0.0005 m³/s/m², 150 Pa per fan and efficiency 0.6. Tests also execute a synthetic leap-weather derivative (not real meteorology) and a genuine zero-load/no-fan case.

Detailed HVAC/plant, heat recovery, airflow networks/pressurization, windows, control/schedule exceptions, product/physical/code applicability, surveyed inputs and full engineering acceptance remain pending. A source-linked operating assumption and successful engine run do not establish suitability for an actual building.
