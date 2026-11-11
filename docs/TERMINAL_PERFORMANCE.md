# Source-bound diffuser operating points

This adapter adds catalogue static/total pressures to an existing passing
terminal_throw workflow. It reuses the pinned fluids1.3.1 interpolation routine
and existing delivery.context/workflow verification;it does not replace an
acoustic or air-network solver.

```powershell
.venv/Scripts/python -m bsa.terminal_performance runs/project/plan.json runs/project/workflow lookup runs/project/performance/settings.json --out runs/project/terminal-operating-points
```

Settings contains exactly source,source_sha256,catalogue,catalogue_sha256 and
conditions. Both source paths are relative to the settings directory and remain
inside it. The conditions string records the actual product,installation/test
basis and relevant acoustic conditions. Catalogue source_sha256 must match the
original document hash in the existing throw catalogue. Both tables have exactly
the same row coverage,flows and throw values. Any original pressure/NC columns
and product model/locator/damper fields must also agree.

Each performance row provides positive flow_L_s and T025_m,nonnegative finite
static_pressure_Pa and total_pressure_Pa,NC (number or null) and nonempty
NC_qualifier. Total pressure cannot be less than static pressure. Null NC remains
qualified by its source;it is never converted to zero. Source bytes and matching
metadata do not prove correct transcription or product applicability:inspect the
original rendered table and its notes.

Maximum/minimum flows and turndown come from the exact original lookup and its
allocation producer. All directional throw results are replayed before pressure
calculation. There are no replacement flow inputs. Pressure uses a declared
piecewise-linear approximation within the original catalogue range;no endpoint
clamping or extrapolation. The adapter retains outside-range results as null.
Static and total columns remain distinct and must not be added together.

NC is only copied at an exact catalogue flow. Between rows,the output retains
the adjacent published flow/NC/qualifier records. Those are references,not
interpolated values,guaranteed bounds or an acoustic acceptance check. Room
absorption,other sound sources,installation effects and room criteria need
independent analysis. Do not sum NC values across terminals.

Outputs are performance.json and index.html in a new directory outside the
immutable workflow. Source/settings/table/method hashes are rechecked before
writing,as is the workflow. The source plan and earlier artifacts remain unchanged.
This postprocessor is available as an optional hvac_package stage using
`--terminal-performance <settings.json>`. It requires exactly one declared
terminal_throw task and inherits the newly executed workflow. The same option
on hvac_project create persists the selection and its complete settings/document/
table/method inventory. Old configurations that omit it remain supported;omission
does not mean a performance check passed. The package links the performance HTML
and retains stage errors;later source changes prevent the package manifest or
project receipt. It remains separate from the existing numerical report PDF and
is not yet a complete fan-budget consumer. Parallel terminal pressures must not be summed;VAV,flex,
rigid-duct,fitting,boundary and balancing data remain necessary for full fan duty.

Seven new tests and14 existing throw/allocation tests pass. Actual archival
Krueger B1-12 600x600mm-panel,8-inch-neck,no-damper table was visually inspected,
including all9 Pt/Ps rows and the10dB room-absorption NC note. All80 actual
terminals produce160 operating points. Independent decimal interpolation checks
both pressure columns for all160 cases. Actual installation/acoustic acceptance,
ADPI and complete fan pressure remain false. The manufacturer PDF and table stay
in ignored private runs;they are not redistributed. Attribution remains Krueger.
See [executed evidence](evidence/terminal-performance.json).
