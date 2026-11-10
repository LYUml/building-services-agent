# ADPI basis before criterion evaluation

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
not yet a registered workflow task or an automatic report/package stage.
