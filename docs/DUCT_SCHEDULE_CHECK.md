# Independent saved-schedule equation checks

```powershell
.venv/Scripts/python -m bsa.duct_schedule_check runs/project/plan.json runs/project-package/workflow native-sheet --out runs/duct-sizing-equation-review
```

Use the exact passing `duct_sheet_native` task ID. The adapter reuses delivery
context validation and saved-native junction/source correspondence to inherit the
same original schedule,source project and flow identities. Replacement geometry,
air properties,criteria or candidate lists are not CLI inputs. Output is a new
repository directory outside the immutable source workflow.

The review independently reconstructs equivalent diameter,actual rectangular
velocity,equivalent-round velocity,Reynolds number,Darcy pressure gradient and
aspect ratio with Python math. It checks the stored Darcy friction factor in the
implicit Colebrook equation;it does not implement another friction solver or call
the producer's calculation function to obtain its expected answers.

```
r = 1/sqrt(f) + 2 log10(epsilon/(3.7 De) + 2.51/(Re sqrt(f)))
```

Numerical relative tolerance is1e-10 and the absolute residual bound is1e-10.
These are software reconciliation checks. They are not chart-reading tolerances,
manufacturer guarantees or engineering acceptance bands. Positive finite inputs
and the producer's supported turbulent domain are required.

For candidate schedules,every original candidate dimension and identity must
occur exactly once. Every saved candidate calculation and failure classification
is checked,and eligible candidates are independently ranked by the original
area/perimeter/lexical-ID policy. Selected dimensions and calculations must match
the preferred eligible candidate. Prescribed dimensions are checked directly;
candidate-ranking status is null when no candidate search was supplied. Failed
or empty schedules reject. Rejected high-velocity trial candidates do not become
physically applicable because their algebra is consistent.

`review.json` retains all original requirement records,source/native/method pins,
selected-section quantities,checked candidate count and maximum residual across
selected and candidate calculations. `index.html` distinguishes actual duct
velocity from the equivalent-round chart velocity. Existing sources and saved
artifacts are checked again before output. Review status remains review_required;
chart reading,physical applicability and design acceptance remain false.

## Source method and graphical limits

ASHRAE's official online [Duct Design chapter](https://handbook.ashrae.org/handbooks/F17/SI/f17_ch21/f17_ch21_si.aspx)
describes the friction chart as a representation of Darcy/Colebrook calculations
and explains equal-flow/equal-friction rectangular conversion. This corroborates
the equation family;the webpage snapshot does not authenticate a different
printed chart edition or a project's operating properties. Retain each actual
source's edition,density,roughness and conditions separately.

An inspected classroom chart is a raster image with no native vector curves.
The pinned pdf2plot trial supports native vector calibration and cannot supply
independent curve readings from this page. No source curves or numerical chart
values were extracted or fabricated. This review explicitly preserves
scanned_chart_readings_verified=false. Physical method/source applicability,
chart transcription/reading,manufacturing dimensions,acoustics,installation and
complete duct/assignment acceptance remain separate.

## Executed evidence

Thirteen targeted schedule/equation/source-path tests pass. They include a
coherently changed factor and pressure that still fail the independent residual,
unselected candidate tampering,missing/substituted candidates,forged eligibility
and ranking,source limits/flow changes,and actual/equivalent velocity separation.

Actual private execution binds the passing saved-native workflow and checks47
sections and16,779 source candidates. Maximum absolute residual is about3.38e-14.
Every original requirement is retained,and numerical success accepts no original
physical design task. Source materials and dense results stay outside Git. See
evidence/duct-schedule-equations.json.
