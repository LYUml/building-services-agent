# ADPI basis before criterion evaluation

Course-specific category review now has separate evidence support. An inspected
classroom example explicitly maps its prescribed diffuser family to the selected
historical classroom row;the [manufacturer's introduction](https://www.krueger-hvac.com/file/3117/1400_1400FR_51400_M1400_M51400_Introduction.pdf) independently identifies
the face/cone/neck family. That supports this course-specific selection basis.
Other manufacturer pattern taxonomies and newer handbook categories remain
separate contexts. Actual room load,L and installation stay unresolved;this does
not establish a measured/predicted ADPI or unrestricted physical correspondence.

The current terminal tool calculates bounded catalogue throw and T/L only. Its
ADPI_verified flag remains false. Numerical interpolation does not select an
applicable comfort criterion.

Review exact edition, product-to-category correspondence, cooling/heating mode,
room sensible-load meaning and range, ceiling/installation conditions, and the
geometric interpretation of L before evaluating an acceptance range. Distinguish
manufacturer chart conditions from generic handbook conditions and coursework
instructions; record conflicts rather than silently combining them. A coil allowance
multiplied by SHF does not establish the room sensible load.

Official source comparison on 2026-11-10 found different classification/load schemes
in [ASHRAE 2015 Tables 3/4](https://handbook.ashrae.org/Handbooks/A15/SI/a15_ch57/a15_ch57_si.aspx)
and [ASHRAE 2023 Tables 5/6A](https://handbook.ashrae.org/Handbooks/A23/SI/A23_Ch58/a23_ch58_si.aspx).
The latter distinguishes louvered blade details. Do not map a manufacturer's older
pattern terminology to a newer category without product evidence.

The actual private source snapshots and hashes are retained in the ADPI edition
review. No table has been automatically chosen for the coursework. Original course
method, actual room load and product/geometry correspondence remain unresolved.
Keep the reported allocation-cell lengths labelled diagnostic proxies; do not alter
geometry or invent loads merely to place ratios inside a preferred interval.

## Concrete applicability checks

Rechecked the official 2023 SI chapter on 2026-11-10. Table 5 ties horizontal-throw
ceiling diffuser L to walls, outlet midplanes or intersecting jets. Allocation-cell
ray distances require physical interpretation; the vertical addition listed for
light-troffer diffusers must not silently be applied to another category.

Table 6A cooling entries use 25 and 50 W/m2, and its source note limits ceiling
height to 3.7 m. These are table applicability conditions, not building regulations
or permission to extrapolate. Establish the actual room sensible load and ceiling
height first. If a course uses a different edition or method, retain that source
and resolve the difference explicitly. Never replace a trial load with a convenient
tabulated value to obtain a passing result. Louvered blade-lip classification also
needs product evidence before selecting the applicable row.

## Research paper versus handbook

Liu, Clark and Novoselac, *Air diffusion performance index (ADPI) of overhead-air-
distribution at low cooling loads*, Energy and Buildings 134 (2017), 271–284,
[DOI 10.1016/j.enbuild.2016.10.055](https://doi.org/10.1016/j.enbuild.2016.10.055),
reports experiments at 25/50 W/m2. Its appendix and the 2023 handbook contain
different louvered selection intervals. Keep the selected source, edition and
conditions together; do not use an interval from one with a category or conditions
from another without resolving the correspondence. Manufacturer participation in
the study is not proof that a specific catalogue model/configuration was tested.
A paper found in a prior project folder is not automatically a course-prescribed
method. The local paper was reviewed without redistributing its copyrighted PDF.

## Scoped interval screening

`bsa.adpi_screen.screen` reuses terminal_throw output without changing the fluids
lookup engine. Supply the exact criterion source, room-load/ratio intervals and
Boolean-or-unknown facts for room load, product category, characteristic lengths,
installation and edition selection. Unknowns retain pending; verified loads outside
the source range or rejected facts mark inapplicable. Only eligible inputs receive
per-case interval results, with both maximum/minimum cases retained. The result
always keeps ADPI_verified and design_accepted false: a ratio interval is not a
measured comfort index or proof that declarations are true.

Five boundary/missing/failed-case controls pass. Actual private lecture-backed
640-case screening remains pending: trial170.1 W/m2 is outside the displayed range
and actual room load is not verified. Product/length/installation evidence remains
unknown. No ADPI criterion has been relaxed to clear the study. This is currently
a Python API, not a registered workflow or automatic regulatory check.

## Verified workflow review command

Run `python -m bsa.adpi_review <workflow-directory> <settings.json> --out
<new-review.json>`. Settings contain exactly criterion, room_load_W_m2, facts,
source (a path relative to settings) and source_sha256. Criterion and facts use the
API contract above. The command verifies the run, selects exactly one passing
terminal_throw task, inherits its result, checks the original criterion document
and records/rechecks all input hashes. Store output outside the immutable run.
CLI exit 2 retains outstanding acceptance even for eligible interval screening.

Actual private execution inherits 640 cases from the new Canvas-source-backed run
and retains pending applicability. A changed criterion-document hash rejects before
output; the five numerical/applicability controls pass. This post-run command is
not a registered workflow task;the HVAC package now invokes it as an optional
review stage.

## Per-fact review evidence

Settings may additionally contain `fact_evidence`,a mapping from any supported
applicability fact name to1–20 document records. Each record contains exactly
`source` (relative to settings),`sha256`,`locator` and `note`. Documents must exist,
match their hashes and remain unchanged. Records are retained in the numerical
result. Evidence does not promote a fact;the reviewer must explicitly declare
true,false or unknown with a justified interpretation. A true course-specific
mapping must not be silently reused for another criterion,product or edition.

The same settings reader is used by the standalone review,HVAC package and saved
project configuration. Supplemental documents enter pre/post execution pins and
the protected source set. Changed evidence during screening or a later package
stage rejects;changed project-config evidence prevents execution. Legacy settings
without this optional map retain their existing behavior.

Eighteen targeted ADPI/project/package controls pass. Actual new seven-stage
execution supports the course-specific category while room-load,length and
installation facts stay unknown. All640 cases remain not_evaluated under pending
applicability and
ADPI_verified=false;trial load and source bounds are unchanged. Private source
documents and interpretations remain local.

## Geometry evidence before choosing L

A clipped nearest-centre allocation boundary can be a bisector toward a diagonally
offset terminal. That does not establish opposing jets along the principal airflow
direction. A diagnostic comparison should distinguish interpreted polygon boundaries,
aligned outlet midplanes and off-axis jet interactions. Polygon holes may represent
columns rather than full-height boundary walls; their semantics need separate review.
Do not automatically replace all L values with either wall-ray distance or Voronoi
cell distance. Product discharge pattern and actual installation remain relevant.

Actual private 320-direction comparison using existing Shapely boundary intersections
finds eight differing proxy directions with no aligned opposing outlet. These are
retained as explicit geometric review targets; the other 312 numeric agreements
do not establish physical jet applicability. No lookup lengths or acceptance states
were changed by this diagnostic.

Alignment trials must reallocate areas/flows and rerun all affected directions,
not just the previously ambiguous direction. A private eight-terminal alignment
trial preserved panel containment but shortened a boundary distance and produced
two maximum-flow ratio diagnostics outside the classroom example interval. It was
retained unselected; no CAD or baseline input was replaced. This is a geometric
tradeoff investigation, not proof of applicable ADPI compliance or optimal layout.
