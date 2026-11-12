# Native spatial schematic replay

Reuse decision: thin wrapper over existing duct_sheet_native.run,native_cad,
cad_intake.export_dwg and cad_sheet.plot;no new engine. Extend existing ordered
native comparison to POINT and existing PDF scale reference to an explicitly
selected straight LWPOLYLINE segment. Existing LINE settings stay compatible.
Curved segments,missing/noninteger/out-of-range indices reject. This uses the
installed proprietary AutoCAD2027 Core Console and existing ezdxf1.4.5(MIT).

`python -m bsa.spatial_terminal_native SOURCE --settings SETTINGS --out NEW
--autocad EXE` (one line) accepts a verified spatial drawing.json. Settings have
exactly layers and sheet;layers must cover the four generated spatial layers.
Sheet uses cad_sheet settings,with optional reference_segment_index for a straight
source boundary segment. Source hash is inherited,never overridden. Every write
uses the existing exact active-document-path guard in isolated Core Console.
User GUI applications are not attached,closed or restarted. Output labels use the
existing Supply Air Distribution filenames;the content remains a schematic.

verify(NEW) checks exact original drawing ancestry,source/method/runtime pins,
required native files,output hashes,native report and saved-export geometry
replay. Additional rendered review images are separate diagnostic artifacts.
Outputs are in the selected workspace;AutoCAD runtime is a host path.

Actual saved source:three rooms,six terminal centres,24entities. AutoCAD saves
DWG,reopens an isolated copy,exports DXF and compares effective entity attributes
and polyline vertices. A4 landscape1:100PDF has expected reference50mm and
measured49.9956667mm,within explicit0.2mm numerical plotting tolerance. This is
plot scale correspondence,not surveyed building calibration or regulation.

The actual PDF was rendered at1800px and inspected. It has all labels,but0.12m
annotation becomes1.2mm on paper and some labels cross room boundaries. Visual
acceptance remains pending;do not treat the numerical/native pass as a finished
sheet. Latest render exactly matches the inspected render by SHA256. Source
originals and earlier failed/stale studies remain untouched. AutoCAD PDF parser
reports a duplicate PageMode metadata warning;render and scale checks succeed.

See evidence/spatial-terminal-native.json. Native geometry correspondence is
verified;formal sheet layout,physical product/routing,ADPI,complete engineering
acceptance and automatic native workflow-task integration remain unfinished.

Validation:8 related tests pass,including POINT movement detection,straight
polyline reference selection/rejection and existing CAD/drawing workflow controls.

The later readability iteration addresses the small-text finding in this exact
synthetic sheet through a keyed flow schedule and explicit paper-height target.
See SPATIAL_TERMINAL_DRAWING.md and evidence/spatial-sheet-readability.json;the
original finding remains historical evidence,not an automatically cleared gate.

## Native automatic workflow task

Use spatial_terminal_native with depends_on an earlier spatial_terminal_drawing,
plan-local settings and optional requires_pass. Source/runtime replacements in
the task are forbidden. AutoCAD is supplied as a trusted host execution argument.
No runtime or failed/pending upstream drawing means pending and no native output.
Execution passes only after actual native production and verification;full manual
review and producer visual acceptance remain pending.

workflow.verify replays spatial-native evidence;delivery.context binds the exact
declared drawing/settings and passing parent/task states. The public builder
accepts --native-settings together with --drawing-settings,--air-balance and
--terminal-allocation. It creates a dedicated spatial-native-settings.json,not
the IFC recognition native-settings.json;the initial filename collision was
caught by source hash validation during testing and corrected before acceptance.
All nine brief requirements remain represented and review depends on native work.
No new engine or dependency;existing native producer/validators are composed.

Four actual scenarios run from fresh outputs: native and MOOSAS produce the same
scoped27entity schematic and real DWG/PDF;missing runtime and disabled source
produce no native output,while independent electrical passes. The two final PDFs
were rendered and reviewed. Native render exactly matches the previously reviewed
sheet;MOOSAS was directly inspected. A MOOSAS vertex-order-dependent room label
outside the plot was found and corrected using the source boundary minimumXY.
A regression test rotates boundary vertices and checks unchanged annotation
positions. All labels,legend,schedule and limitations are now visible in these
specific sheets. Numeric/visual execution does not complete engineering design.
See evidence/spatial-native-workflow.json. Original trials remain untouched.

Workflow regression:37 related tests pass with actual MOOSAS runtime enabled,
including missing-runtime/disabled-source gates and ring-order annotation checks.
