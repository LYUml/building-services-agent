# Hong Kong air-conditioning water piping

The `hk-hvac-water-2026.11.08` pack implements selected conditions from [EMSD BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/BEC_2024_ENG.pdf), clauses 6.9.1Ã¢â‚¬â€œ6.9.3, printed pages 26Ã¢â‚¬â€œ27 / PDF pages 32Ã¢â‚¬â€œ33. The official PDF SHA256 matches the existing BEC source cache. Scope, edition and prescriptive-route selection need explicit sourced project decisions. These are air-conditioning water-piping checks, not general domestic water rules.

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
