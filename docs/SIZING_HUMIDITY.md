# Explicit humidity in zone sizing

The design-day adapter accepts optional `sizing_humidity` with a source and `humidification_rh_percent` / `dehumidification_rh_percent`. Both values must be strictly between zero and 100, with the lower value no greater than the upper. See `examples/sizing-humidity/project.json`. Annual-weather/PTAC workflows currently reject this option rather than silently ignoring it.

```powershell
.venv/Scripts/python -m bsa.energy examples/sizing-humidity/project.json --out runs/new-sizing-humidity --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
```

The author sets `Sizing:Zone` to sensible-and-latent sizing and attaches separate constant RH schedules. This differs from the default sizing mode, which does not enable latent sizing; see the [EnergyPlus 25.2 design-object reference](https://bigladdersoftware.com/epx/docs/25-2/input-output-reference/group-design-objects.html). It does not add an operating humidistat or change ideal-load operating humidity controls. An existing operating humidistat is rejected because it overrides sizing-only schedules. Existing latent supply-humidity-ratio-difference defaults are retained and are not sourced equipment specifications.

After saving, the adapter reloads OSM to check zone mode, source provenance and schedules, then independently reloads IDF to check exact zone coverage, mode and schedule links/values. `metadata.sizing_humidity_audit` records the result. These are actual model input checks, not guarantees of all-timestep RH control. Native sizing CSV and SQL remain available for inspection; the demonstrated case has nonzero latent loads and also some timestep RH deviation.

This closes part of the missing humidity-input support needed for Hong Kong load-design integration, but the full Table 6.4 rule-to-model binding remains pending. Current examples retain synthetic weather, gains and equipment assumptions. Do not infer recognized load-method applicability, sufficient plant performance, annual humidity control or complete regulatory conformity from these checks. Native runs, reports and injected-fault tests are in `docs/evidence/sizing-humidity`.
