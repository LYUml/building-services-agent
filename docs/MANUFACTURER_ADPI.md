Alternative-family source check: official2024Model1240/51240 dimension and performance sheets support modular1/2/3/4core jet data and shown1/2/3/4way arrangements.90published metric flow rows/360throw triplets independently match native PDF coordinates in1530scalar checks. Pattern count is not discharge-direction count; pressure/NC from1core table are not transferred to other arrangements. At unchanged80terminal demands,57terminals have no neck whose published table covers both flows; only9of35wall terminals have operating-flow coverage. This is missing published data, not equipment failure. Its own4way ADPI spacing charts are20Btuh/ft2, not current~53.92; no1400curve transfer or product substitution. Read-only existingKSelect repos remain1400-only at3eecd371. See [source check](evidence/modular-core-source-check.json).

Actual spatial follow-up reuses pinned SciPy differential_evolution with fresh source-polygon service-area/flow allocation for each candidate. An initial eight-parameter grid remained57failed terminals; a source-layout nine-parameter refinement reduced the hypothetical comparison from39to35failed terminals. Final exact source screen still has145failed curve tests/104direction-operating failures. All80points remain inside source boundary; service polygons cover without overlap, original thermal balance and40percent flow turndown preserved. Finite35iteration budget is exhausted, not optimizer convergence/global infeasibility. No failed candidate is adopted or drawn. The original lecture explicitly uses horizontal half spacing; no downward travel is adopted for coursework. See [spatial evidence](evidence/adpi-spatial-layout.json).

Wall/neck diagnosis: all35terminals with wall-limited proxy rays fail the unchanged paired diagnostic for every one of six neck tables at their existing positions/flows (210neck-terminal cases). However, all80terminals retain an individually compatible target effective L with the original8inch neck: each target midpoint was checked against the actual source screen at both operating conditions and all four load-curve tests. These independent scalar targets are not a spatial layout. This identifies layout/length applicability, rather than neck-only selection, as the next design task. See [diagnosis](evidence/adpi-wall-neck-diagnosis.json).

Length-basis follow-up: source a1-10 prose includes downward mixed-jet travel, while its adjacent table uses abbreviated wording. The earlier planar-length diagnostic and square-grid density bound do not cover that interpretation. A separate actual80terminal/8inch sensitivity sweep preserves walls, flow, loads, source curves and margins:462failed direction/case combinations at zero added distance; best sampled70 at hypothetical2.32m, including55unchanged wall-limited failures. No full pass among301samples; no actual height or length rule adopted. See [review](evidence/adpi-length-sensitivity.json).

Current source audit: manufacturer guide explicitly maps1400toType3; independent native PDF-coordinate extraction of all54metric flow/T025 rows matches the current parser. No type/throw-column error was found. The170.1vs160W/m2 coursework applicability conflict remains; final basis choice requires clarification. The12page coursework review report now binds the completed DWG recheck. See [audit](evidence/course-adpi-source-audit.json).

# Separate manufacturer ADPI comparison

Latest native status: all current coursework demands now have 49 actual GRD10.0.2 native reports, 2,401 independent PDF scalar checks and 640 native-reported classroom ratio checks. Original load-domain applicability and ADPI remain pending. The separate user-owned MCP toolkit is reused unchanged. Earlier blocked-launch records below remain historical. See CURRENT_COURSE_KSELECT.md.

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
Additional mixed-neck reconstruction finds zero terminals in each sampled layout
that pass all declared conditions with any of the six necks, so mixing necks does
not repair these particular layouts.

An independent planar-length necessary-bound study (L=half horizontal spacing, excluding downward mixed-jet travel) considers only a regular square interior
grid, spacing=2L and area=4L². Using the greatest represented paired-curve ratio
1.186815 and both catalogue operating-flow bounds, it maximizes q/(4L²) over each
original piecewise-linear throw segment. Endpoints, published knots and interior
stationary points are considered; no airflow extrapolation occurs. The resulting
optimistic bounds are 2.722–2.750 L/s/m², or about 39.4–39.8 W/m² at the inherited
12 K, air density and specific heat. Lower ratio and minimum-load curve checks
are omitted, so this necessary bound is not a sufficient design. It is not a
bound for arbitrary irregular layouts or actual room loads. It highlights the
conflict with the preliminary 170.1 W/m² basis under this regular-grid diagnostic.
An independent 60,044-point scan including original table knots reconciles every
analytic maximum. The initial uniform-only scan missed a knot maximum; source
values and comparison tolerances were retained, with knots added to the scan.

The course plan, source allocation, original DWG/report and recent connection
layout remain byte-preserved. Seven focused controls pass. Independent verification
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

## Authorized native launch outcome

The user subsequently authorized installation and trial. The exact installer
hash and valid Authenticode signature were rechecked. Actual Windows
`sky.launch_app` did not expose a targetable installer window; the subsequent
window/process inventory found no K-Select installer. Windows Code Integrity
events 3033/3077 identify the installer attempting to load its extracted temporary
component and rejecting that component under the enterprise signing policy.
The outer valid signature therefore did not establish launchability of its
embedded components. The original XML event records remain private and hashed.

No installation or manufacturer selection executed. This is an actual runtime
failure, not a withdrawn permission request or a successful integration. No
policy was changed, blocked module retried through another loader, or user app
restarted. Native selection now needs a publisher/IT-supported signed package or
an approved execution environment. The checked official software page exposes
the same setup endpoint; the scoped official-site search did not locate a
separate MSI/portable selection engine. That search is not proof none exists.
See [actual runtime record](evidence/k-select-runtime-block.json).


Further user-requested retry identifies the policy specifically as Windows Smart
App Control: event PolicyName=VerifiedAndReputableDesktop and read-only registry
state=1. Signature-information events for the extracted module report zero
signatures and PublisherName=Unknown. This does not establish enterprise device
management; earlier "enterprise signing level" wording came from the generic
Windows event message. The actual outer package remains validly signed.
Microsoft's signature-testing guidance identifies this enforcement policy and
requires testing all installer binaries. A read-only CiTool policy inventory
returned access denied; no elevation or policy modification was attempted.
No distinct supported public installer was located. Common local Sandbox/VM
executable paths were absent, which is not a complete virtualization inventory.
A local sanitized support note is ready for the user; no message was sent.


PLQR follow-up uses actual manufacturer square-discharge wording rather than face
outline: PLQ square plaque is radial360, while PLQR round plaque expands as a
square pattern. Own24x24/no-damper54metric rows pass378independent coordinate-based
scalar checks. The unchanged actual80terminal flow pairs can be covered by77eight-
inch and3ten-inch necks (flow-domain choice only). Own640planar ratios range
0.612-2.222; no coursework1-3.4 interval is transferred to the alternative product.

The same pinned pdf2plot engine now calibrates Type9's324native points in six
preserved fragments. Conditional product/pattern mapping and both adjacent load
curve diagnostic across every flow-eligible neck produce2528curve checks. Best
per-terminal choices still leave320failed direction/operating cases and626failed
curve checks; zero terminals fully pass this diagnostic at current positions.
This rejects this bounded unchanged-layout candidate, not all PLQR layouts or
actual-load comfort. No geometry/product/ADPI adoption. Explicit user decision now
defers course acceptance until an applicable ADPI basis is established.
See [source-bound receipt](evidence/plqr-adpi-diagnostic.json).
