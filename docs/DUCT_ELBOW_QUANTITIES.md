# Native rectangular bend quantities and conditional table study

`bsa.duct_elbow_quantities` reads the existing hollow rectangular quarter
revolution and its independent saved circular Axis. It authors no geometry and
supplies no built-in coefficient. Full source/native producer inspection is
required before design use.

`source_fitting_data` now attaches these quantities to every original BEND
request and exposes them through the existing table engine:

- bend_radius_over_radial_width / bend_height_over_radial_width
- bend_angle_deg
- bend_centerline_radius_m / bend_centerline_arc_length_m
- bend_radial_internal_width_m / bend_normal_internal_height_m
- bend_hydraulic_diameter_m / bend_hydraulic_reynolds

W is clear width in the bend's radial plane; H is clear dimension normal to it.
Radius comes from literal native profile placement, checked against the saved
circular Axis. Local revolution/profile conventions, positive clear dimensions
and thickness, outside throat clearance, quarter angle, directed owned port ends
and actual Axis stations must agree. Radius metadata alone cannot substitute.
Chords, nonquarter bends, unsupported profiles/axes or invalid source air reject.

Rectangular design velocity is Q/(WH). Hydraulic diameter is 4A/P and hydraulic
Reynolds is rho*V*Dh/mu with unchanged source conditions. These are geometric/
design quantities, not measured operation or automatic source applicability.
The general hydraulic-diameter convention is described in
[ASHRAE Fluid Flow](https://handbook.ashrae.org/Handbooks/F21/IP/F21_Ch03/F21_Ch03_ip.aspx).
Detailed source-correlation definition, regime, fabrication, surface/friction
stations and interaction applicability remain review-required.

Existing IfcOpenShell geometry/Axis APIs and pinned SciPy 1.18.1 interpolation
are reused. Native literal sections must match recovered material caps before
canonical dimensions/velocities are used. No ratio is snapped or table bound
widened. Requested bend quantities on other fitting types remain unavailable.

## Real source study

The official 2021 supplement's printed page12, Fitting3-5, was rendered and
inspected, including sketches and angle/Reynolds correction information. Its
base/angle/Reynolds factor product is interpreted explicitly. Actual quarter
bends use its 90-degree angle factor. Seven actual bends require bounded
Reynolds interpolation; three use its explicit high-Re constant region. The
latter query domain has a voluntary finite numerical ceiling, not an asserted
published validity maximum.

Ten curved native bends are screened under that source interpretation. No
round-pipe, splitter-vane or miter correlation is substituted. Publisher grids,
derived grids, PDF and images stay private/ignored. Only generic code, fictional
controls and safe aggregate results are public. Source rows are additionally
extracted from the actual PDF text and checked against the inspected page.

These remain conditional local-dynamic contributions. Reynolds/source definition,
whole-fitting friction/stations, adjacent joints and interactions, products and
complete path/fan pressure remain pending. Previous runs retain original method
hashes; new elbow-enabled outputs are generated fresh, never rehashed in place.

The real fresh study preserves 76 fitting paths and now records 23 conditional
table values (13 prior main paths plus 10 bends), 13 sparse-support requests and
40 paths with no supplied table. Fifty-three paths still lack a numerical
coefficient; every physical application remains review-required. All 31 native
transition requests, 20 outlet paths and 33 original requirements remain.

Eleven native/source/interpolation/workflow tests pass. Actual independent
bilinear base-table interpolation times a separately extracted Reynolds row,
then actual native common-section reference pressure, agrees for all ten bends.
The standalone source_fitting_data verify CLI also replays the complete
source/native/flow/correction study successfully. Full pressure, critical path
and design acceptance remain unresolved. See
[safe aggregate evidence](evidence/native-elbow-fitting-data.json).
