# Verification record

2026-11-08 foundation milestone, Windows / Python 3.12.

- Editable package installation succeeded in this repository's .venv.
- `python -m unittest discover -s tests -v`: 4 tests passed. Covers hand calculation, rejection of invalid provenance/topology/numbers, visible cable failures, artifact counts, immutable input and overwrite refusal.
- `python -m bsa.cli run examples/office-electrical/project.json --out runs/office`: executed; calculated checks pass; design_accepted remains false.
- Three synthetic device circles exported, source JSON hash unchanged.
- No native AutoCAD, IFC, EnergyPlus or photometry execution yet. HTML/SVG generated but visual review is pending. No full engineering/design acceptance is claimed.

Run directories are excluded from Git; regenerate them from the tracked example. The current overall goal remains active; see ROADMAP.md for unfulfilled requirements.

Follow-up checks: all five skills passed the host skill-creator validator after installing its PyYAML prerequisite. DXF serialization now uses pinned ezdxf 1.4.5 with explicit metre units and declared layers. Independent reload verified three circles, three labels, units=metres and zero audit errors. Four tests passed again; the updated sample ran in runs/office-v2. AutoCAD 2027 and Revit 2027 installation directories are present; live/native integrations have not yet been executed.

## Native CAD milestone

AutoCAD 2027 Core Console X.118.0.0 executed against a new synthetic overlay under this repository. It saved a DWG, reopened it in a second independent process, and matched three circles (positions/radii/layers), three text entities (positions/labels/layers) and INSUNITS=6. Source DXF hash remained unchanged. PDF plotting was performed from the reopened native DWG without saving plot changes.

Initial extents plotting produced edge crowding; replaced with a padded window. Final PDF was rasterized with Poppler and visually inspected: three symbols and labels complete, legible and without overlap. Evidence: docs/evidence/native-office contains verification hashes, rendered page and a separate visual review tied to the PDF hash. Plotted scale is fit-to-page schematic, not an engineering fixed-scale sheet.

`BSA_TEST_AUTOCAD=1 python -m unittest discover -s tests -v`: **6 tests passed**, including real native save/reopen and PDF output. Integration test does not claim visual acceptance; that is separately documented above. No GUI session was attached, closed or restarted. Existing drawings, full plot layouts and engineering design acceptance remain pending.

## Energy-engine milestone

OpenStudio SDK 3.11.0 generated two adjacent 20 m2 zones, matched both shared-wall surfaces and translated to EnergyPlus 25.2.0. Official engine archive SHA256 matched the upstream asset digest. Baseline (12 W/m2 lights) and variant (6 W/m2) each completed two synthetic design days with zero warnings/severe errors in the final EnergyPlus summary. Original project JSON stayed unchanged. ForwardTranslator emits an informational note about reversing the asymmetric construction on the shared wall; this is retained in run output.

Independent balance: 40 m2 x 12 W/m2 = 480 W baseline lighting; variant 240 W. Extracted coincident peaks match both values; each 24-hour design-day lighting quantity equals power x 24 h. Reduced lighting decreases summer cooling and increases winter heating, as expected under these ideal-load assumptions. Values are not annual energy or plant electricity. See docs/evidence/two-zone-energy for JSON, OSM/IDF and engine diagnostics.

Test run: 8 discovered; 7 passed (including actual engine baseline/variant test), 1 native AutoCAD test skipped because this invocation enabled only the energy test. The previously recorded native test remains independent evidence. Stdio OpenStudio-MCP probe loaded the model and successfully queried spaces/zones. An upstream no-occupants building-summary failure was observed and documented in THIRD_PARTY.md, not treated as a successful query.

Annual weather simulation, broad HVAC system selection, existing-building input fidelity, lighting photometry, hydraulic design, brief-to-data automation and final engineering acceptance remain incomplete.

Combined verification: both BSA_TEST_AUTOCAD and BSA_TEST_ENERGYPLUS enabled; all **8 tests passed with no skips**. The pinned setup script was executed against existing local artifacts and confirmed archive checksum and clean upstream commit before reinstalling the local MCP package. A fresh-machine download path is implemented but not independently tested on another machine.
