# Steady water graphs: EPANET 2.2 / WNTR 1.5.0

The optional adapter solves connected water graphs, including parallel pipes, branches, loops and reverse flow. It extends the prescribed-flow tree tools with an actual hydraulic solver.

```powershell
.venv/Scripts/python -m pip install -e ".[water]"
.venv/Scripts/python -m bsa.epanet examples/water-loop/project.json --out runs/water-loop
.venv/Scripts/python -m bsa.workflow execute examples/water-loop/plan.json --out runs/water-loop-workflow
```

Every data group cites a source description. Internal diameters, routes and absolute D-W roughness are metres; flows are m³/s. WNTR serializes LPS INP with millimetre diameters/roughness. Head is elevation plus **static pressure head in metres**, distinct from the older tree's total pressure Pa. Water specific gravity must be 1. `relative_viscosity` is EPANET's dimensionless multiplier, not m²/s. Diagram coordinates are schematic; route lengths are independently supplied. Reservoir connection elevation checks route plausibility; specified head is the boundary. See [units](https://usepa.github.io/WNTR/units.html) and [reference constants](https://github.com/OpenWaterAnalytics/EPANET/blob/v2.2/src/types.h).

Choose explicit DDA fixed withdrawals or PDA pressure-driven withdrawals. PDA has one global minimum/required pressure and exponent. Individual junction targets are acceptance criteria, not separate PDA curves. Between minimum and required pressure, delivered fraction is `((P-Pmin)/(Preq-Pmin))**exponent`; below/above, zero/full applies. DDA's inactive pressure-law source inputs are not serialized. Small native PDA demand overshoots remain visible and use the explicit demand tolerance. See [upstream hydraulic scope](https://usepa.github.io/WNTR/hydraulics.html).

Fixed-speed pump head curves begin at zero flow, strictly increase flow and decrease positive head, with two or at least four points. One-point implicit curves and three-point power-law fitting are unsupported. The solved point must remain within the original piecewise-linear curve and match its head; extrapolation fails. See the [EPANET network manual](https://usepa.github.io/EPANET2.2/3_network_model.html). Native unused energy defaults are recorded but never become accepted electricity estimates.

The isolated worker has an explicit timeout and trial budget, verifies runtime version 20200, and records DLL SHA256 and package versions. Native INP/RPT/BIN, raw JSON and node/link CSV are retained and hashed. Reopened INP checks cover IDs, endpoints, dimensions, demands, reservoir heads, pump curves/speed/status and active hydraulic/solver settings. Original input bytes remain unchanged; existing output folders are refused. Errors/timeouts retain failure evidence.

Independent numerical checks cover nodal continuity including reservoirs, junction head/elevation/static-pressure identities, PDA law, signed-flow-derived Q/A velocities, source pump interpolation and supplied targets. Native velocity and Q/A are retained separately: EPANET's legacy `LPSperCFS=28.317` differs slightly from exact SI conversion. The example declares a separate 0.0001 m/s cross-check tolerance for this and binary precision. The physical velocity limit uses SI Q/A without that allowance. The reference source tag explains conventions; runtime version does not prove an identical source build.

The synthetic diamond predicts symmetric 2 L/s JA/JB branches, 1 L/s AC and -1 L/s CB. The supplied pump meets the system near 4 L/s and 45 m head rise. Tests also exercise weak-pump pressure/delivery failure, a separate DDA parallel-pipe equal split, corrupted output, physical velocity failure and workflow tampering. All example values are synthetic, not manufacturer/code data. [Retained evidence](evidence/water-graphs/README.md).

Pending: independent general pipe energy residuals; actual source, route and IFC binding; fittings/products; efficiency, electrical coupling and NPSH; tanks, valves, controls, schedules, quality; drainage/fire rules and full professional acceptance. Execution success does not establish a finished engineering design.
