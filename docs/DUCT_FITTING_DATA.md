# Source-linked fitting table studies

`bsa.duct_fitting_data` reuses fresh saved-chain native/flow analysis and pinned
SciPy1.18.1 `RegularGridInterpolator`. It binds externally supplied coefficient
tables to actual product/path identities, native body fingerprints and owned
reference ports. It does not select a physical correlation, verify transcription,
or establish installed fitting losses from a table name.

```powershell
.venv/Scripts/python -m bsa.duct_fitting_data runs/span-project.json runs/chain-workflow/chain --basis runs/fitting-basis.json --out runs/fitting-study
```

The basis has exactly `sources` and `tables`. Each source ID maps to `document`
(relative to the basis), `sha256`, `citation` and `edition`. Source documents must
exist within the repository and match their hashes. Keep private/licensed source
files and transcriptions in ignored local runs; this repository distributes no
coefficient database. Missing or changed source files reject before native work.

Each table has these required fields:

| Field | Meaning |
|---|---|
| source_id,citation_location | Existing source ID and precise page/table location |
| classification | published correlation,manufacturer data,or synthetic |
| applicability_note | Explicit interpretation and unresolved conditions; never automatic proof |
| friction_scope | local_dynamic_only or whole_fitting_including_internal_straights,as declared by the source interpreter |
| product_guid,geometry_sha256 | Actual fitting GUID and existing duct_fitting_chain.shape_hash body fingerprint |
| inlet_port_guid,outlet_port_guid | Exact directed path from the fresh saved model |
| reference_port_guid | Owned port whose actual velocity pressure multiplies the coefficient |
| axes | One to three unique quantities and finite,strictly increasing values;angles from0 to180degrees,other quantities positive |
| coefficients | Nested grid in axis order; finite signed numbers or null |

Supported axis quantities are outlet_to_inlet_flow_ratio,
outlet_to_inlet_area_ratio,outlet_to_inlet_width_ratio,
outlet_to_inlet_height_ratio,outlet_to_inlet_velocity_ratio,inlet_aspect_ratio
and outlet_aspect_ratio,plus deflection_deg. All queries come from fresh native dimensions and exact
inherited design flow. No duplicate model,flow,density or length overrides exist.
Deflection is the angle between inward inlet and outward outlet axes from saved
world port frames,computed with atan2(cross magnitude,dot). A centred transition
has zero deflection even when its walls taper:this is not the wall/taper opening
angle. Entrance radius,Reynolds regime,developed inlet profile and installation
remain part of physical review. Body equality binds a record to geometry,not to
a physically valid method.

Supported centred four-ring transitions also expose taper_length_m,
inlet_straight_length_m,outlet_straight_length_m,total_length_m,
taper_width_angle_deg,taper_height_angle_deg,major_taper_angle_deg,
outlet_hydraulic_diameter_m,taper_length_over_outlet_hydraulic_diameter and
total_length_over_outlet_hydraulic_diameter. inlet_to_outlet_area_ratio is
available on all supported paths. Transition-only axes/conditions on tees reject.
Native inner/outer ring stations supply these quantities through
duct_transition_quantities;no declared30degree input is copied over the geometry.
Outer end planes set total/straight lengths. The deliberate inner Boolean bore
cap extension is excluded from physical length,and inner taper stations provide
the width/height opening angles. Reversing flow swaps sections and end-straight
lengths while retaining taper angles;the outlet hydraulic diameter changes with
the actual outlet. Mixed width contraction/height expansion stays a distinct
flow-change class,not a pure contraction inferred from area alone. This is a
scoped dimension reader after full native/source inspection,not another solid
kernel or a complete geometry/pressure acceptance check.

Transition quantities and saved construction classifications accompany all
transition data requests,even when no coefficient table exists. The numerical
report displays both opening angles and separate taper/end lengths. A geometric
hydraulic diameter does not establish rectangular applicability of circular pipe
correlations or replace the existing equivalent-round straight-friction method.

Optional `conditions` is a list of unique native quantity records with exactly
quantity,minimum,maximum. Bounds must be finite and ordered;ratio bounds are
positive and angle bounds stay within0–180degrees. Conditions are checked
before interpolation,with actual values retained. A failed condition gives null
coefficient and native_condition_failed recovery status. No hidden tolerance
expands these bounds. The caller must source the constraint interpretation;
passing a partial condition list cannot verify full physical applicability.

Queries outside the table return pending with no coefficient. Every corner of
the actual interpolation cell must be published/finite. Blank cells are never
zero,large sentinels or extrapolated values. Exact grid-axis hits collapse that
axis before interpolation; adjacent blank cells with no interpolation weight do
not invalidate an exact published point. No tolerance silently snaps a query.
SciPy supplies the interpolation engine; this adapter adds scope and data checks.

Coefficients multiply the saved reference port's actual density-based velocity
pressure. Negative coefficients remain signed. Changing reference ports requires
the matching coefficient conversion; the native test verifies identical scalar
contributions after this conversion. Partial contributions are grouped by exact
inlet-to-outlet path,never summed across parallel outlets. Missing data keep the
path's tabulated-plus-separate-straight sum null. Even complete numeric table
coverage leaves full pressure,critical path and acceptance null/pending: source
truth,friction station conventions,interaction/joints,boundaries and installation
remain unverified. A declared friction-scope string cannot release this gate.

## Unified workflow

