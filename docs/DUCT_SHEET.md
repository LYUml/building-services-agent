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


## Unified DXF preparation

Workflow kind `duct_sheet` takes `depends_on` pointing to an earlier `duct_schedule`,
plus `drawing`, `binding`, optional `requires_pass` and `description`. Its binding
omits `schedule_sha256`: the executor supplies the exact newly produced result hash.
It rejects replacement schedule/project inputs or hashes, pins source drawing/binding
and adapter modules, and leaves the task pending without output if sizing failed.
Changed producer bytes fail before writing. A passing task means saved-DXF preparation
only; `native_reopen_pass` stays false and plot review stays pending.

54 focused tests pass, covering inherited producer identity, mutation, replacement,
failed sizing and source/geometry checks. The actual private full-brief plan now runs
allocation, lookup, candidate sizing and drawing preparation in one invocation; all
four scoped stages pass, while nine regulatory/engineering work packages stay pending.
The saved modelspace exactly matches the corrected, previously reviewed single-line
candidate. That match does not substitute for fresh native/plot acceptance of this run.
Unified native save/reopen/plot orchestration remains incomplete.


## Repeatable native adapter

`python -m bsa.duct_sheet_native prepared.dxf settings.json --out runs/new-native --autocad <accoreconsole.exe>`
copies the prepared source into a new directory, guards active paths before writes,
saves DWG, independently reopens through cad_intake, compares explicitly named layers,
and plots through cad_sheet. Settings contain exactly `source_sha256`, `layers` and
`sheet`. The sheet uses the existing sourced window/scale/reference-handle/tolerance
contract plus optional `paper` (`A4` default or `A1`). Runtime/source/settings hashes
and unchanged copied DXF are checked. It never attaches to the user's GUI session.

Supported reviewed entities are LINE/TEXT/CIRCLE/LWPOLYLINE. Comparison uses ordered
effective attributes and polyline vertices; it does not claim nested base-building,
XDATA or arbitrary block semantic fidelity. Unknown types or changed attributes fail.
The saved PDF reference is independently measured; actual visual review stays pending
in the machine result and is recorded separately after viewing the rendered artifact.

Actual private adapter execution reopens 624 generated entities and produces A1 at
1:100; the 10 m reference measures 99.991333 mm against expected 100 mm, inside 0.2 mm
tolerance. The generated PDF was rendered and inspected with corrected D-22 placement
and no page clipping. AutoCAD's duplicate PDF PageMode warning remains; no PDF-standard
conformity is claimed. 55 HVAC tests and two existing CAD-sheet tests pass. Native
workflow registration, final titleblock and full engineering acceptance remain pending.
