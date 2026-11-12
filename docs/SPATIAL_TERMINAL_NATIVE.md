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