Task kind `duct_fitting_data` accepts `basis` and `depends_on` on an earlier
duct_fitting_chain,plus normal id/description/requires_pass fields. It inherits
the exact producer project/IFC; IFC inventory and downstream data gates must refer
to the same producer. The executor runs fresh native analysis under analysis/,
then writes fitting-data.json and a readable index.html. The task always retains
pending design scope. `requires_pass` consumers stay unexecuted. CLI exit2 is
expected for this incomplete pressure study,not evidence of a completed design.

## Recovery data and original requirements

Every study now emits data-requests.json with one record per unique saved fitting
path,including paths without any table. Records preserve native body fingerprints,
inlet/outlet dimensions and inherited design flows,all owned reference ports and
their actual velocity pressures,the exact affected outlet paths,and original
BSA_DesignInputs source/classification fields. Saved study assumptions remain
assumptions. Do not treat a shape fingerprint or source note as a manufacturer
selection or measured installation. Requests distinguish source_data_required,
table_support_missing,native_condition_failed and physical_review_required. Even successfully interpolated
tables retain the physical-review request and their signed results.

The saved analysis carries source_context for its original upstream plan/native
workflow. The data study pins those files,checks complete requirement identities
and contents against the original execution record,and preserves every original
requirement's execution and acceptance states. This original-plan context is
distinct from the current local workflow's affected requirements. It does not
assert that every original requirement depends on these local fittings,or that
the interpreted plan captures any requirement absent from that original plan.
Independent assignment intake/delivery review remains necessary.

workflow_status adds these retained requests and original-plan context to the
fitting-data recovery root and task. It verifies the request artifact,nested
analysis,source/generator/model inputs and original plan/workflow hashes before
exposing them. A changed native model after fresh analysis blocks study output.
The queue describes missing evidence and declared dependencies; it does not
invent equipment,repair a design automatically,or clear physical acceptance.

Initial recovery execution retained eight requests:six without tables and two with blank
source support. All eight preserve their saved assumed-construction inputs.
The original34 requirement records are retained unchanged as parsed
records,including pending acceptance. The local recovery root contains the exact
eight requests and links only its declared local affected tasks. New native
request/identity tests,mutation controls and existing diagnosis regressions verify
these boundaries. See evidence/duct-fitting-recovery.json; private requirements
and source notes remain local.

## Executed evidence and sources

Native synthetic controls cover eight fitting paths,three outlet paths,signed
coefficients,owned reference-pressure conversion and independent per-path sums.
The fictional coefficient controls are not physical duct data. Source/body/port
substitution,blank support cells and bounds reject or stay pending as appropriate.
Stage controls separately exercise source pins,forbidden overrides,wrong-model
gates and blocked release; mocked stage controls are not native evidence.

The official [ASHRAE2021 supplement](https://xp20.ashrae.org/SupplementalFiles/PHVAC9/Fitting_Loss_Coefficients.pdf)
was downloaded locally and printed pages19,20,42 rendered and inspected. Fitting
5-28 on page42 is a sharp rectangular branch candidate. Actual native branch
velocity and flow ratios both equal the branch fraction in this equal-section
local geometry. Both real queries require blank table cells. The initial workflow
retained two pending source queries and six paths without supplied tables; no
coefficient or complete pressure is manufactured. Source editions,use terms and
the separate source-transcription/physical-review limits remain explicit.

Subsequent actual execution follows the page42 sharp-tee main-path reference to
the page38 main table of Fitting5-23;it does not substitute that fitting's wye
branch data. Native main areas/heights are equal and deflection is zero. The
declared0–0.000001degree frame condition is a software alignment bound,not a
published construction tolerance. Both actual main velocity ratios lie inside
published cells and yield two finite signed table contributions,independently
checked with linear segment arithmetic and the actual common-inlet velocity
pressure. Four transitions still lack tables and two branch queries still need
unpublished support. All original34 requirements and their acceptance states
remain preserved. Physical/friction/interaction/boundary acceptance and complete
pressure stay pending. The report now displays coefficients,reference velocity
pressures and signed table contributions separately. See
evidence/duct-main-loss-study.json;private table transcriptions remain local.

The next actual study extracts four saved transitions and preserves the two
main-table results and all34 upstream requirements. Unequal width/height opening
angles are retained rather than replaced with the nominal maximum angle. Native
tests cover reduction,expansion,mixed oblique geometry,reversed endpoints,bore
extension exclusion and malformed/filled body rejection. A synthetic transition
angle-table control reproduces its known scalar result;using a transition-only
quantity on a tee rejects. See evidence/duct-transition-quantities.json.

The pinned python-hvac ConvergingTransitionA9B source was additionally inspected
for its API axis ranges,without running its removed interp2d engine or computing
coefficients. Three actual taper/outlet-hydraulic-diameter ratios exceed that
candidate's declared tabular range;one is within the inspected ranges. This is
candidate API support screening,not validation of an original correlation or
proof that the one bounded case is physically applicable. Official supplemental
page21's round/rectangular shape-conversion diagrams were inspected separately
and are not substituted for these rectangular-to-rectangular bodies. All four
transition coefficients remain absent pending suitable source/method evidence.

Additional inspection pinned MIT
[TomLXXVI/python-hvac](https://github.com/TomLXXVI/python-hvac/tree/94247560a667905bfbf67e45a58965a58254fce8)
at94247560a667905bfbf67e45a58965a58254fce8. Its rectangular tee implementation
also has sparse data and depends on scipy.interpolate.interp2d. The installed
SciPy1.18.1 API explicitly rejects that removed interface. This is source/API
inspection,not a verified full-package integration. No candidate code/tables are
copied or installed. Existing SciPy is reused instead of implementing another
interpolation engine. Public aggregate evidence is in evidence/duct-fitting-data.json.
