# Reading declared points from raster charts

For source-labelled circular-duct curve points, ROUND_DUCT_CHART_CHECK.md adds
complete point replay and descriptive comparison with the existing friction
engine. It preserves point-identity uncertainty and does not accept the schedule.

`python -m bsa.raster_chart_points INPUT.json --out NEW_DIRECTORY` converts
explicitly selected image pixels using a pinned, unmodified upstream calibration
function. Install the optional `raster` dependencies (NumPy2.5.4, Pillow13.0.0).
This supports linear or log10, axis-aligned XY charts. It does not identify curves,
remove grids, smooth data, fit engineering correlations or accept duct designs.

Reuse: [Huang Jianing's scientific-plot-digitizer](https://github.com/huangjn58/scientific-plot-digitizer)
commit `165b2b3e954e7185359e37f274d9c2dc5b1304f6`, MIT, copyright2026 Huang Jianing.
The original script and license are retained in third_party/scientific-plot-digitizer.
Only its pixel_to_data function is invoked; its executable path is fixed and its
SHA256 is checked before loading. The upstream automatic-mask CLI is not invoked.
No full upstream skill installation or automatic extraction integration is claimed.

Input fields are exact:

- `source`: relative path, SHA256, and a nonempty page/figure locator.
- `image`: relative path and SHA256 of the actual inspected image.
- `axes`: `x`/`y`, each with nonempty `quantity` and `unit` strings.
- `calibration`: upstream x1/x2/y1/y2 pixel/value objects and x_scale/y_scale,
  either linear or log10. X anchors share a y-coordinate; Y anchors share x.
- `pixel_uncertainty`: positive finite pixel displacement, smaller than half
  either calibrated axis span. This is a declared reading assumption.
- `checks`: at least two `{pixel:[x,y],expected:[x,y]}` held-out ticks. Both axes
  need interior ticks, not only the original calibration endpoints.
- `points`: nonempty `{id,pixel:[x,y],series,interpretation}` records. IDs are
  unique; series and interpretation describe what the host actually selected.

Both original ticks and manually selected pixels must lie inside the original
image and the calibrated axis rectangle. No extrapolation is performed. A false
held-out tick, changed source/upstream script, nonfinite quantity, rotated anchors,
missing units or existing output rejects. Rejection before writing preserves the
sources and creates no results. Explicit BSA_PROJECT_ROOT selects an external
project; documents cannot select that workspace or an executable.

Outputs are points.json and unit-labelled points.csv. Coordinate bounds use the
four corners of the declared pixel-displacement box, clipped to the calibrated
domain. Bounds do not include axis-anchor uncertainty, page skew/distortion,
curve ambiguity, hidden marks or source/method applicability. Source/image hashes
bind declared files; they do not prove that the image was rendered from the cited
source. source_image_derivation_verified, curve_identity_verified and
design_accepted remain false. Axis unit strings are declarations, not validation
of their physical interpretation. Source, wrapper, upstream and workspace method
hashes plus NumPy/Pillow versions are retained in the result.

Four targeted tests cover independent linear/reversed/log-axis expectations,
coordinate bounds, false ticks, invalid inputs, workspace/upstream/source changes
and output preservation. An actual classroom friction chart trial converts two
visually identified grid references within declared3pixel bounds. The initial
approximate endpoint selection failed held-out checks; reinspection corrected
the endpoint coordinates without widening the uncertainty. These are axis-grid
checks, not extracted diameter curves or independent duct friction readings.

The existing saved-native schedule equation review separately verifies47sections
and16,779candidate calculations with maximum absolute Colebrook residual
3.3751e-14. Both source chart readings and installed applicability remain
unverified. See evidence/raster-chart-calibration.json. Private charts, calibration
inputs and detailed outputs stay in the selected coursework workspace.
