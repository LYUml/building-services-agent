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

## Requirement orchestration milestone

Executed examples/workflow-plan.json from a new synthetic brief: electrical calculations/overlay, actual AutoCAD native conversion/reopen/PDF generation and actual EnergyPlus baseline/variant all succeeded. The required manual review remained pending. Every requirement acceptance remains pending review; no claim is made that tool success proves the natural-language acceptance text. The CLI returns nonzero for the pending manual task, preserving the report.

Combined test run with both native and energy engine flags: **12 tests passed**. Tests cover exact-source quote enforcement, stale brief detection, paragraph coverage, path traversal rejection, task identity restrictions, missing engine handling and source locators, in addition to previous native/energy behavior. Subsequent integrity-verifier tests passed (10 passed, 2 engine tests skipped in that focused invocation); changing a generated DXF was detected. `verify runs/workflow-demo-v2` passed input and task-artifact hash checks. Archived workflow report: docs/evidence/workflow/workflow.json.

The plan was authored by this agent from the synthetic brief. No general autonomous PDF/Word/OCR interpretation or arbitrary MEP design is claimed. The generated PDF from this workflow run has not been separately visually reviewed; earlier plot inspections do not count for this file's visual gate.

## Document intake milestone

Added read-only PDF/DOCX extraction and source locators. Parser fixtures cover Chinese Word text, table cells, headers/footnotes, tracked changes, two-page PDF text, unreadable pages, empty briefs and a Word requirement driving electrical execution. Explicit document review is required; blockers cannot be cleared merely by supplying a note.

Actual offline OCR ran on the prior synthetic AutoCAD PDF: three regions recognized; rendered image was inspected and OCR symbol/slash errors retained. Source PDF and page image bindings were verified; changed image/source hashes were rejected. The OCR sidecar, image and review observation are retained at docs/evidence/document-intake. Uncorrected OCR is not accepted as equipment IDs.

Test invocation with BSA_TEST_OCR_INPUT enabled: 19 discovered, 17 passed, 2 CAD/energy engine tests skipped. Prior real engine evidence remains independent. No broad Chinese OCR, handwriting, equation or arbitrary drawing-understanding claim is made.

Combined regression after the final OCR-plan bindings: BSA_TEST_AUTOCAD, BSA_TEST_ENERGYPLUS and BSA_TEST_OCR_INPUT enabled together; all **19 tests passed, no skips**. Updated intake skill passed the host skill validator. Source PDF is retained alongside the OCR evidence for independent read-only reproduction.
