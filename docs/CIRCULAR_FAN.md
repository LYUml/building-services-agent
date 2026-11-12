# Source-bound circular fan operating point

`circular_fan_operating_point` inherits the exact passing `route_pressure` result.
It reuses the existing bounded bisection/interpolation in `pump._solve`, the
air-only curve validator/operating-network builder from `rectangular_fan`, and
the pinned circular network/fluids calculator. No fan solver or dependency is
added. Source curves retain their original point order and declared bracket;
there is no extrapolation or static-to-total pressure conversion.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/route-search/port-fan-plan.json --out runs/new-circular-fan-workflow
```

The public synthetic example preserves all original requirements, adding one
free-flow fan task and a fan gate on the route-only DXF. Original prescribed
airflow is the minimum design duty. Curve intersection must also satisfy velocity,
terminal pressure, residual and flow-bracket checks. A converged weak curve can
produce an operating-network diagnostic while remaining failed and blocking
drawing. An unbracketed/exhausted solve has no operating network. Final manual
engineering review remains pending.

Standalone use can consume an existing checked pressure output:

```powershell
.venv/Scripts/python -m bsa.circular_fan runs/source-port-pressure-final-workflow/pressure --curve examples/route-search/circular-fan-curve.json --out runs/new-circular-fan
```

The adapter verifies upstream input/method/artifact hashes, reconstructs the
extended network and body ledger from native material/canonical/IFC sources,
and compares them with the exact saved pressure input before solving. A pressure
success flag alone cannot establish native binding. Original numerical pressure
must pass; this entry does not waive or redesign a failed upstream budget.
Workflow tasks cannot replace the inherited network or native model.

The curve declares fixed speed, total-pressure rise, source points, density,
viscosity, inlet total pressure at the same upstream cap/reference, a positive
bounded flow bracket and solver tolerances. Efficiency must be `not supplied`.
External network stations must share an elevation, the whole bracket must be
turbulent Re>=4000, and there must be one terminal without branches/internal
withdrawals. A vertical excursion inside the checked path does not change the
equal-height external station contract; intermediate pressure suitability and
ambient-reference applicability remain unaccepted.

The solved demand/supply are written to a separate operating-network sidecar
and freshly rerun through the existing circular pressure engine. Source geometry,
original demand and original budget are preserved. Air power is Q times fan
total-pressure rise, reported in kW; it is not electrical input, nameplate motor
power or a Hong Kong fan-power assessment. Native fan geometry/ports and device
flow metadata are not automatically authored by this analysis.

Independent native-source trials give approximately 0.08029227424 m3/s at
6.963465719 Pa for the supplied synthetic curve, satisfying the 0.08 m3/s minimum.
The weak curve converges near 0.06897014789 m3/s and fails the unchanged minimum.
All curve points, fixed K, dimensions, pressure references and fluid conditions
are explicit study assumptions, not product data or installation ratings.
See evidence/circular-fan.json for complete workflow outcomes, current source
pins and the independent scalar-pressure regression.

Manufacturer curve authenticity/tolerances, stable region, installation category,
system effects, actual hardware, electrical power, acoustics/fire, multibranch
balancing, native joined drawing review and full Hong Kong/engineering acceptance
remain pending. Existing rectangular fan and real-graph research workflows retain
their separate source/applicability contracts.
