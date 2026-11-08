# Annual hourly weather analysis

`annual_energy` extends the existing synthetic two-zone design-day adapter with actual complete-calendar EPW simulation. It keeps ideal supplied heating/cooling **thermal** kWh separate from lighting **electricity** kWh. It does not infer plant electricity, COP, whole-building EUI or a finished HVAC system from ideal loads.

```powershell
.venv/Scripts/python -m pip install -e ".[energy]"
.venv/Scripts/python scripts/setup_energy.py
.venv/Scripts/python -m bsa.workflow execute examples/annual-energy/plan.json --out runs/annual --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python -m bsa.workflow verify runs/annual
# Standalone: --weather accepts an EPW or a losslessly compressed .epw.gz.
.venv/Scripts/python -m bsa.annual_energy examples/annual-energy/project.json --weather examples/annual-energy/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe --out runs/annual-standalone
```

## Inputs and weather provenance

The source-linked project declares its model scope, building assumptions, calendar year, weather source/station/raw SHA256, numerical/runtime budgets and per-zone heating/cooling unmet-time target. Building dimensions, constant setpoints, envelope resistance and baseline/variant lighting densities remain explicit synthetic data. Site coordinates/time zone/elevation come from the validated EPW, preventing duplicate mismatched site input. The template excludes design days.

The example preserves the exact Chicago O'Hare TMY3 bytes distributed in the verified official EnergyPlus 25.2.0 Windows archive, compressed with gzip mtime=0. [Asset attribution/hashes](../examples/annual-energy/WEATHER_SOURCE.md) and the retained EnergyPlus license apply. Header and uncertainty flags remain unmodified. This is typical meteorological data with mixed source years, remapped to the explicit simulation calendar, not historical 2025 weather or Hong Kong design weather.

