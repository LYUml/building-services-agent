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

Each table has exactly:

| Field | Meaning |
|---|---|
| source_id,citation_location | Existing source ID and precise page/table location |
| classification | published correlation,manufacturer data,or synthetic |
| applicability_note | Explicit interpretation and unresolved conditions; never automatic proof |
| friction_scope | local_dynamic_only or whole_fitting_including_internal_straights,as declared by the source interpreter |
| product_guid,geometry_sha256 | Actual fitting GUID and existing duct_fitting_chain.shape_hash body fingerprint |
| inlet_port_guid,outlet_port_guid | Exact directed path from the fresh saved model |
| reference_port_guid | Owned port whose actual velocity pressure multiplies the coefficient |
| axes | One to three unique quantities and finite,positive,strictly increasing values |
| coefficients | Nested grid in axis order; finite signed numbers or null |

Supported axis quantities are outlet_to_inlet_flow_ratio,
outlet_to_inlet_area_ratio,outlet_to_inlet_width_ratio,
outlet_to_inlet_height_ratio,outlet_to_inlet_velocity_ratio,inlet_aspect_ratio
and outlet_aspect_ratio. All queries come from fresh native dimensions and exact
inherited design flow. No duplicate model,flow,density or length overrides exist.
Other conditions such as angle,entrance radius,Reynolds regime,developed inlet
profile and installation remain part of physical review; these axes do not infer
them. Body equality binds a record to geometry,not to a physically valid method.

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
local geometry. Both real queries require blank table cells. The actual workflow
retains two pending source queries and six paths without supplied tables; no
coefficient or complete pressure is manufactured. Source editions,use terms and
the separate source-transcription/physical-review limits remain explicit.

Additional inspection pinned MIT
[TomLXXVI/python-hvac](https://github.com/TomLXXVI/python-hvac/tree/94247560a667905bfbf67e45a58965a58254fce8)
at94247560a667905bfbf67e45a58965a58254fce8. Its rectangular tee implementation
also has sparse data and depends on scipy.interpolate.interp2d. The installed
SciPy1.18.1 API explicitly rejects that removed interface. This is source/API
inspection,not a verified full-package integration. No candidate code/tables are
copied or installed. Existing SciPy is reused instead of implementing another
interpolation engine. Public aggregate evidence is in evidence/duct-fitting-data.json.
