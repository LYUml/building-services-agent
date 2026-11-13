# Separate transition end-straight friction study

source_fitting_data now records transition_end_straight_study for every supported
native centred transition. It reuses duct_equivalent and the pinned MIT
Fluids1.3.1 Colebrook engine. This is separate analysis of both constant-section
ends using saved native lengths/sections and inherited source flow/air properties.
Boolean bore-cap extensions and the taper are excluded. Ring and directed-port
sizes must agree; flows must conserve mass at the inherited common density.
Negative/nonfinite lengths, mismatched dimensions/flows and overflow reject.

Each end retains its calculation, actual port and geometric body identity.
Zero supplied straight length has zero separate straight contribution; it does
not mean zero fitting loss. Per-body end totals are not summed across parallel
network paths. Existing source-table pressure paths remain unchanged, and
added_to_pressure_paths is always false. Short end lengths between nearby
fittings may not support developed flow; these are conditional developed-flow
studies, not accepted installed friction or complete fitting loss. Table station
and friction-inclusion conventions, taper friction and interaction remain open.

## Reuse research

The installed Fluids1.3.1 source and its official documentation expose conical
contraction/diffuser methods with diameter inputs. No executed basis establishes
them as unequal-wall-angle rectangular transition correlations. They are not
substituted here. The ASHRAE official database page describes a subscription
product; SMACNA describes a web exhaust-design application. Neither description
establishes an open CLI/MCP, available licence or executed applicable integration.
No purchase, account creation or database extraction was performed.

- https://fluids.readthedocs.io/fluids.fittings.html
- https://www.ashrae.org/technical-resources/bookstore/duct-fitting-database
- https://www.smacna.org/technical-standards/apps/view/exhaust-system-design

This study adds no new engine/dependency and redistributes no publisher grids.
Existing equivalent-round friction applicability and all source assumptions
remain. A fresh source/native replay is required after the adapter change;
previous table studies remain immutable historical records.

## Actual execution

A fresh real-project run covers31 transitions and62 constant-section ends.
Independent equivalent-diameter, velocity, Reynolds, Darcy arithmetic and
Colebrook residual checks agree; maximum residual is1.78e-15. Original table
results and outlet pressure paths compare exactly with the preceding study.
No new fitting coefficient is added:31/76 conditional values remain, with45
unknown. Eight targeted source/native/family/friction tests pass and their
runner receipt verifies. The source construction assumptions remain unchanged.

Three additional source-linked table/workflow regression tests pass with a
verified runner receipt. They supplement the eight targeted checks above.

The independent standalone verify CLI replays source/native ancestry, hashes,
table results, every end-straight result and unchanged path states; integrity
passes. Domain exit2 retains incomplete engineering acceptance.
