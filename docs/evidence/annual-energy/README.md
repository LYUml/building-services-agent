# Executed annual EPW comparison

Executed 2026-11-08 from examples/annual-energy/plan.json with OpenStudio 3.11.0 and official EnergyPlus 25.2.0-cf7368216c. Both actual native cases covered the full 2025 calendar: one weather environment, 8760 hourly records per zone/light variable, with no design-day or warmup rows included. Original project/compressed weather bytes were unchanged; the complete original run at runs/annual-energy-evidence-v1 passed workflow integrity verification.

This directory is **selected evidence**, not a complete portable workflow archive. original-workflow.json and annual.json preserve the full original input/artifact inventories, including hashes for unarchived native SQL/ESO/weather outputs. Actual OSM/IDF, native stdout/error/end reports, hourly building-rate CSV, monthly/annual summaries and weather audit are retained. Reproduce with the source plan and pinned dependencies; do not treat missing unarchived inventory files as present here.

| Quantity | Baseline 12 W/m² lights | Variant 6 W/m² lights | Variant minus baseline |
|---|---:|---:|---:|
| Ideal supplied cooling, kWh thermal | 2358.2704 | 1403.5059 | -954.7645 |
| Ideal supplied heating, kWh thermal | 1564.9961 | 2521.7485 | +956.7524 |
| Lighting, kWh electricity | 4204.8 | 2102.4 | -2102.4 |

The independent lighting calculation is 40 m² × 12/6 W/m² × 8760 h / 1000. January, February and December monthly balances were also independently checked. Every per-zone heating/cooling unmet-time sum was 0 zone-hours against the explicitly synthetic <=1 criterion. Lower lighting gains reduce cooling demand while increasing heating demand; no plant electricity/COP, whole-building EUI or net HVAC saving is inferred.

weather-provenance.json records a fresh whole-archive SHA256 check and byte-for-byte comparison between the committed gzip's raw data and the exact Chicago TMY3 WeatherData member inside that verified archive. The asset preserves source header/uncertainty flags. Weather source years are mixed TMY years; 2025 is the remapped simulation calendar. The model/weather are not an actual Hong Kong building scenario.

Native SQL Completed/CompletedSuccessfully values were `FALSE`/`FALSE` in both cases. Actual processes returned zero, stdout and eplusout.end reported successful completion with no severe/fatal errors, and complete hourly weather-period data were checked independently. The discrepancy is preserved in summary.json/annual.json and remains pending; no native flags were changed or certified true. Retained warnings also include unused life-cycle escalation resources; no cost calculation is asserted. The translator's shared asymmetric wall warning records creation of the reversed construction copy. No upstream root cause for the SQL flag discrepancy is claimed.

monthly-comparison.png was generated from the actual monthly summaries with separate thermal/electric units and inspected for readable labels, complete twelve-month curves, correct baseline/variant colors and explicit synthetic scope. figure-provenance.json binds the source summary/image hashes. This is an analytical figure, not building geometry or plant validation.

Full local regression: 168 tests passed in 162.551 seconds, no skips, with actual AutoCAD, EnergyPlus, Radiance and OCR optional checks enabled (regression.log). New tests include real 8760-hour operation, real 8784-hour operation using an explicitly synthetic Feb29 derivative, weather hash/station/missing-field/duplicate-hour checks, malformed SQL period/interval/coverage rejection, failed unmet-time retention and workflow artifact integrity. Both edited skills passed validation. The new Windows energy CI job is configured; remote execution is not claimed as observed local evidence.

An independent checkout-index snapshot imported its staged code, validated all 26 source-linked plans and executed/verified the annual workflow using actual native EnergyPlus. Selected archived artifact, figure, weather asset and license hashes were rechecked, and CI YAML parsed. The snapshot check caught prior Git normalization of the license notice's CRLF bytes; .gitattributes and index normalization now preserve the unchanged upstream notice bytes and recorded hash across checkout.

Actual building geometry/constructions/optical properties/gains/schedules, weather applicability, ventilation/moisture, detailed HVAC/plant, calibration, source/code/domain acceptance and the native SQL completion discrepancy remain unresolved.
