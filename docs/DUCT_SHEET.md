# Bound single-line duct sheet updates

`python -m bsa.duct_sheet source.dxf results.json binding.json --out runs/new-sheet`
updates explicitly bound schedule TEXT entities in an existing single-line sheet.
It reuses ezdxf 1.4.5 and the existing duct schedule result; no CAD engine or physical
routing optimiser is reimplemented.

Binding has exactly `source_sha256`, `schedule_sha256`, `basis`, and `sections`.
The last is keyed by every unique result section ID. Each entry contains a modelspace
`line_handle`, directed three-component `from_m` / `to_m`, and five `cells` in order:
ID, L/s, width x height mm, actual m/s, equivalent-round Pa/m. Each cell has `handle`
and `expected_text`. Source units must be known. Centreline endpoints are checked
within 1e-8 m, and all line/text handles must be distinct. Missing/changed cells,
geometry, source hashes or nonpassing schedules reject. This explicit binding is
not automatic interpretation of an arbitrary drawing.

The adapter retains original centreline geometry and other entities, updates selected
size/flow/friction text and reopens the saved DXF. Modelspace DXF tags outside edited
cells must remain unchanged, including polyline vertices. It does not regenerate
physical-width ducts, fittings, labels, routing or full sheets. Native DWG and PDF
acceptance are separate; its result deliberately leaves those gates pending.

53 focused tests pass, including changed geometry/cells and failed-study rejection.
Actual private execution updates 47 rows / 235 cells. Separate AutoCAD Core Console
save and independent DWG reopen match 47 calculated rows and 624 BSA entities,
including effective DXF attributes and polyline vertices (1e-7 drawing-unit absolute
tolerance, default attributes resolved, handles/owners excluded). The actual plotted
PDF was rendered and inspected: the plan and complete schedule are visible without
page clipping. D-22 placement near a wall, final titleblock and full ADPI/source,
coordination and engineering acceptance remain pending. Native verification is actual
private evidence, not yet incorporated in this callable or a workflow drawing task.
