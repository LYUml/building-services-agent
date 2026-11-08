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

SQLite extraction requires one weather environment (EnvironmentType 3), no sizing/design-day environments and two complete, unique hourly series for every requested rate/unmet-time variable. Year, month/day/hour, minute, 60-minute interval, reporting frequency, units and finite nonnegative values are checked. Warmup data are excluded. Rates are summed across zones/lights at each hour before coincident peaks are found. Hourly average W integrates over exactly one hour to kWh; twelve monthly totals reconcile with annual totals. Independent always-on lighting power and energy are checked against area, density and calendar length. Unmet time is reported separately for each zone/thermostat variable in zone-hours; it is not occupied/facility unmet hours.

Process return code, severe/fatal diagnostics, stdout completion marker and eplusout.end must agree on successful completion. In this installed runtime, SQL Simulations completion flags remained `FALSE` even though the retained process/end/log and full-calendar output indicated success. Raw flags are preserved and the discrepancy stays **pending**; the tool does not certify those flags true or silently overwrite native data. The pinned [SQLite implementation](https://github.com/NatLabRockies/EnergyPlus/blob/v25.2.0/src/EnergyPlus/SQLiteProcedures.cc) defines these fields. No definitive upstream root cause is claimed.

The example's 40 m² building at 12 W/m² versus 6 W/m² gives independently expected annual lighting electricity of 4204.8 versus 2102.4 kWh in 2025. Lower lighting gains reduce supplied cooling demand and increase supplied heating demand in this climate. No net HVAC electricity saving is calculated without actual plant/efficiency data. [Retained execution evidence](evidence/annual-energy/README.md).

Outputs include source/weather hashes, weather audit, actual OSM/IDF/native logs/SQL, hourly whole-building rate CSV, monthly/annual metrics, per-zone unmet time, controlled comparison and HTML report. Workflow task input hashes include the compressed weather asset; altered inputs/results fail integrity verification. Missing EnergyPlus leaves the task pending. Real building/weather applicability, internal gains/schedules, moisture/ventilation, detailed HVAC/plant electricity, calibration, code applicability and full engineering acceptance remain unresolved.
