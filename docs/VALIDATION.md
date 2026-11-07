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

## IFC MEP milestone

IfcOpenShell 0.8.5 generated/reopened IFC4 electrical (board and luminaire) and ventilation (fan, duct envelope, terminal) fixtures. Both passed schema/EXPRESS validation, geometry-engine bounds, exact spatial/system membership, port coordinates/directions, connection endpoint and unit checks; source input hashes unchanged. Both also executed through a source-linked BIM workflow and its integrity verification. Evidence: docs/evidence/ifc-models.

Combined regression with AutoCAD, EnergyPlus and OCR enabled plus the new IFC tests: **22 tests passed with no skips**. This includes negative BIM input/topology cases and a BIM task in a requirement workflow. The IFC files have not had BIM-viewer visual acceptance or physical clash/routing checks. Example dimensions are synthetic bounding envelopes, not measured or manufacturer-certified models. No complete electrical, ventilation, hydraulic, photometric or code acceptance is inferred.

## Circular tree pressure milestone

Executed source-quoted air and water network briefs through the new `network` adapter. The level-air tree aggregates 0.2 and 0.3 m3/s terminal withdrawals to 0.5 m3/s at its source and identifies MAIN/BR-B as critical. Under the explicit synthetic assumptions, the source total-pressure requirement is 81.9104 Pa. The water scenario gives 5057.6952 Pa dissipative loss plus 48935.1835 Pa elevation contribution, requiring 153992.8787 Pa source total pressure to retain the specified 100000 Pa outlet total pressure. These are prescribed-flow budget results, not operating-point solutions or code acceptance.

Independent tests compare laminar loss against Hagen-Poiseuille, turbulent factor against the implicit Colebrook residual, branch continuity, elevation, invalid topology, transitional-flow rejection, and visible pressure/velocity failures. A failed pressure budget correctly marks its workflow task failed while retaining its report. Input hashes stayed unchanged and both workflow artifact-integrity checks passed. Evidence is retained under docs/evidence/network; explicit assumptions are in examples/network.

Combined regression with actual AutoCAD, EnergyPlus and OCR plus IFC and network modules: **29 local tests passed, no skips**. New GitHub Actions network job is configured; no remote CI result is inferred from local success. Physical route/BIM binding, rectangular ducts, loops, balancing and fan/pump selection remain pending.

## Shared electrical coordination milestone

The same electrical project now generates saved calculations, DXF and IFC via a geometry-only companion. The companion cannot repeat XY, power, PF or circuit fields; IDs must match exactly. A reopened IFC check verifies XY centres (with explicit centre-to-corner conversion), power/PF/source properties and circuit assignments/properties. Saved calculation values, check outcomes and memberships are compared; DXF centres and labels are independently read and compared. Device schedule ties common IDs to IFC GUIDs.

The coordinated native workflow ran on actual AutoCAD 2027, saved/reopened the nested DXF as DWG and plotted a padded schematic. The resulting PDF was rasterized and visually inspected: all three symbols and labels complete with margins and no overlap. Evidence hashes, IFC, calculation data, native verification, rendered page and visual-review record are under docs/evidence/coordination. The manual engineering review remains pending; the IFC viewer/physical geometry gates are also still pending.

Tests verify missing/duplicate geometry fields rejected, corrected coordinate-reference handling, saved-calculation and IFC-power tamper detection, and propagation of a revised dotted equipment ID, XY, power/PF and circuit phase/breaker values. Full local regression with AutoCAD, EnergyPlus and OCR enabled: **33 tests passed, no skips**. Subsequent stricter saved-check/source/circuit validation passed all 4 targeted coordination tests; all 7 skills passed the host skill validator. No new upstream implementation is copied by this bridge: it reuses the already attributed ezdxf/IfcOpenShell dependencies.

This is an electrical cross-artifact bridge, not a universal building-services data model. Other discipline geometry/analysis binding, supplied-bottom-drawing integration, professional performance and complete acceptance remain unfinished.

## Radiance lighting milestone

Official pinned Radiance Windows archive was downloaded, SHA256-verified and extracted inside tools. Its ies2rad/xform/oconv/rtrace executables ran actual IES-backed optical simulations. Black-room tests matched 1000 cd inverse-square/cosine illuminance on- and off-axis within 0.3 lux; halving maintenance factor halved direct illuminance while IES input-watts metadata stayed unchanged. Invalid tilt/scene/input data is rejected; missing engine stays pending and IES files join workflow source hashes.

A 15-point synthetic rectangular reflective-room example executed through its quoted workflow. Direct and reflected results were computed with increased-bounce/division verification, and its maximum relative change was about 3.5%, below the explicit synthetic 10% tolerance. These are arithmetic sensor statistics, not a regulatory task-area result. Recorded outputs under docs/evidence/lighting preserve scene, points, raw command diagnostics, illuminance and integrity metadata. Actual manufacturer's photometry, exact building geometry, grid coverage, glare/daylight, native coordination and final acceptance remain pending.

