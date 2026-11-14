# Smooth rigid outlet bend comparison

This is a separate construction study on the existing logical supply model, not
selection of a flexible-duct product or replacement of the course scheme.
The native IFC geometry is unchanged. The existing round_bend_quantities reader
checks actual hollow swept profiles, independent axes, units and owned ports.
smooth_round_bend then calls pinned MIT fluids 1.3.1 bend_rounded, Rennels method,
with actual internal diameter, centreline radius and bend angle. No loss engine
is reimplemented. The upstream module and adapter hashes are recorded in
evidence/smooth-rigid-bend-study.json.

The upstream documentation attributes this method to Rennels and Hudson (2012).
The original book has not been independently inspected. The documented method
covers smooth bends from 0 to 180 degrees and R/D above 0.5; this adapter uses the
existing native minor-bend reader and restricts the study to turbulent flow.
The actual model has D=0.2032 m and R=0.3048 m. Both branch bends per terminal
are evaluated at both prescribed flow conditions: 320 rows in total. Their
conditional losses range from 0.2070 to 4.5878 Pa at maximum flow, and 0.04039 to
0.85067 Pa at minimum flow. These are individual bend values, not fan duties.

The alternative explicitly assumes hydraulically smooth rigid branch walls
(roughness zero). Its 160 downstream straight spans are recomputed consistently;
the main-network roughness and other existing component values are retained.
The method already includes arc friction, so no extra fL/D term is added for the
bend arc. Only the separate native straight lengths receive straight friction.

Fresh pressure-path reconstruction gives 354 conditional numerical component
values and 104 unresolved directed component paths in each case. The unresolved
classes are four compound-main paths, 20 VAV losses and 80 plenum paths. Every
terminal path retains three numerical gaps, three logical-equipment interfaces
and unknown complete pressure. This does not clear the global requirements for
physical joints, equipment airways, pressure stations, adjacent-fitting effects,
actual elevation or diffuser discharge. The short upstream leads and subsequent
disturbances are not accepted as isolated, fully developed experimental conditions.

Actual controls reject corrugated-flex selection, boolean flow and a laminar
study point. A matched-Reynolds velocity-squared control passes. All 160 terminal
rows reconcile the two new bend contributions to the change in conditional
component subtotal, with arc friction included once. Main geometry and the
original logical-network pressure evidence remain separate and unchanged.

Miller was examined but not selected: its documented lower angle is 10 degrees,
while this model contains smaller bends, and its downstream recovery correction
requires an explicit disturbance-length interpretation. No silent 20D default,
angle clamping or extrapolation was adopted. A lower smooth-wall result is not an
uncertainty bound for installed corrugated flexible duct.

Course files under 05_Calculations/Connection_Layout contain Smooth Rigid Bend
Study.csv (320 rows), Smooth Rigid Terminal Pressure Study.csv (160 rows), and
Smooth_Rigid_Bend_Check.json. These are conditional design comparisons.

Reference: https://fluids.readthedocs.io/fluids.fittings.html#fluids.fittings.bend_rounded
