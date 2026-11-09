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
