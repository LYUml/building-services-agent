# Multi-space native energy evidence

Synthetic three-space chain from examples/annual-energy/three-spaces.json, executed with pinned OpenStudio 3.11.0 / EnergyPlus 25.2.0. annual.json records source/engine/weather hashes, geometry adjacency and exact series identities, native completion and numerical checks. Selected OSM/IDF, summaries and native diagnostics are retained; large raw SQL/hourly outputs remain in ignored runs/three-space-annual-v3 and can be regenerated. Their hashes remain in annual.json; this selected archive is not a complete replay archive.

Three zones, 48 m², four reciprocal shared surfaces, complete 8760-hour baseline/variant results; lighting 5045.76 / 2522.88 kWh. Full local regression: 177 tests, no skips, 167.489 s; native AutoCAD, EnergyPlus, Radiance and OCR were enabled. Tests separately reopen stacked floor/roof adjacency, reject overlap/partial contacts and reject renamed SQL zone identities. Engine translation reports reversed copies of asymmetric shared constructions; retained warnings are not suppressed.

No real-building geometry, IFC-space binding, plant electricity or engineering acceptance is claimed. Original completed coursework remains untouched.
