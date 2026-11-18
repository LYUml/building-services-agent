# Physical-time OpenFOAM history diagnostics

`bsa.openfoam_transient` reads one complete fixed-step native `surfaceFieldValue`
segment with Decimal seconds. It remains separate from `openfoam_history`'s
steady integer-step convergence gate. Install the pinned existing NumPy dependency
with the `cfd-history` extra. No new CFD or quadrature engine is implemented.

For a saved steady segment, use `bsa openfoam-history-review --manifest <file>
--output <new-file>` or MCP `bsa_review_openfoam_history` with `manifest`,
`output` and optional `window`. Both use host-selected project-relative paths.
The CLI retains the review and exits 2 when its numerical window fails.
Use `bsa openfoam-history-verify --manifest <file> --report <saved-file>` or
MCP `bsa_verify_openfoam_history` with the original `window` to reconstruct
the saved review. Integrity can pass while the numerical result fails.
See [the steady manifest contract](OPENFOAM_IMPORT_PRECISION.md#project-command).
Both interfaces replayed the retained 51–250 step segment from byte-identical
local input copies. All 10 history files, four basis files and numerical
results matched the old receipt. Flow and mass passed while pressure stability
failed. The interfaces produced identical new reports. No solver rerun or
engineering pressure acceptance was inferred.
Two additional saved steady windows, steps 851–1050 in the late run and
221–420 in the refined first-order run, reproduced their historical numerical
passes through both interfaces. Window stability is scoped to each saved run;
mesh, domain and experimental comparisons require separate evidence.

For a source-bound transient pressure-difference review, use
`bsa openfoam-pressure-review --manifest <file> --output <new-file>` or MCP
`bsa_review_openfoam_pressure` with the same two project-relative fields. Install
the `cfd-history` extra. A manifest identifies the two synchronous pressure
histories, named windows and the associated observer and source basis files.

```json
{
  "schema": "bsa.openfoam-pressure-history.v1",
  "units": "Pa",
  "delta_t_s": "0.00025",
  "inlet": {"file": "inlet.dat", "column": "average(Pt)"},
  "outlet": {"file": "outlet.dat", "column": "average(Ptf)"},
  "windows": {"comparison": ["0.20", "0.25"]},
  "basis_files": {"observers": "functions", "case": "controlDict"}
}
```

The output pins both histories and the basis files. Each window reports signed
inlet-minus-outlet pressure statistics and leaves stationarity and adoption open.
Both interfaces reproduced the recorded statistics for four outlet paths over
the 0.15–0.20 s and 0.20–0.25 s windows using the five retained native files.

Use `bsa openfoam-pressure-verify --manifest <file> --report <saved-file>` or
MCP `bsa_verify_openfoam_pressure` to reconstruct and compare a saved review
without writing files. The report binds the reviewing method and NumPy version;
use the original source snapshot to replay historical method hashes.

```python
from bsa.openfoam_transient import read_samples, difference, window_statistics
inlet = read_samples(inlet_text, "average(Pt)", delta_t_s="0.00025")
outlet = read_samples(outlet_text, "average(Pt)", delta_t_s="0.00025")
result = window_statistics(difference(inlet, outlet), "0.20", "0.25")
```

The caller must bind pressure units, density, weighting, field definitions and the
selected restart segment. Supported columns are sum(phi), orientedSum(phi),
average(Pt) and average(Ptf). The parser rejects partial trailing writes,
unexpected headers, missing/overlapping times and nonfinite values. Do not feed a
file still being written to this complete-segment reader. Restart merging and
variable time steps are outside this API's current scope.

Windows require exact sampled endpoints. Means and RMS deviations use upstream
NumPy2.5.4 trapezoidal quadrature; the latter is quadrature of squared nodal
deviations, not an exact continuous variance or uncertainty estimate. Difference
requires exact simultaneous time labels. There is no stationarity threshold,
pressure acceptance or conversion to steady iteration labels.

Actual completed BSE3227 replay reads five981-row native histories and matches
24previously recorded scalar statistics across four paths/two windows. Four new
focused tests and six existing steady-history tests pass. This verifies scoped
history handling, not the CFD model or design pressure. See
[executed receipt](evidence/physical-time-history.json).
