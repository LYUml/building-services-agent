# Hong Kong air-conditioning water piping

The `hk-hvac-water-2026.11.08` pack implements selected conditions from [EMSD BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/BEC_2024_ENG.pdf), clauses 6.9.1ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“6.9.3, printed pages 26ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“27 / PDF pages 32ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“33. The official PDF SHA256 matches the existing BEC source cache. Scope, edition and prescriptive-route selection need explicit sourced project decisions. These are air-conditioning water-piping checks, not general domestic water rules.

The pack separates the diameter bands, fixed/variable flow velocity limits, distributed friction limit and required variable-flow pump control alternatives. Small-pipe checks do not silently apply the large-pipe friction limit. Unsupported/missing input units, values, control evidence or source files cannot pass.

```powershell
.venv/Scripts/python -m bsa.water_pipe_regulations examples/regulations-hk-water/network.json --basis examples/regulations-hk-water/bases.json --pack regulations/hk/hvac-water-2026.11.08/pack.json --sources runs/hk-regulation-sources --out runs/new-water-rule-check
```

The adapter recomputes the original circular-tree network with the existing pinned `fluids` Darcy/Colebrook implementation. It derives each segment's velocity and distributed friction per metre, excluding fitting losses and elevation from that metric. It requires exact segment basis coverage and prohibits supplying replacement numeric velocity/friction values. Results retain input hashes, the fresh hydraulic report hash, bound facts and segment-level regulatory comparisons. Hydraulic pressure/velocity failures remain failures even when the selected regulatory comparisons pass.

`code_diameter` is a separately sourced classification in mm. It is not silently equated to the hydraulic internal bore used in network calculations; the agent must establish the actual project/product interpretation from evidence. `flow_mode` and, for the variable-flow large-pipe branch, `pump_control` also need sourced evidence. Supported control categories are `variable_speed` and `multiple_duty_fixed_speed_staged_by_demand`. This checks a declared control scheme, not installed pump operation. Density/viscosity, roughness, flows, route lengths and diameter evidence remain engineering inputs requiring review.

All examples are synthetic. `docs/evidence/hk-water-piping` retains a passing baseline, a high-flow failure and a low-pressure case where selected rules pass but hydraulics fail. Tests cover the exact diameter and numerical boundaries, both pump-control alternatives, invalid/missing data, source changes and attempts to override computed metrics.

Workflow kind `water_pipe_regulations` takes `project`, `basis`, `pack` and `sources`. A downstream `network` task can declare `requires_pass` on it; preflight requires identical network input bytes, including through intermediate prerequisites. Coverage review recognizes this scheduled adapter. Other network authoring/optimization consumers are not automatically bound to checked geometry or revised dimensions. Looped hydronic circuits, operating-point/control performance, 6.8 variable-flow applicability, complete HVAC clauses and full regulatory conformity remain pending. The updated planning catalog `regulations/hk/coverage-2026.11.09.json` lists this additional HVAC module; its predecessor remains unchanged for reproducible historical evidence.


## Workflow evidence

`docs/evidence/water-pipe-workflow` contains official-source positive and low-pressure synthetic plans and runs. The latter retains a failed rule-adapter task and skips its downstream network task. Each archive excludes the official PDF; restore the pinned source beside its plan before rerunning with `python -m bsa.workflow execute plan.json --out new-run` (see the CLI help for the execution subcommand). Input identity and native/visual acceptance remain separate: this milestone does not bind CAD/BIM authoring to water-rule results.


### Saved IFC producer

A `water_pipe_regulations` task may instead specify `depends_on` on an earlier `network_coordination` task, omitting `project`. It verifies the producer's saved artifact hashes and original model/binding identities, reopens and reconciles IFC ports/route length/internal diameter, then recomputes the derived hydraulic network for the rule checks. An unsuccessful producer blocks execution; replacement project inputs are rejected. This supports the existing circular-tree geometry subset, not arbitrary IFC or optimized-network producers. Code-diameter classification and pump-control evidence remain separate sourced inputs. Further CAD/plotting and modified downstream geometry still need their own correspondence checks.

`docs/evidence/ifc-water-regulations` retains an actual saved-IFC negative high-flow example and a separately staged synthetic 0.1 L/s positive example. The negative producer fails hydraulics and its regulatory task remains pending. The positive producer and scoped rules pass; complete engineering and legal acceptance remain unresolved.


### Regulation-aware finite selection

`python -m bsa.water_pipe_design examples/regulations-hk-water/network.json --catalogue examples/regulations-hk-water/catalogue.json --basis examples/regulations-hk-water/bases.json --classifications examples/regulations-hk-water/classifications.json --pack regulations/hk/hvac-water-2026.11.08/pack.json --sources runs/hk-regulation-sources --out runs/new-regulated-search` enumerates every allowed catalogue combination within the existing explicit search bound. Each option requires its own sourced code-diameter classification; hydraulic internal bore does not silently determine it. All candidates retain derived input files, fresh hydraulic calculations and rule comparisons. Selection minimises the supplied length-weighted material score only among candidates passing both hydraulic targets and scoped rules. It reruns the selected candidate and records artifact hashes. No qualifying candidate means no selection, including when official sources are missing.

The synthetic example retains D25 hydraulic/rule failure, D32 hydraulic success but rule review, and D40 passing both. Evidence is in `docs/evidence/water-regulated-design`. These are test sizes/material points, not product availability or costs. Route, demands and local K remain fixed assumptions; equipment control, fittings, installed geometry, other clauses and full acceptance remain unresolved. This standalone search does not yet author the selected IFC or integrate with a workflow task.


### Selected model revision

`bsa.regulated_water_model` connects the finite search to the existing straight-route IFC revision tools. Required CLI flags are `--network`, `--model`, `--binding`, `--catalogue`, `--geometry`, `--basis`, `--classifications`, `--pack`, `--sources`, `--out`. For the retained example use network/model/binding/catalogue/geometry from `examples/water-riser`, `riser-bases.json` and `riser-classifications.json` from `examples/regulations-hk-water`, and the HVAC water pack/cache above.

Geometry filtering retains rejected options. Remaining candidates undergo hydraulic and rule checks; the selected diameter revises a separate source model while preserving fixed endpoints and stable object/port identities. Saved IFC geometry is reopened and reconciled, then hydraulics and rules run again from its derived network. The final pressure budget must match the ranked candidate. No feasible candidate produces no selected model. Original inputs and baseline IFC remain retained.

Actual synthetic evidence is in `docs/evidence/regulated-water-model`: the four-size riser search selects D40, creates a new IFC and passes the scoped rechecks. Tests additionally verify that insufficient supply leaves no selected model. Scope remains supported straight circular pieces with supplied outside diameters and fixed route/K assumptions. Automatic workflow registration, clash/clearance, product applicability, native plotted drawings and whole-project acceptance remain pending.
