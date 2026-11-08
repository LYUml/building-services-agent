# Saved IFC thermal-space binding evidence

Source plan: examples/thermal-ifc-plan.json. Fresh actual execution: runs/thermal-ifc-v2; workflow verify returned integrity_pass true, design_accepted false. Geometry is read from the saved IFC solids/placements, with full GUID coverage and a sourced 30-degree EnergyPlus north axis. Three spaces total 102 m²; two shared-face pairs are checked in the saved energy model. Lighting totals match 10722.24 / 5361.12 kWh for the complete 2025 calendar.

Selected saved IFC, prepared project, geometry/source audits, annual results, OSM/IDF and native completion/diagnostics are retained. Full raw SQL/hourly files and other generated workflow artifacts remain in the ignored run and are hash-listed by the manifests. This selection is not a complete portable replay archive. The native completion diagnoses retain the exact inspected binary's false SQL flags; the original native data is not rewritten.

Full local regression: 182 tests in 174.754 s, no skips, with native AutoCAD, EnergyPlus, Radiance and OCR enabled. Binding tests include actual millimetre IFC conversion, moved world placements, deformed/rotated-solid rejection, mapping coverage, duplicate-input rejection, saved OSM orientation, missing-engine pending behavior and saved-BIM-to-annual execution. The source plan and all other tracked plans passed passage/hash validation. Engine warnings about reversed asymmetric shared constructions are preserved.

No IFC-viewer visual acceptance, measured geometry, real thermal-boundary/material/gain/weather applicability, imported HVAC/plant electricity or engineering acceptance is claimed. The completed coursework remains untouched. See docs/THERMAL_BINDING.md and THIRD_PARTY.md.
