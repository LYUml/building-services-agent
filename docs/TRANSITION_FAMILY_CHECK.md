# Centred transition source-family checks

The existing fitting-table adapter accepts optional `transition_family` with
`centred_one_plane` or `centred_equal_angle_pyramidal`. It checks actual saved
transition quantities before coefficient lookup, in addition to the independently
required source flow-change declaration. Failed families retain a null coefficient.
Non-transition fittings cannot carry a transition family.

One-plane requires one exactly unchanged plane and a positive other wall angle.
Equal-angle pyramidal requires both positive included wall angles and agreement
within 1e-6 degrees. This is numerical equality, not a published fabrication
allowance. Both require contraction or expansion; mixed width/height changes do
not qualify. The reader already checks centred native rings. A maximum angle
alone cannot establish either family. Optional means old reviewed bases retain
their existing conditions; no retrospective family acceptance is inferred.

## Source inspection and real-project screening

The privately held 2021 ASHRAE Principles of HVAC 9th edition fitting supplement
was visually inspected at printed pages19-20. Fitting4-2 depicts a symmetrical
rectangular transition with two sides parallel; Fitting4-4 depicts pyramidal
geometry with equal included angles in both planes. Fitting4-3 has three sides
straight and does not match the supported centred construction. Both4-2 and4-4
label the contraction region tentative, adapted from round Fitting4-1.
The4-2 header repeats30 degrees; no silent correction to20 is made. Queries
must avoid ambiguous support or obtain authoritative clarification.

Of31 saved real-project transitions, one passes the one-plane screen, eight
pass equal-angle pyramidal and22 pass neither. All nine matching candidates
are contractions inside the displayed outer axis bounds. These are geometry
candidates only: no transition coefficient has been added, no complete pressure
or fan duty established. The previous23 finite conditional paths remain23/76.
Publisher coefficient grids, source pages, identifiers and coursework records
remain in the selected private project workspace.

## Reuse and validation

This adds thin applicability checks to duct_transition_quantities and the
existing duct_fitting_data/SciPy adapter, without a new solver or dependency.
Source attribution remains ASHRAE2021; protected tables are not redistributed.
Native generated contraction/expansion/one-plane/equal-angle/mixed cases and
negative shallow-second-plane/unsupported-family/non-transition checks execute
with existing fitting/source-workflow regression tests. Historical run hashes
are preserved; changed methods require fresh runs rather than rehashing old ones.
