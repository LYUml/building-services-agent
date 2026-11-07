# Source-bounded liquid pump operating points

`pump_operating_point` extends the prescribed-demand pressure engine with a separate **single-terminal fixed-pressure, free-flow** calculation. It finds the intersection of a supplied fixed-speed pump pressure curve and the pipe-line resistance. It does not reinterpret every network demand as pressure dependent, solve passive branch flows or model a closed circulation loop.

```powershell
python -m pip install -e ".[network,bim,clash]"
python -m bsa.workflow execute examples/water-riser/pump-plan.json --out runs/water-pump
python -m bsa.workflow verify runs/water-pump
# Or a validated explicit network input:
python -m bsa.pump network.json --curve pump-curve.json --out runs/pump-only
```

The workflow accepts a sourced `curve` and exactly one `project` network input or an earlier `network_coordination`, `network_design` or `network_model_design` dependency. It resolves the producer's known input artifact, not a caller-supplied arbitrary output path. Nonpassing producers leave pump analysis pending. The water-riser example consumes the selected IFC-reconciled network dimensions without another length/diameter copy. Geometry remains fixed; the operating-state file changes flow and source pressure explicitly, without changing original project files or the electrical scenario.

## Input basis

The exact model declaration is `fixed-speed liquid pump; single fixed-total-pressure terminal; free flow`. The network's terminal `demand_m3_s` is the minimum design-flow target, while its `required_total_pressure_pa` is explicitly treated as a fixed boundary for this calculation. That is a new operating assumption, not a deduction from a minimum pressure requirement. A throttled/control-valve or pressure-dependent fixture needs its own supported boundary model; do not silently map one here.

The curve requires source descriptions, source ID, positive fixed `speed_rpm`, matching fluid density/viscosity, nonnegative `inlet_total_pressure_pa`, an efficiency basis, ordered performance points, an explicit positive `flow_bracket_m3_s`, flow/pressure convergence tolerances and a 1..200 iteration budget. Points use `flow_m3_s` and `total_pressure_rise_pa`; flow must strictly increase and pressure must strictly decrease. No point reordering, fitted polynomial, affinity correction, speed change or extrapolation is performed. A supplied zero-flow shutoff point is retained, but the solver's positive bracket must lie inside the source curve.

Pump pressure rise is the added **total pressure**, separate from inlet pressure. The current pressure/power contract assumes equal pump inlet/outlet elevations at the network source reference; suction geometry is not bound to the pump envelope. Source that assumption explicitly. Route elevation potential is calculated separately as rho*g*dz. Manufacturer head values need an explicit sourced unit/basis conversion before becoming pressure-rise inputs. Total pressure and static pressure are not interchangeable without the velocity basis.

The network must be an unbranched directed line, with one terminal and zero internal withdrawals. Its constant-density Newtonian fluid must match the supplied curve. The whole solver bracket must remain either laminar below Re=2000 or turbulent at/above Re=4000 for every segment. A bracket crossing the unsupported transition is rejected; the tool does not skip an unverified interval. A full source curve can contain shutoff and transition flows outside the explicitly declared solver bracket.

If `efficiency_basis` is `wire to water`, every point must supply the combined `wire_to_water_efficiency`, between zero and one and strictly positive at positive flows. Zero is permitted at shutoff. Interpolated combined efficiency gives estimated electrical input; a pump-only shaft efficiency cannot be used as motor/drive efficiency. With `not supplied`, efficiency fields are absent and electrical input stays null. The pump speed is curve metadata, not a command to physical equipment.

## Calculation and evidence

Every evaluated flow reruns the existing Darcy-Weisbach/Colebrook or laminar engine with the original diameters, route, roughness, local K and fluid. System required pump rise is terminal boundary pressure plus all line losses/elevation potential, minus inlet pressure. The bracketed residual is pump rise minus that requirement. A monotone descending pump curve and this fixed single-line resistance model support a unique bracketed intersection. Bisection preserves evaluated sign bounds and stops only when both source tolerances pass; insufficient iteration budget remains a failure.

The selected state uses the lower flow bound with a nonnegative pressure residual. Minimum design flow is checked against that conservative bound; velocity is checked through the upper bound. Selected node pressures and an independent saved-input pressure rerun must also pass. A converged intersection can still fail capacity or velocity checks; its evidence is retained. Missing sign bracket or convergence never produces an extrapolated operating state.

Hydraulic kW is Q times pump-added total-pressure rise divided by 1000. Estimated electrical kW divides that by combined wire-to-water efficiency. Inlet pressure is not counted as pump-added power; kVA, nameplate rating, starting current, annual energy and thermal load are not inferred. `operating-network.json` gives the revised state its own provenance and is rerun through `bsa.network`. `pump.json`, `iterations.csv`, `report.html`, raw network results and hashes retain sources, root bounds/residuals, failures and pending gates.

The synthetic 5 m riser produces approximately 1.253485 L/s at 157.32574 kPa pump rise, 0.197205 kW hydraulic and 0.437828 kW estimated electrical input with the supplied synthetic combined efficiency. Its original 0.75 kW electrical assumption is unchanged and remains unreconciled. Tests compare an independent analytic Poiseuille intersection, nonzero inlet pressure/power, curve bounds, capacity/velocity failures, absent efficiency, fluid mismatch, branches, transition rejection, iteration exhaustion and artifact tampering.

Real curve validity, operating region/BEP, viscosity corrections, NPSH/cavitation and absolute suction conditions, pump/motor selection, control behavior, electrical reconciliation and complete engineering acceptance remain pending. This is not general building water distribution acceptance.

Method references: [Hydraulic Institute combined curves](https://datatool.pumps.org/pump-fundamentals/combined.html), [Hydraulic Institute pump curves and efficiency definitions](https://datatool.pumps.org/pump-fundamentals/pump-curves), and [US DOE pumping systems sourcebook](https://www.energy.gov/sites/prod/files/2014/05/f16/pump.pdf). These explain the method; they do not certify example values or constitute copied solver code.
