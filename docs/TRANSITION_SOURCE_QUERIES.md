# Conditional native transition source queries

The source-network fitting adapter now has a private basis for eight saved,
centred equal-angle pyramidal contractions. It reuses the existing family
checks, native dimensions/ports, source-flow reconciliation and pinned
SciPy1.18.1 bounded interpolation. No new engine or dependency is added.

The visually inspected source is the2021 ASHRAE Principles of HVAC Ninth Edition
online fitting supplement, printed page20,Fitting4-4. Both wall angles are
checked separately before the major angle can enter the table. The ratio is
inlet A0/outlet A1 and the velocity reference is the actual owned inlet port V0.
Original floating angles are queried without rounding or snapping. The source
explicitly calls this contraction region tentative, adapted from round
Fitting4-1. That limitation is retained in every query; diagram agreement does
not establish actual product or installation applicability.

The other matching one-plane candidate remains unsupplied because printed
page19,Fitting4-2 repeats a30-degree header. No presumed20-degree correction,
coefficient selection or substitute asymmetrical4-3 source is used. Twenty-two
other transitions retain unequal angles and do not match these source families.
All original source construction, elevation, gauge and nominal-dimension
assumptions remain. Native geometry is not a measurement of installation.

The coefficients and source pages stay private in the selected coursework
workspace. Public snapshots contain only aggregate execution evidence. Internal
end-straight friction, measurement stations, adjacent-fitting interaction,
physical joints, terminal/equipment/boundary losses and full engineering review
remain unresolved. Conditional table contributions do not establish complete
pressure, a critical path or fan duty.

## Executed evidence

A fresh complete source/native analysis and table run produces31 conditional
values among76 fitting paths (previous23 plus8 transitions). Thirteen other
queries retain unpublished support and32 paths have no supplied table:45 paths
still have no numerical coefficient. All33 source requirements,31 transition
requests and20 outlet paths survive. Full pressure remains false and critical
path remains null.

Independent extraction of the selected source row, separate linear arithmetic,
recalculated native wall angles/area ratio and actual inlet-reference pressure
agree on all eight transition values to1e-12. An additional real-native negative
control changes only their source family to one-plane: all eight reject before
lookup, restoring23 finite values and preserving null pressure acceptance.
Nine source/native/flow-family/table/workflow regression tests pass, with durable
runner verification. The private basis, copied source and controls are kept in
project07_Agent_Work/project/full-network-transition-study; the fresh actual
record is under07_Agent_Work/runs/full-network-transition-fitting-data. These
are internal records, not submitted document filenames.

The standalone verify CLI independently replays the complete source/native
ancestry, basis/document/method hashes and all fitting/path outcomes; integrity
passes. Its incomplete-scope exit2 preserves pressure_budget_complete=false
and design_accepted=false. No old run was rehashed.