Weather validation requires eight EPW headers, one hourly January 1 to December 31 period, matching raw hash/station, exactly ordered unique month/day/hour rows (8760 or 8784), a consistent legacy minute field of 0 or 60 and finite in-range required dry/dew temperature, humidity, pressure, infrared/solar, wind and sky-cover values. Leap calendars require weather permission and February 29 records. Compressed/raw inputs have a 20 MB processing budget. Hourly end labels 1..24 retain the engine convention; they are not interpreted as hour-beginning samples. The validator is a structural/required-field check, not meteorological certification or a claim that every unused EPW field was quality-assured. See the [EPW format guide](https://energyplus.readthedocs.io/en/stable/auxiliary-programs/auxiliary-programs.html).

## Actual simulation and accounting

Pinned OpenStudio 3.11.0 / EnergyPlus 25.2.0 generate/save OSM and IDF and execute the supplied engine on the hash-verified prepared EPW. The model has two adjacent rectangular zones with matched shared surfaces, adiabatic floors, a uniform resistance plus fixed synthetic mass layer, ideal air loads, always-on lighting and constant heating/cooling setpoints. No windows, people, equipment, outdoor-air system or infiltration are included. SDK optical/default assumptions remain visible in saved OSM/IDF; they are not measured constructions. Four internal timesteps per hour are inherited from the existing model builder. Rain/snow indicators, DST and holidays are disabled; no sizing/design-day simulation runs.

SQLite extraction requires one weather environment (EnvironmentType 3), no sizing/design-day environments and a complete, unique hourly series for every authored zone/light for each requested variable, with exact authored key identities. Year, month/day/hour, minute, 60-minute interval, reporting frequency, units and finite nonnegative values are checked. Warmup data are excluded. Rates are summed across zones/lights at each hour before coincident peaks are found. Hourly average W integrates over exactly one hour to kWh; twelve monthly totals reconcile with annual totals. Independent always-on lighting power and energy are checked against area, density and calendar length. Unmet time is reported separately for each zone/thermostat variable in zone-hours; it is not occupied/facility unmet hours.

Process return code, severe/fatal diagnostics, stdout/end reports and SQL version/flags are now checked by the shared [native completion diagnosis](ENERGY_COMPLETION.md). The inspected official 25.2 Windows executable normally leaves initialized FALSE/FALSE flags because its source releases SQLite before the guarded final status update. This source-backed limitation is accepted only for the exact build/executable hash with all other completion checks passing; raw flags remain false. Other contradictions/missing data stay unverified, and actual failures remain failed. Calendar/numerical and real-project acceptance checks still apply separately.

The example's 40 mÂ² building at 12 W/mÂ² versus 6 W/mÂ² gives independently expected annual lighting electricity of 4204.8 versus 2102.4 kWh in 2025. Lower lighting gains reduce supplied cooling demand and increase supplied heating demand in this climate. No net HVAC electricity saving is calculated without actual plant/efficiency data. [Retained execution evidence](evidence/annual-energy/README.md).

Outputs include source/weather hashes, weather audit, actual OSM/IDF/native logs/SQL, hourly whole-building rate CSV, monthly/annual metrics, per-zone unmet time, controlled comparison and HTML report. Workflow task input hashes include the compressed weather asset; altered inputs/results fail integrity verification. Missing EnergyPlus leaves the task pending. Real building/weather applicability, internal gains/schedules, moisture/ventilation, detailed HVAC/plant electricity, calibration, code applicability and full engineering acceptance remain unresolved.

## Explicit multi-space geometry

Use `examples/annual-energy/three-spaces.json` with the same standalone command and weather asset. Model `annual hourly EPW; explicit thermal spaces` replaces the three legacy dimensions with `building.spaces`: each entry has a case-insensitive unique ASCII `id`, a geometry `source`, and metre-valued three-component `origin_m` / positive `size_m`. Each box is one space and one ideal-load thermal zone. Dimensions derive area; no separately supplied measured area is inferred. Other construction, schedule and load limitations above still apply.

The builder checks up to 100 axis-aligned boxes, rejects volume overlap and partial face contact, matches complete shared faces (including stacked floor/roof faces), and verifies reciprocal surface links, zone identities, shared areas, zone count and total floor area. Disconnected boxes are allowed; remaining floors are adiabatic and other exposed surfaces use the existing outdoor defaults. Arbitrary polygons, partial-face subdivision, rotated geometry remain pending; saved-box IFC binding is described in [THERMAL_BINDING.md](THERMAL_BINDING.md). This is an explicit geometry contract, not an arbitrary-building importer.

The three-space synthetic chain has widths 3/5/4 m, depth 4 m and height 3 m: 48 m², three thermal zones and two shared-face pairs. Actual 8760-hour baseline/variant execution gives independently expected lighting electricity 5045.76 / 2522.88 kWh. Tests reopen stacked OSM geometry and reject renamed SQL zone keys even when sample counts still match. All inputs retain per-space sources; the example is not a measured or accepted building design.

For sourced role-specific opaque layers replacing the legacy uniform construction, see [THERMAL_MATERIALS.md](THERMAL_MATERIALS.md). All other weather, geometry, internal-gain/schedule, plant and acceptance limitations above still apply.

For sourced weekly lighting, people, equipment and fixed scheduled simple infiltration/ventilation replacing the legacy absent-gain/always-on assumptions, see [THERMAL_OPERATION.md](THERMAL_OPERATION.md). The example includes independently checked equipment/occupancy/fan quantities and native density-dependent outdoor-air mass flows. Full HVAC/plant and real applicability remain pending.

For explicitly sized actual DX PTAC/electric-heat/fan components replacing ideal loads, see [THERMAL_HVAC.md](THERMAL_HVAC.md). This optional branch adds real native equipment electricity and component balances; existing examples still use ideal loads. Equipment capacity/curve/product applicability, other HVAC/plant types and full acceptance remain separate gates.

For explicitly sourced exterior-window rectangles and simple glazing, see [THERMAL_WINDOWS.md](THERMAL_WINDOWS.md). The optional branch adds saved world-geometry/glazing/net-opaque-area audits and exact native hourly solar/heat-gain/loss results. Existing no-window examples retain their assumptions; architectural IFC/window products and daylight controls are not inferred.
