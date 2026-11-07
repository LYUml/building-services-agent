# Circular tree network pressure budgets

```powershell
.venv/Scripts/python -m pip install -e ".[network]"
.venv/Scripts/python -m bsa.network examples/network/air.json --out runs/air
.venv/Scripts/python -m bsa.workflow execute examples/network/plan.json --out runs/network
```

The `network` adapter aggregates prescribed withdrawals through a connected directed tree. It is a pressure-budget calculation for given flows, diameters and fluid properties, not a looped hydraulic solver, pressure-dependent demand calculation or fan/pump operating-point model. Node residual pressure inequalities do not prove that a passive unbalanced network will deliver the prescribed branch flow split.

## Input contract

All values are SI. See examples/network/air.json and water.json.

- `model`: `steady incompressible circular tree`.
- `sources`: descriptions of measurements, reference tables or explicit assumptions. Fluid, supply, every node and every segment cite a source ID. A nonempty source field does not validate the source's truth.
- `fluid`: density_kg_m3 and dynamic_viscosity_pa_s, both positive. Constant-density, Newtonian, fully filled flow is assumed. The tool does not look up properties or temperature-dependent viscosity.
- `supply`: source node and available total_pressure_pa (nonnegative, common reference).
- `nodes`: id, elevation_m, demand_m3_s (nonnegative) and required_total_pressure_pa (nonnegative). Supply withdrawal is zero. Terminal withdrawals are positive; intermediate withdrawals are allowed.
- `segments`: id, from/to nodes, positive internal diameter_m, measured/assumed length_m, nonnegative roughness_m, nonnegative minor_k and a supplied positive max_velocity_m_s. Input route length must be at least its elevation difference; no route is inferred from a drawing or straight-line distance.

Every non-source node has one parent. Cycles, disconnected components, duplicate IDs and unknown endpoints are rejected. Roughness/diameter must be below 0.05 for this adapter. Rectangular ducts, partially filled drainage, sprinkler demand methods, pressure-dependent outlets, pump/fan curves, transients and compressible gases are not supported.

## Methods and pressure basis

Continuity gives each segment the sum of downstream prescribed withdrawals. Circular area is pi D squared /4, velocity is Q/A and Reynolds number is rho v D/mu. Darcy factor is 64/Re below Re=2000. Re from 2000 inclusive to 4000 exclusive is rejected as transitional; no silent turbulent or interpolation assumption is applied. At Re>=4000 the pinned fluids library solves Colebrook with relative roughness epsilon/D.

Friction loss is f_D L/D times rho v squared /2; minor loss is K times the same local segment velocity pressure. K must be supplied for that reference velocity. Fittings at diameter changes and branch junctions need consistent source data, not a universal guessed K. Elevation contributes rho g dz with conventional g=9.80665 m/s2 and its sign retained.

Node pressure is **total pressure** (static plus velocity pressure), with elevation potential accounted separately. Required node values must use the same basis. Do not paste a static terminal pressure requirement into the total-pressure field without a justified conversion. For vertical air systems, a common-reference constant-density budget is not an ambient-referenced stack/buoyancy pressure model. The demonstrated air example is level; water example includes a rise.

The required source budget is the maximum over all node minimum pressures plus accumulated losses and elevation potential, bounded below by zero. This identifies the critical path under the prescribed flow assumptions. Available pressure and velocity are checked against user-supplied targets; there are no embedded regulation values. Pump head, motor electrical power, efficiency and an operating point are not selected by this calculation.

## Outputs and evidence

network.json contains segment flow, Reynolds, Darcy factor, friction/minor/elevation pressure components, node pressure/margin, critical path, source data and unresolved gates. segments.csv exports the segment schedule; report.html provides a brief pressure summary; manifest.json binds input and output hashes. A failed numerical target remains visible and causes the CLI/workflow task to fail while retaining its report. A successful calculation does not mark design acceptance.

Independent tests compare laminar loss to Hagen-Poiseuille, verify the turbulent factor against the implicit Colebrook residual, check branch continuity and static elevation pressure, and ensure insufficient supply/velocity failures propagate into workflow status. The synthetic air and water briefs were both executed. Direct BIM/CAD geometry binding, automatic sizing, balancing, component selection and complete professional acceptance remain pending.

Method reference: https://fluids.readthedocs.io/fluids.friction.html (Colebrook and Darcy friction-factor definitions). This is a calculation-method reference, not a building-services regulation clause.
