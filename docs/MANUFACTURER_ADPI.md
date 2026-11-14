# Separate manufacturer ADPI comparison

The user selected a separate manufacturer-based comparison while preserving the
coursework design. This study does not replace the historical classroom criterion,
change its load range or approve the existing terminal layout.

Actual source extraction uses the inspected 2012 Krueger engineering guide,
printed a1-11, Type 3 circular ceiling pattern. Its PDF SHA256 is
`f98aa9ded59150e157c83d5c5114faaa1a24c185928709ffe5d60c9b2f607988`.
`scripts/extract_krueger_adpi.py` reuses existing native LINE splitting and the
unmodified MIT pdf2plot helper at `99a8ee1d1e24a0859fea1cd06011280734ab82cb`.
PyMuPDF 1.26.7 stays isolated under its existing AGPL/commercial runtime terms.
Native grid checks and independent linear calibration reconcile all 365 points.
Five source fragments remain separate, including the two 40-load fragments;
there is no invented connector, load interpolation or curve extrapolation.

The original performance PDF, printed B1-12, SHA256
`073c639219b28068a0c8190a926d493e42a12c0918db464ee8439c55a3994aef`, supplies
54 rows: nine rows for each 6/8/10/12/14/15 inch neck on a 600×600 mm panel,
without damper. The actual rendered page was inspected. Extraction of the 8-inch
table exactly reconciles all nine earlier reviewed rows. Static/total pressures
stay distinct and a dash in NC remains qualified null, not zero.

```powershell
# Explicit host BSA_PROJECT_ROOT; isolated runtime is a host argument.
tools/pdf2plot-runtime/Scripts/python scripts/extract_krueger_adpi.py SOURCE_GUIDE --out NEW_CURVES
python -m bsa.manufacturer_adpi run PLAN WORKFLOW NEW_CURVES PERFORMANCE_PDF POLICY --out NEW_COMPARISON --pdf2plot-python HOST_PDF_PYTHON
python -m bsa.manufacturer_adpi verify NEW_COMPARISON
```

Policy contains `grids`, `split_y_m`, `basis`, `classification`, `curve_document`.
It declares finite two-zone grids (main office and upper bay) as design choices.
At most twenty shapes and 160 terminals per shape are supported. Zero-area boundary
tails are excluded from grid-region bounds; no empty cell is silently dropped.
The original reviewed source polygon and supplied thermal-load area stay distinct.
Shapely representative points and existing nearest-centre service allocation
preserve source total load, airflow and 40% turndown. Directional lengths stop at
the actual polygon ray boundary or exactly aligned opposing midplane. They remain
diagnostic geometric proxies, not verified physical walls/jet lengths.

The preliminary maximum sensible estimate is 170.1 W/m². A separate constant-ΔT
part-load scenario uses 40% sensible load, 68.04 W/m²; actual part-load heat gains
are unknown. Using 1 IT Btu = 1055.05585262 J and 1 ft = 0.3048 m, these conditions
fall between the published 40/60 and 20/40 Btuh/ft² series respectively. The study
does **not** interpolate ADPI between loads. Its explicit diagnostic requires both
bracketing source curves to meet 80 with a full source-stroke margin in both axes.
This paired test is not a manufacturer prediction at the actual load; monotonic
load interpolation and source testing uncertainty have not been established.
Performance interpolation uses the existing fluids-backed terminal tool, without
clamping or extending published airflow bounds.

Actual execution checks the current 80-point layout plus seven grids with
12/22/36/54/80/106/136 terminals, each against six neck tables: 48 comparisons
and 31,832 directional/load curve cases. No complete sampled pair passes this
conditional diagnostic. Rejections retain original-table airflow exclusions,
source-curve domain/fragment exclusions and represented threshold shortfalls.
Larger necks can leave minimum flow below published data. These are heterogeneous
failure records, not unique failed diffusers. The finite negative result is not
a proof that all physical designs are infeasible.

No candidate is selected and no new native layout is issued from rejected trials.
The course plan, source allocation, original DWG/report and recent connection
layout remain byte-preserved. Five focused controls pass. Independent verification
reopens the exact source PDF through the pinned helper/runtime, reconstructs the
grid allocation, curve comparisons and CSV, and rejects mismatched saved output.
This replay does not establish actual room-load, ceiling, installation, acoustics
or ADPI acceptance. Detailed source/point/case records remain in the selected
private project; only scoped aggregates are public. See
[comparison evidence](evidence/manufacturer-adpi-comparison.json).

The next upstream route is the official [K-Select program](https://www.krueger-hvac.com/public/software/k-select),
which describes room-area/ΔT/characteristic-length ADPI selection. Version 13.3.54
was downloaded from the linked official endpoint. Actual Authenticode status is
Valid, observed signer Revalize, Inc.; size 195,687,088 bytes and SHA256
`386b3a71d41731c3d2c93dd17de50c0cc847ccf1620d6f1b2ee88f362350d8d4`.
Static 7-Zip/PE inspection found an embedded Wise installer and did not expose a
ready command-line selection engine. No installer/payload/selection has run; its
web feature list is not executed integration evidence. See
[static review](evidence/k-select-static-review.json). A native application trial
is the next step, subject to the Windows computer-use confirmation rule.
