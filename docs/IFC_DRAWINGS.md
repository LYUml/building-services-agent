# Saved IFC segment schedules and projected diagrams

The `ifc_drawing` workflow task reads a source IFC, or the registered output of an earlier supported IFC producer, with sourced drawing settings. It extracts **every IfcPipeSegment and IfcDuctSegment**; other element classes are listed explicitly as excluded. It generates a pipe/duct schedule and an editable projected centreline DXF from the saved model rather than retyping hydraulic dimensions.

```powershell
python -m pip install -e ".[bim,network,clash]"
python -m bsa.workflow execute examples/water-riser/delivery-plan.json --out runs/water-delivery
python -m bsa.workflow verify runs/water-delivery
# Standalone IFC:
python -m bsa.ifc_drawing source.ifc --settings examples/water-riser/drawing-settings.json --out runs/drawing
```

Settings require `projection_axes` (two distinct ordered X/Y/Z axes), `annotation_height_m` (0.001 to 1 m) and an explicit `source` description. Projection coordinates are metres. X/Z produces an elevation view; X/Y is a plan projection. An end-on segment fails drawing generation instead of becoming an invisible zero-length line. The geometry is an orthographic centreline projection, with true 3D lengths labelled separately; projected length is recorded in JSON. This is not a developed riser, hidden-line projection or installation drawing.

Supported segments must have one direct Body/SweptSolid containing an IfcExtrudedAreaSolid with an IfcCircleHollowProfileDef, positive normal extrusion, explicit rigid product/solid placements, and one placed SOURCE/SINK port at the actual profile endpoints. Radius, wall thickness and depth determine inside/outside diameters, length and analytic wall volume. Nested placements and circular profile offsets are applied, and declared units are resolved to SI metres. Rotation is supported by this reader even though the current authoring adapter only creates axis-aligned bodies. When present, metre-valued BSA diameter properties must match the saved native profile and BSA source descriptions must be nonempty. Plain IFC without project-specific properties is supported: missing metadata is recorded and dimensions are explicitly attributed to the declared profile/placement geometry and the input file SHA256, not to a manufacturer or measured installation. Wall volume is an analytic geometry quantity, not mass, fluid volume or a product bill of materials.

Unsupported/missing/mapped/compound segment bodies, inconsistent diameter properties, mismatched ports and incomplete segment coverage fail the adapter. `drawing.json` retains errors and excluded classes; `segments.csv` retains readable supported segment records. A failed geometry extraction does not emit a partial diagram that could be mistaken for full coverage. Non-segment equipment, fittings and insulation are not drawn by this adapter.

Outputs are `segments.csv`, `drawing.json`, `segments.dxf` and `preview.svg` when drawing succeeds. Schedule rows preserve source object/port GUIDs, system GUIDs, directed world endpoints and provenance. Pipe-axis, label and leader layers are separate. Every segment-linked DXF entity carries the saved IFC GUID as BSA_IFC XDATA. The DXF is reopened and its identities, endpoints, annotation positions/text and segment count are reconciled. The SVG uses the same projected centreline/label data, but a preview inspection does not establish native DWG or printed sheet quality. Inputs and generated artifacts are hashed; source bytes remain unchanged.

The synthetic vertical-water delivery plan executes electrical calculations, model-aware water sizing, saved-IFC clearance and this drawing task. The selected two 2.5 m hollow pipe bodies produce two schedule rows and two model-linked axis lines, with 32 mm bore and 40 mm outside diameter. Tests also cover native millimetres, rotated placements, end-on projection failure, unsupported segment geometry, conflicting metadata and artifact tampering.

The optional native stage below checks AutoCAD reopen and a physical print reference. Equipment/fitting symbols, installation details, fabrication quantities, product suitability, BIM-viewer review and complete professional acceptance remain separate pending gates. The broader agent objective is not complete at this diagram milestone.

## Native diagram delivery

`ifc_native` now converts the generated LINE/TEXT metre diagram through isolated AutoCAD 2027 Core Console processes. It accepts either an earlier `ifc_drawing` dependency or an explicit generated `dxf`, plus a sourced sheet configuration. An unavailable AutoCAD engine or failed/pending drawing producer leaves the task pending. It never attaches to the user's GUI session or closes their drawings.

```powershell
python -m bsa.workflow execute examples/water-riser/native-plan.json --out runs/water-native --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
python -m bsa.workflow verify runs/water-native
```

`native-sheet.json` requires the explicit metre-coordinate window, scale denominator, PDF tolerance (at most 1 mm), provenance and an existing reference IFC GUID. Exactly one BSA_PIPE_AXIS line must carry that GUID. The supplied window must fit A4 landscape at the requested scale. In the synthetic example a 2.5 m pipe axis is independently found in the PDF at approximately 49.996 mm at 1:50, against a 50 mm expected length and 0.2 mm tolerance.

The adapter copies the input DXF, checks the active drawing's exact path before SAVEAS, then reopens a copy of the saved DWG in another Core Console process and exports a read-only DXF audit. Reconciliation checks native geometry, rendering attributes, layers, text/positions, metre units, the complete set of model entity handles/counts and every BSA_IFC XDATA value. Unexpected entities or lost GUID data fail verification. The plot also checks its active path; the saved DWG and source input bytes must remain unchanged during export/plot. Generated export/script/log files remain available as evidence.

The PDF verifier reads actual vector paths and page transforms; command success alone is insufficient. `native-verification.json` records physical reference evidence and leaves actual visual review pending. Render the real output and record a separate artifact-hash-bound review of label legibility, overlaps, clipping, margins and linework. `docs/evidence/ifc-native` retains such a scoped review of the synthetic example. It is still a centreline diagram: equipment, fittings, insulation, installation details, complete sheet standards and engineering acceptance remain pending.
