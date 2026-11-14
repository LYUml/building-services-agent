# Source-bound VAV placement and duct-size revision

The actual layout revision moves ten VAV symbols and their associated taps to
the centres of existing rectangular four-terminal groups. All eighty terminal
positions, maximum/minimum flows, group membership and rigid topology survive.
No bend is added. This is a new single-line design scenario, not installation
approval or a silent update of the existing IFC/pressure/report scenario.

The design reuses Shapely 2.2.0 envelope/centroid geometry, pinned ezdxf 1.4.5,
fluids 1.3.1 and U-C4N/Autocad-MCP's verified MIT backend at
`6f6a538255ca9f885232e845ac32f10b4433fe3e`. Existing source/native correspondence,
finite candidate sizing, preserved-entity writing and isolated AutoCAD adapters
provide the engines. No dependency, geometry kernel or pressure solver is added.
Original upstream notices remain applicable.

```powershell
python -m bsa.vav_recenter run PLAN WORKFLOW native-sheet POLICY --out FRESH_OUTPUT --autocad HOST_ACCORECONSOLE
python -m bsa.vav_recenter verify FRESH_OUTPUT
```

Use explicit host `BSA_PROJECT_ROOT` for external project work. Policy contains
exactly `layers`, `obstacles`, `coverage`, `basis`, `classification`. Layers use
the existing four scoped supply/VAV/terminal/flex names. Obstacles use the
source-handle polygon contract in DUCT_PLAN_CLEARANCE.md. Coverage must explicitly
remain incomplete with unresolved items; classification is `design_choice` and
basis explains the engineering scope. Files/executables cannot be selected by
the source documents. Output must be fresh and outside the original workflow.

The original native→sheet→schedule→allocation ancestry is verified before and
after execution. Source rectangular group centres come from unchanged allocated
terminal positions, reconciled to the original symbols. Supported groups have
exactly four rectangle-corner centres and one vertical inlet. Moving a tap in X
requires one or two existing horizontal trunk connections. Every rigid section
must retain its direction: reversal, zero length and added bend reject.
Each moved group must strictly reduce its longest planar flex connection; total
flex must decrease and total rigid centreline must not increase. Source columns
are revalidated against actual saved outlines. Nominal rigid footprints and
flex centrelines must avoid all supplied columns. Unrelated modelspace entities
and bound table identities are preserved. Moved VAV labels use existing
conservative text rectangles and bounded vertical offsets to avoid other labels.

Geometric centring alone increased five untrimmed straight-friction path estimates
by up to 0.8374 Pa in the retained initial trial. The delivered revision therefore
also reuses existing finite candidate sizing. For each lengthened section its
additional design cap is original gradient × old length / new length, limited
further by the original source cap. Original velocity/aspect limits and candidate
dimensions are unchanged. No feasible candidate stops native delivery. These are
derived design constraints, not new regulatory limits. Source/node inspection
and fresh fluids replay must show every outlet's untrimmed straight-friction
estimate is nonincreasing (1e-9 Pa numerical comparison tolerance).

Actual result: total planar flex decreases 198.8452→197.8940 m; total rigid
centreline decreases 202.7168→201.5285 m. The largest moved-group maximum-length
reduction is 0.7426 m. D-06, D-13 and D-20 change 500×350→550×350 mm using the
original grid; the other 44 sections retain their dimensions. Of twenty outlet
paths, ten straight-friction estimates decrease and ten are unchanged, with a
maximum reduction of 1.8519 Pa. These estimates exclude fittings, flexible ducts,
equipment, trims and interactions; no complete pressure or fan duty follows.

Actual upstream writing and AutoCAD save/reopen preserve 718 generated entities;
the A1 1:100 PDF's 10 m reference measures 99.9913 mm against 100 mm. A rendered
page inspection found a moved VAV-15 label conflict; the bounded offset corrected
it and the final actual PDF was inspected again. Existing dense source labels
are not blanket annotation approval. Independent raw-native checks reconcile all
80 unchanged terminal symbol vertices, 20 group centres, 80 flex lengths,
47 rigid lengths/directions and 235 native table cells. All source allocation
bytes match. Forty-seven independent Colebrook residuals are within 1.8e-15.
Ten final targeted controls pass; earlier pre-compensation and failed fixture
records remain historical. See [aggregate evidence](evidence/vav-recenter-design.json).

Verification reconstructs the original design edits and compensated project,
checks source/runtime/artifact pins, replays upstream sizing/writing correspondence
and reconstructs native path comparisons. These are local reproducibility checks,
not authenticated provenance. Original 33 requirements and six input gaps remain.

The coursework's `Connection_Layout` DWG/PDF and associated calculation CSV are
separate from earlier `Agent_Study` outputs, report, IFC network, VAV table and
pressure ledgers; those earlier artifacts must not be combined with this revision.
Physical scale, installed lengths/elevations/slack, actual VAV ports/hardware,
open ninth-column outline, wall/insulation/fitting envelopes, chart-method
applicability, detailed room load, ADPI and full jurisdiction/design acceptance
remain unresolved. Do not propagate an old IFC body's geometry or pressure
acceptance by matching section names after changing positions and sizes.

The next major source choice is ADPI basis. Current classroom settings use a
35–160 W/m² domain; the preliminary 170.1 W/m² sensible estimate is outside it and
is not a verified room load. The already inspected manufacturer engineering
guide uses a different Type 3 circular-pattern graph and cannot silently replace
the classroom basis. A separate manufacturer-based design may alter neck sizes,
terminal count and layout; keep original coursework evidence and seek the user's
direction before that scope change. No load is clamped and no ADPI pass is given.


The recentered Connection_Layout now has a separate matching connection table
in actual native DWG/PDF/CSV, with80rawlines and140nativecells independently
reconciled. Earlier Agent_Study tables remain preserved. See
[coordinated schedule](RECENTERED_VAV_SCHEDULE.md). IFC/pressure scenario
integration and installed-length acceptance remain pending.