Full local regression with actual AutoCAD, EnergyPlus, OCR, IFC, network and Radiance branches: **37 tests passed, no skips**. Later explicit header/unsupported-field hardening passed all 4 targeted lighting tests. Pinned Radiance setup was executed and verified extracted files against archive contents. GitHub Actions lighting job was added; no remote job result is inferred from local success.

### Fixture byte preservation

Found and corrected a cross-platform reproducibility defect: Windows working-tree CRLF bytes differed from the prior Git index's normalized LF bytes, invalidating source-linked brief hashes after non-Windows checkout. .gitattributes now preserves exact example/evidence bytes, and tracked files were re-indexed without changing their working input contents. An independent checkout-index snapshot validated all 5 source-linked example plans with their recorded brief hashes. A regression test now validates every tracked example plan. The line-ending-only index changes also preserve archived artifact hash bindings; no completed coursework file was touched.

Final combined local regression after adding fixture-byte preservation: **38 tests passed with no skips**, with AutoCAD, EnergyPlus, OCR, IFC, network and Radiance enabled. Raw machine evidence is exempt from whitespace rewriting; example sources retain CRLF-aware whitespace checks while preserving exact bytes.

## Shared fixture lighting milestone

The new electrical_lighting workflow reuses the electrical device positions and geometry space/envelope heights in actual Radiance. Explicit sourced offsets locate the optical origins; translated-room tests preserve local geometry. Missing assignments, duplicated position inputs and nominal IES/electrical watt mismatches are rejected. The fixture's 40 W metadata is checked independently of its synthetic candela distribution and maintenance factor.

The synthetic shared-lighting plan executed coordinated calculations/DXF/IFC, Radiance and actual AutoCAD DWG save/reopen/PDF generation. Both technical tasks passed; manual physical/visual/domain review remains pending and design_accepted stays false. Recorded workflow input/artifact integrity verification passed. This PDF has not been separately visually inspected. Selected reports and the regression log are retained under docs/evidence/shared-lighting; reports retain original run paths and hashes rather than claiming the evidence subset is a complete portable run.

Combined local regression with AutoCAD, EnergyPlus, OCR, IFC, network and Radiance enabled: **42 tests passed, no skips**. The previous commit c1da0edbaa5b5cbc2bc2a20c93abd8d9dee05fe8 also completed all four remote GitHub Actions jobs successfully in run 42412285420 (electrical, network, IFC and lighting). That remote result predates this binding change; its updated Windows CI integration has not yet been verified remotely. Full engineering acceptance and the broad project goal remain unfinished.

## IFC/pressure geometry binding milestone

A source-linked synthetic ventilation brief now executes the network_coordination adapter. The model owns the straight duct's 3 m port-centre length, source-backed 0.4 m internal diameter and 2.25 m node elevation; these numbers are omitted from network inputs and derived before the actual fluids calculation. IFC4 is authored/reopened/schema-checked and its saved port coordinates/diameter properties are independently compared with derived network input. Original input hashes and the workflow artifact-integrity check passed. Selected reports, IFC and regression log are retained under docs/evidence/network-binding; this is a selected evidence subset, not a portable complete run directory.

Tests cover derived dimensions without source mutation, duplicate-input rejection, model elongation propagation, endpoint mismatch, missing/oversized internal diameters, connected multi-piece routes, disconnected/reused piece rejection, actual IFC and pressure execution, and detection of a changed diameter in saved IFC. Combined local regression with all installed engine branches enabled: **47 tests passed with no skips**. The network skill passed the host validator; Linux CI is configured to run the new binding tests with BIM/network dependencies, but no remote result for this change is claimed.

The model still uses envelope solids. Circular section and K evidence, junction physical detail, arbitrary routing, clashes, loops, balancing, pump/fan operating point and full professional acceptance remain pending. The broad goal is not complete.

## Source drawing intake milestone

Read-only DXF inventory and isolated AutoCAD DWG export now feed a drawing_intake workflow task. A selected source SHA256 binds boundary handles and an independent LINE dimension. The synthetic millimetre L-shaped boundary gives 18 m2, independently checked as 6*2 + 3*2. Its native DWG was actually created/exported by AutoCAD 2027; original and copied DWG bytes remained unchanged during intake and the derived area stayed 18 m2. Core Console's observed QUIT prompt asks whether to discard changes; the adapter answers yes and verifies the isolated file hash rather than assuming generic save-prompt wording.

