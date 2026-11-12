# Bounded automatic terminal design candidates

This CLI reduces manual terminal-count/position preparation by composing existing
source-pinned room balance, Shapely2.2.0 polygon intersection/representative points,
nearest-centre service allocation and fluids1.3.1 catalogue interpolation.
It adds bounded enumeration and an explicit objective, not a new geometry kernel,
pressure solver or comfort prediction. Existing attribution/licences apply.

```powershell
.venv/Scripts/python -m bsa.spatial_terminal_search ORIGINAL/terminal-performance.json --policy POLICY.json --drawing-settings DRAWING.json --out runs/NEW
```

The policy has exactly grids, objective and product_from_terminal. Grids and
objective are value/source/classification records; classification must be
explicitly design_choice. Grids is a unique list of [columns,rows], up to32
shapes/16terminals per shape (computational bounds, not engineering criteria).
Objective is fewest_terminals_with_catalogue_coverage. Equal counts follow the
declared grid order. product_from_terminal maps each original room GUID to an
existing selected terminal in that same room. It inherits that terminal's exact
catalogue/settings and source classifications; no unsourced product is selected.

For every original room the declared bounding grid is clipped to its exact
source polygon. Each positive cell supplies a Shapely interior representative
point. Empty cells reject the grid; counts are never silently reduced. Existing
nearest-centre allocation assigns actual polygon service areas and inherits
original load/density/air properties and turndown unchanged. Both maximum and
minimum cases must lie within the same original manufacturer's source table.
No clamping, extrapolation, room-flow replacement or hidden minimum-flow default.

Every attempted grid, rejection and case remains in search.json. The selected
basis/products are generated only if every room has a feasible candidate.
Otherwise no partial candidate/drawing is published. A feasible result is rerun
through spatial_terminal_revision, allocation and performance, then optionally
through spatial_terminal_drawing. verify(folder) reconstructs the search and
checks exact inherited products, selected centres, nested reports and artifacts.

This is standalone candidate generation, not a new workflow release. The original
full workflow/requirements and unresolved inputs remain authoritative and are
not edited or accepted. Do not copy old per-terminal physical geometry bases to
new terminal IDs or declare coordination passed. Whole-plan materialization,
physical device/joint/routing design, ADPI/acoustics, regulatory and complete
engineering acceptance remain unfinished. No global optimum is claimed beyond
the explicitly sampled grids or among alternate products.

Executed native/MOOSAS source chains each propose five terminals from an explicit
six-terminal baseline, with identical keyed positions and inherited flows.
All10maximum/minimum cases are within the source table. An infeasible-grid control
publishes neither candidate nor drawing, and changed chosen positions reject.
See evidence/automatic-terminal-search.json. These are synthetic engineering
studies; the BSE3227 coursework is unchanged.

The generated schematic also passed the existing isolated AutoCAD DWG save/reopen
and1:75 PDF reference check. Initial PDF schedule clipping was found by actual
render inspection and retained. A separate explicit lower plot window corrected
it; the final single page shows all five rows. That window adjustment is not yet
automatic. Schematic centres are not physical installation geometry. See the
separate visual evidence; native report acceptance remains pending.

Validation:18related tests ran,17passed and1optional test skipped. No full-suite
claim. Source-bound native/MOOSAS/infeasible execution and changed-position
controls were additionally executed; all original source bytes remain unchanged.
