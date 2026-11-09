# Pinned pdf2plot trial

Upstream: [Adam Kucharski / pdf2plot](https://github.com/adamkucharski/pdf2plot), MIT, commit 99a8ee1d1e24a0859fea1cd06011280734ab82cb. Original license is retained here. File hashes are in lock.json. PyMuPDF 1.26.7 runs in an isolated repository environment under its AGPL/commercial licensing; no runtime/environment is committed. WebPlotDigitizer was also surveyed (AGPL frontend, browser calibration), but this PDF exposes native vector paths and the pinned pdf2plot Python calibration helper can be invoked directly. No upstream README claim substitutes for execution.

Bootstrap exact helper files with `.venv/Scripts/python scripts/bootstrap_pdf2plot.py`; add `--install` to create/install the pinned isolated runtime. Then run:

```powershell
tools/pdf2plot-runtime/Scripts/python scripts/extract_tcf_vectors.py --pdf runs/tcf-fan-intake-v1/tcf-m300.pdf --helper tools/pdf2plot-99a8ee1/pdf2plot_helper.py --out runs/new-tcf-vectors
```

The source-specific adapter checks the reviewed PDF hash, page, line primitives, speed labels, axis tick labels and exact source grid. It extracts with native PyMuPDF get_drawings, splitting at discontinuous line endpoints. It then delegates logarithmic calibration and CSV export to the unchanged upstream helper. An independent exponential coordinate reconstruction checks every exported point against the upstream CSV's six-significant-digit precision. Native source coordinates are retained. Green stroke identity allows only 16-bit PDF color quantization, not expanded physical tolerances.

Actual trial: the upstream render command ran and found 187 paths. Its flattened green data path has 1201 points but contains six distinct 201-point curves. The helper omits five new start points and creates false joins across subpaths. The thin native-line splitter preserves all 1206 points; no upstream file was patched. The actual source green curves use LINE primitives, so unsupported Bezier extraction is rejected rather than approximated. Windows export initially failed printing a Unicode arrow; invoking the unchanged helper with UTF-8 mode fixed this. The initial failed log is retained under runs/tcf-calibrated-vectors-v1.

Actual corrected run: runs/tcf-calibrated-vectors-v2. Six speed-labelled curves calibrate successfully. Three tests cover disjoint starts, unsupported/nonfinite primitives, real isolated extraction and helper-pin rejection. See docs/evidence/rectangular-air/tcf-vector-extraction.json. Whole source PDFs, dense paths and calibrated curves remain in ignored runs; only hashes/diagnostics are committed.

This is research extraction, not a solver-ready manufacturer curve. CSV rounding agreement does not bound source graph rounding, drawing precision, interpolation uncertainty or actual fan performance. The extra source-grid residual is a diagnostic, not an engineering tolerance. Stable operating interval, installation applicability, viscosity, actual hardware/motor/ports and full acceptance remain pending. No electrical input is inferred from graph kW labels. Only this exact source page is supported; no claim of a general PDF chart extractor.

## Log-chart interpolation diagnostic

`tools/pdf2plot-runtime/Scripts/python scripts/check_tcf_interpolation.py --pdf runs/tcf-fan-intake-v1/tcf-m300.pdf --extraction runs/tcf-calibrated-vectors-v2 --out runs/new-tcf-interpolation` independently reopens the pinned source and compares every saved native path point before analysing interpolation. Rehashed forged points reject. Source anchors and artifact coverage are checked; no interpolation is permitted between different speed curves or outside a native segment.

A straight line in log-log coordinates maps to y/y0=(x/x0)^k with k=ln(y1/y0)/ln(x1/x0). For falling pressure, k<0 and this function is convex. A physical-coordinate linear interpolant therefore lies above it. bsa.curve_interpolation differentiates chord/y and chord-y to obtain their separate interior stationary points and evaluates endpoint/interior maxima; this is a source-representation diagnostic, not a new fan or uncertainty engine. The maximum relative and absolute errors occur at different flow values in general. Analytic reciprocal and independent dense-sampling tests check the result.

Actual runs/tcf-interpolation-v1 rechecks six native curves/1200 segments. The largest representation-relative excess is about 1.9453e-5 (0.0019453%). Four new and three extraction tests pass, including native-source tamper rejection. Evidence: docs/evidence/rectangular-air/tcf-interpolation.json. Dense source curves and segment records remain in ignored runs. Upstream pdf2plot remains unchanged and supplies the prior calibration; this thin analytic check addresses a gap not covered by its CSV export.

This number excludes CSV endpoint rounding, source axis/graph precision, manufacturer performance tolerances, operating-point sensitivity and installation effects. The independent half-flow grid residual (~0.062%) is a separate source-calibration diagnostic, not a certified uncertainty interval. No acceptance tolerance or manufacturer accuracy was invented. Solver-ready remains false pending a justified combined error/applicability basis; no real fan design was released.
