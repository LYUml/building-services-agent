# Comparing manual round-duct chart readings

`python -m bsa.round_duct_chart_check BASIS.json --out NEW_DIRECTORY` reuses
raster_chart_points and the existing fluids-backed duct_equivalent engine. Install
the repository's pinned `raster` and `network` optional dependencies. There is no
new friction solver, automatic curve recognition or design acceptance flag.

The basis requires exact fields:

- `points_project`: relative path to the original raster point configuration.
- `points_result` and `points_result_sha256`: the original saved points.json.
- `air`: density_kg_m3, viscosity_Pa_s and roughness_m in SI.
- `air_basis`: one `{classification,basis}` record for each air quantity;
  classification is given, assumed or measured. The basis text is a declaration.
- `diameters`: exactly one `{point_id,diameter_m,source_label,identity_observation}`
  per original point. The host records which visible curve was followed and why.

The complete raster result is regenerated in a temporary directory and compared
with the saved result. Changed sources, points, metadata, methods or declared
hashes reject; an updated hash alone cannot accept an edited reading. Units must
be L/s and Pa/m. The diameter interpretation is still a reviewer assertion, not
authentication of a graphical label. Output stays outside the saved point folder
and cannot contain source files. External work uses explicit host BSA_PROJECT_ROOT.

For each interpreted diameter, a computational square is chosen whose existing
equivalent-round conversion gives that exact diameter. The existing engine then
computes round-duct friction at the center flow and both flow interval endpoints.
That square is neither a proposed physical section nor CAD geometry. The diameter
correspondence is checked with relative tolerance1e-12 and zero absolute tolerance.

comparison.json retains the original manual point, its declared pixel-derived
coordinate intervals, air classifications, equation values, signed relative center
difference and whether the two endpoint ranges overlap. The endpoint range is a
descriptive comparison, not a proof of complete error bounds or source equivalence.
It excludes anchor uncertainty, scan skew, curve confusion and unknown chart
operating conditions. Overlap never verifies curve identity, satisfies a requested
graphical sizing method or accepts the full duct schedule. All engineering and
curve/image acceptance flags remain false. Sources/methods and fluids version are
recorded; original point outputs remain unchanged.

Fourteen targeted chart/engine tests pass. They include an independent Colebrook
residual from the resulting pressure gradient, retained non-overlap, edited-point
replay rejection, source changes, missing/duplicate diameter interpretations,
incompatible units and output preservation.

Actual execution uses two manually selected visible points on the classroom
chart's labelled1000mm curve, near10 and12m3/s. Center equation gradients exceed
the image center readings by approximately3.9% and4.6%. The flow-endpoint equation
ranges overlap the declared3pixel reading ranges. These are two approximate manual
observations, not47section graphical verification. Density and roughness follow
the chart heading; viscosity remains an explicit numerical assumption. No point
was moved and no pixel uncertainty widened to obtain overlap. Source images,
inspected detail crop, exact inputs and detailed outputs stay in the coursework
workspace. See evidence/round-duct-chart-comparison.json.
