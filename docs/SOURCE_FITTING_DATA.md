# Source-linked fitting tables on the represented network

`bsa.source_fitting_data` reuses the existing bounded fitting-table engine after
the complete represented network's native/source/flow/path verification.

```
python -m bsa.source_fitting_data run NATIVE_ANALYSIS_RUN BASIS --out FRESH_RUN
python -m bsa.source_fitting_data verify FRESH_RUN
```

Host BSA_PROJECT_ROOT explicitly selects external coursework. Basis and source
documents must remain in the repository or that selected workspace. Source
documents cannot select a workspace. Outputs are fresh and outside immutable
inputs. The original analysis, model and requirements are preserved. Exit 2
retains incomplete engineering scope even if source/numerical integrity passes.

## Reuse and native quantities

The adapter reuses duct_fitting_data.prepare/calculate, its sparse bounded
SciPy RegularGridInterpolator logic, and duct_transition_quantities. The shared
basis parser now accepts the explicit host-selected project as well as the
repository; unselected/protected workspaces remain rejected. No interpolation
engine or coefficient database is rebuilt or redistributed. See
[existing schema and limitations](DUCT_FITTING_DATA.md).

Native material-cap dimensions are independently checked by the producer. Where
the actual saved junction inner prism or centred transition rings provide
canonical dimensions, those literal values are checked against the native cap
and used for table queries. This prevents floating world-coordinate subtraction
from falsely violating an exactly equal-area source condition. No ratio is
rounded/snapped, no source condition is widened, and mismatching native caps
reject. Actual source design flow and matching reference velocity pressure are
retained. All 31 source transitions also retain their fresh native flow-change,
separate taper angles and physical lengths in requests, even without tables.

## Explicit applicability and missing data

Every table targets an actual native body fingerprint, directed inlet/outlet
path and owned reference port. Sparse cells remain null and out-of-range
queries do not clamp or extrapolate. Signed coefficients and contributions
retain their sign. Each original fitting path gets a data request and affected
outlet paths, including paths with no table. Full original requirement identity
and complete-pressure/critical-path pending states remain.

Only the appropriate main-inlet, sharp three-port tee construction is screened
for the current source study. Crosses, the compound body, elbows, transitions
and a branch-inlet tee are not silently assigned its coefficients. Proximity to
adjacent transitions, friction convention, source transcription, physical
fabrication and complete applicability remain review-required even when source
quantity conditions and interpolation pass. Local dynamic contributions are not
whole-fitting pressure unless that convention is independently established.

## Source review and private material

The existing official 2021 ASHRAE Principles of HVAC supplemental source was
reopened locally. Printed pages 38 and 42 were rendered and inspected, including
the tee main-table cross-reference, geometric conditions, footnote and use terms.
The original source and transcriptions are preserved. New project-local copies
and bound queries stay private/ignored; no publisher table/PDF/image is included
in public snapshots. Numerical controls use fictional data only.

The source study screens 13 main-inlet core tees and submits 26 source-bound
queries. One other core's inlet is its branch and is excluded from this source
interpretation. Thirteen main queries obtain bounded conditional values; the
13 branch queries require unpublished support cells and stay unknown. Fifty
other fitting flow paths have no supplied table. Thus all 76 original paths
remain represented, with 63 lacking a numerical table result and all physical
acceptance still pending. The original source analysis remains unchanged.

Eight native/source/interpolation/workflow tests pass. Separate actual linear
segment arithmetic and native common-inlet velocity-pressure multiplication
independently agree with all 13 finite results. The standalone verify CLI also
recomputes complete source/native analysis, source hashes, canonical geometry,
sparse-table outcomes and every pressure/data-request path. Integrity passes;
source/friction/physical/interaction acceptance and full pressure remain pending.
See [safe aggregate evidence](evidence/source-fitting-data.json).
