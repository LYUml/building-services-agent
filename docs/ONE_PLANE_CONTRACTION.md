# Conditional one-plane contraction query

The saved reduced-branch network now has one additional source-bound numerical
query using the existing native geometry reader and bounded SciPy table adapter.
No engine, dependency or geometry was replaced.

The privately held ASHRAE 2021 Principles of HVAC ninth-edition supplement,
printed page 19, Fitting 4-2 was visually inspected. Its repeated 30-degree
headers remain literal. At both selected contraction rows the duplicate entries
agree; the common ordinate and the unambiguous 45-degree ordinate define this
restricted query. No expansion data, inferred 20-degree header or angle snapping
is used. The publication calls the contraction data tentative, adapted from
round Fitting 4-1; that limitation remains binding.

The actual saved transition has one unchanged plane, a 30.000000000000004-degree
included angle in the other, and inlet/outlet sections 0.5 x 0.45 / 0.5 x 0.35 m.
The inlet-referenced coefficient is 0.05714285714285716. Conditional local dynamic
loss is 0.8311127729644842 Pa at maximum flow and 0.13297804367431748 Pa at the
given 40-percent flow. Independent Decimal interpolation and pressure replay
agree. Every other fitting result is unchanged.

Both cases now have 30 finite conditional paths and 33 numerical gaps.
This is additional calculation evidence, not a pressure-saving design change.
Physical applicability, adjacent-fitting interaction, fitting friction/stations,
terminal/equipment losses and full fan duty remain unresolved. Existing delivered
reports now use the 30/33 calculation snapshot; all 240 cells across 40 outlet
case rows reconcile to the latest ledgers. Native geometry and drawing artifacts
are unchanged. Protected tables and project scripts remain in
the selected project workspace.

Private evidence: `07_Agent_Work/runs/reduced-branch-network-reviewed/one-plane-source-extension-reviewed/review.json`.
The first output directory is retained as an unexecuted workspace-guard failure.