Tests cover the nonrectangular area, unit mismatch/unitless handling, stale source selection, open/curved/width-bearing polygons, crossing/nonplanar boundaries, clockwise large-world-coordinate area, nested/unsupported inventory visibility, output/source overlap, workflow source integrity and missing native engine handling. Combined regression with AutoCAD, EnergyPlus, OCR, IFC, network and Radiance enabled: **53 tests passed with no skips**. The modified requirements skill passed the host validator. The source-linked DXF workflow and its input/artifact integrity verifier passed. CI now runs the portable example; no remote result for this change is claimed.

Selected native source, exported DXF, selection, inventory, measurements, command log, workflow evidence and regression log are retained under docs/evidence/drawing-intake. Paths in manifests identify original run locations; this subset is not a complete portable run directory. Source-handle/measurement evidence applies to the supplied synthetic fixture only. Nested geometry interpretation, arbitrary DWG fidelity, visual inspection, semantic space inference, existing-base overlay integration and fixed-scale deliverables remain pending. No completed coursework file was used or modified.

## Preserved source base and physical plot scale milestone

The base_overlay adapter now places common electrical devices onto a unit-proven copied source drawing. Supported base geometry, block contents, layer state and INSUNITS are compared after DXF authoring and after actual AutoCAD save/reopen/export. Source DXF and native DWG base routes were both executed on the synthetic L-shaped fixture with three devices. All source hashes stayed unchanged. The final source-quoted native workflow and its artifact-integrity verifier passed; a separate portable workflow also passed.

The A4 landscape model-window plot uses explicit 1:50 scale, not Fit. An independent pypdf graphics-path reader verified the six-metre reference at its expected page location: expected 120 mm, measured 119.9726667 mm, within the supplied 0.2 mm tolerance. Page dimensions were about 297.039 by 209.903 mm. Tests verify matrix stacking and exclusion of nonpainted clipping paths, and reject impossible window/scale settings. AutoCAD's PDF emits a duplicate PageMode dictionary warning; it remains visible in the log. Actual rendering and reference checks passed despite this metadata warning.

Visual inspection exposed text/symbol collisions in initial synthetic placements. A versioned placement/label-offset revision corrected them without editing base entities. The final workflow PDF and the native-DWG-base PDF render to the same SHA256 image bytes; inspected imagery shows all three separate symbols and labels, original text/boundary/block symbol and reference line with margins. The exact final PDF/image hashes and restricted review scope are recorded in docs/evidence/base-overlay/visual-review.json. A limited schematic visual pass does not clear professional title-block, manufacturer, placement, protection or code gates; design_accepted remains false.

Final combined local regression with AutoCAD, EnergyPlus, OCR, IFC, network and Radiance enabled: **60 tests passed, no skips**. Overlay tests include source preservation/tamper rejection, metre-to-millimetre rigid transforms, explicit annotation scale, unsupported bases, workflow input tracking, missing sheet engine handling and real native reopen/physical PDF scale. The electrical skill passed the host validator. Portable CI execution was added; no remote result for this commit is claimed. Evidence includes selected native/DXF drawings, PDF, render, verification reports and regression log; reports retain original run paths and do not make the evidence subset a complete portable run.

## Conditional catalogue sizing milestone

The network_design adapter preserves baseline calculations, evaluates every permitted diameter/roughness combination and reruns the chosen feasible network. The synthetic branched-air brief evaluated all 125 combinations, with 18 meeting the unchanged velocity/pressure/continuity checks. Its deliberately undersized baseline failed velocity/pressure and required 734.4568129 Pa against a 300 Pa supply. The minimum supplied material-score result uses MAIN 0.35 m, BR-A 0.20 m and BR-B 0.25 m internal diameters, scores 63 synthetic points and requires 125.5978604 Pa. This choice matches independently calculated per-branch velocity lower bounds; it is not a real product or cost selection.

Independent laminar tests compare each candidate pressure to Hagen-Poiseuille, verify unchanged demand/route/K/targets, deterministic ties, exact enumeration bounds and source preservation. Transitional candidates retain explicit errors; no-feasible workflow tasks fail with their comparison evidence preserved, and changed selected inputs fail artifact-integrity verification. An additional actual CLI infeasibility scenario restricted the air network to its three undersized choices: one candidate, zero feasible, no selected network, exit status 2. Its catalogue and comparison are retained alongside the successful example.

Full local regression with actual AutoCAD, EnergyPlus, OCR, IFC, network and Radiance enabled: **67 tests passed with no skips**. The modified network skill passed the host validator. The source-linked design workflow and integrity verification passed; new network CI steps are configured but no remote result for this change is claimed. Selected comparison/CSV/HTML, baseline and selected reports, selected input, no-feasible evidence and regression log are under docs/evidence/network-design. Manifests retain original run paths; this selected subset is not a complete portable run directory.

Search optimality is limited to the explicit finite catalogue, fixed prescribed-demand routes/local K and supported circular tree method. Material score is not money or carbon. Updating outside dimensions and authored BIM, fitting applicability, balancing, operating points and complete professional acceptance remain pending. The broad goal remains active.
