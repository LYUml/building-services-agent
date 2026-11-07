# Conditional network sizing and iteration

The `network_design` adapter turns a supplied network plus an explicit candidate catalogue into a versioned baseline/design comparison. It uses the same actual fluids-backed circular tree solver, with the same prescribed-flow and total-pressure contract as NETWORKS.md.

```powershell
python -m pip install -e ".[network]"
python -m bsa.workflow execute examples/network-design/plan.json --out runs/network-design
python -m bsa.workflow verify runs/network-design
# Or call the tool directly:
python -m bsa.network_design examples/network-design/project.json --catalogue examples/network-design/catalogue.json --out runs/design-direct
```

Catalogue options contain source-linked IDs, internal diameters, absolute roughness and material score per metre. `allowed_options` must cover exactly every network segment. The only supported objective is `minimise sum(length_m * material_score_per_m)`, subject to all existing velocity, total-pressure and flow-continuity checks. Scores are supplied metrics, not inferred monetary cost, quantities or emissions. Demand, routes, elevations, fluid properties, local K and targets are not altered to make a candidate pass.

The catalogue must explicitly source the assumption `prescribed demands; route and local K unchanged across sizes`. Real fittings, equivalent lengths and K reference velocities may invalidate this assumption; do not silently treat a synthetic catalogue as product data. Alternative fitting methods require their own model before use.

Every allowed combination is enumerated. `max_evaluations` is an explicit integer bound up to 10000: if the full product exceeds it, validation fails before creating a run, rather than sampling/truncating and calling the result optimal. IDs/order are deterministic. Feasible candidates rank by material score, then required source total pressure, then lexical option IDs by sorted segment ID. This proves an optimum only within the supplied finite catalogue and supported model, not a universal engineering optimum.

Pressure/velocity failures remain in candidate records. Unsupported transitional regimes remain analysis-error rows; they are never assigned invented friction factors. No feasible combination yields no selected network and nonzero CLI/workflow failure while retaining evidence. A bad baseline's calculation or error also remains visible. Missing solver packages are execution failures, not successful synthetic calculations.

The selected variant changes only diameter, roughness and their provenance. It is saved as `selected-network.json` and independently run again into `selected`; the ranked pressure and pass status must match. Baseline artifacts, the complete `candidates.csv`, `report.html` and `design-comparison.json` retain sources, constraints and failures. Workflow integrity binds original project/catalogue plus generated evidence and detects later output edits.

The supplied synthetic air example evaluates 125 combinations, of which 18 meet the defined checks. The deliberately undersized baseline requires about 734.457 Pa against its 300 Pa source and fails velocity/pressure. The minimum-score candidate uses 0.35 m MAIN, 0.20 m BR-A and 0.25 m BR-B internal diameters, scores 63 synthetic material points and requires about 125.598 Pa. Its minimum-size result also matches an independent per-branch velocity lower-bound calculation. These values demonstrate the adapter; they are not manufacturer selections or a finished balanced ventilation system.

Selected dimensions are not silently applied to an existing IFC model: outside envelope dimensions, wall thickness, fittings, clearances and source evidence remain necessary. Update the authored model explicitly and rerun NETWORK_BINDING.md reconciliation. Fan/pump curves, motor electrical power, pressure-dependent flow splitting, noise, closed loops and domain/code acceptance remain pending. `design_accepted` always remains false here.
