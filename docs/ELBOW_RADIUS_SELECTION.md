# Finite elbow-radius design candidates

`bsa.elbow_radius_selection` uses installed SciPy 1.18.1 optimize.milp / embedded
HiGHS 1.12.0, with NumPy 2.5.4, to choose among explicitly supplied radius candidates.
It does not generate manufacturer data or apply a radius regulation. Existing
tee/pump candidate tools do not model coupled two-end radius budgets, while the
existing elbow authorer requires one declared radius per source corner. The thin
adapter supplies binary choice/length constraints to the upstream solver and
reuses the existing source compiler and native IfcOpenShell authoring/checks.
No optimisation or geometry engine is reimplemented; no new dependency is needed
beyond the already pinned tee extra. SciPy/wheel and HiGHS notices are preserved
under third_party/licenses. Official references:
[scipy.optimize.milp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)
and [HiGHS notice](https://github.com/ERGO-Code/HiGHS/blob/v1.12.0/LICENSE.txt).

```powershell
$env:BSA_PROJECT_ROOT='C:/ABSOLUTE/COURSEWORK'
python -m bsa.elbow_radius_selection run PLAN WORKFLOW NATIVE_TASK BASIS POLICY --out FRESH_OUTPUT
python -m bsa.elbow_radius_selection verify FRESH_OUTPUT
```

PLAN/WORKFLOW must have passing native sheet, sheet and schedule ancestry. BASIS
retains classified elevation, gauge and nominal-section interpretation from
DUCT_BACKBONE_IFC.md. The elbow authorer now permits the explicitly selected
external project workspace, preserving repository/historical boundaries.

POLICY has exactly basis (nonempty text), minimum_remainder_m and nodes. The
remainder has value, classification (assumed/design_target) and source. Each node
must correspond to an original equal-section elbow and have a nonempty finite
candidate list. Candidate fields are id, radius_m, penalty, classification and
source; no radius, penalty or remainder default exists. At most 256 candidates
are supported. Radius must exceed the outside radial half-width for this native
geometry method; this is a software constraint, not a product/code recommendation.

The MILP selects exactly one eligible candidate per elbow, minimising the sum of
supplied penalties. Every source section with known endpoint elbows reserves the
explicit remainder after both radii. Source IDs, sizes, flows and route coordinates
remain unchanged. Only the declared known-elbow reaches are budgeted; other
fittings/trims, wall/insulation, product availability, actual installation scale,
clearances and pressure acceptance remain unknown. Geometric preference is not
hydraulic or product optimality. Infeasible policy returns no selection or native
IFC, without silently dropping corners or reducing supplied radii.

The selected combination is independently checked by the original source compiler
before native authoring. Verification rebuilds the original native junctions,
checks exact source/method/solver-binary pins, reruns optimisation, reconstructs
the model and inspects the saved IFC geometry, owned ports and cap links. A forged
objective is rejected. Native artifact checks remain distinct from coordination.

## Actual source-backed scenario

An explicit design study preserves the original 1.5-width radius option and
adds host-declared 1.0/0.75-width alternatives with a 0.05 m positive known-elbow
remainder target. These are classified design choices, not measured dimensions,
manufacturer offerings, regulations or a claimed physical minimum. All original
source construction assumptions and 33 requirements remain.

The solver retains eight original choices and changes CORRIDOR-A/B. All ten
original equal-section elbows author as native geometry: 47 straights plus ten
bends, 114 owned ports and 20 coincident opposed cap links. The original-radius-
only control is infeasible and creates no native IFC. Both cases independently
verify; the source objective-tamper control rejects. Twelve focused native/source
checks pass without skips.

The raw no-waiver coordination check still FAILS: 76 intersection records and
31 clearance violations, with complete geometry coverage and no unverified solid
pairs. This is not a collision-free or fully connected design; remaining unequal
tees/multi-branch/other connections and physical/pressure acceptance stay open.
The source-wide and local IFC previews were inspected; whole-model labels overlap
and neither preview is a delivery drawing. Existing coursework DWG/PDF outputs
are unchanged. See [aggregate evidence](evidence/elbow-radius-selection.json).
