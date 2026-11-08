# Saved HVAC sizing inputs and jurisdiction checks

`bsa.hvac_idf_rules` reads the saved EnergyPlus IDF rather than trusting a second copy of numeric design assumptions. It calls the separately selected jurisdiction pack through the existing rule evaluator. Zone bases supply sourced application, scope and edition decisions, never replacement numeric conditions.

```powershell
.venv/Scripts/python -m bsa.hvac_idf_rules runs/hk-design-energy-v1/baseline/model.idf --basis examples/regulations-hk-hvac/zone-bases.json --pack regulations/hk/hvac-design-2026.11.08/pack.json --sources runs/hk-regulation-sources --out runs/new-native-hvac-check
```

The supported subset requires exact zone/sizing/thermostat/basis coverage, enabled zone sizing, sensible-and-latent sizing, constant dual heating/cooling setpoints, explicit constant sizing RH schedules, and explicit summer/winter design days using default dry-bulb range multipliers and wet-bulb humidity input. Overrides, other sizing-period types, nonconstant schedules and numeric substitutions in the basis are rejected. References currently require exact native spelling; this is not a general-purpose arbitrary-IDF validator.

Summer uses the cooling sizing setpoint and winter the heating sizing setpoint. The entire specified sizing RH band is checked conservatively: its lower bound against the summer minimum and its upper bound against the winter maximum. These are sizing inputs, not proof that simulated or operating indoor states maintain those values. Winter outdoor minimum is maximum dry bulb minus daily range; summer uses the maximum dry bulb and corresponding wet bulb. The profile interpretation follows the [EnergyPlus 25.2 design-day reference](https://bigladdersoftware.com/epx/docs/25-2/input-output-reference/group-location-climate-weather-file-access.html). The limits remain in the source-pinned [EMSD BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/BEC_2024_ENG.pdf) pack, not in this reader.

Outputs retain the IDF, basis, pack and available official-source hashes, missing sources, each zone/day comparison and the generated facts. Unsupported native structures raise an error; changed or missing official sources cannot pass. Exit code 0 means the supported comparisons pass; code 2 retains review/pending results. Neither implies complete regulatory conformity or design acceptance.

## Verification evidence

The original synthetic fixture has winter maximum 10 C and range 5 C. Both zones correctly require review because its minimum is 5 C. A separate synthetic fixture, `examples/regulations-hk-hvac/native-energy-project.json`, changes winter maximum to 7 C and range to zero. Both baseline and lighting variant were actually executed with EnergyPlus 25.2; the saved baseline's four zone/day comparisons pass. This deliberately selected boundary is not a weather recommendation for a real project.

`docs/evidence/hvac-idf-rules` preserves positive/negative rule outputs, native models/completion logs, run analysis and a hash manifest. Unit tests additionally exercise missing zone coverage, attempts to override native numbers, altered sizing mode/control schedules and changed official-source bytes. Synthetic source bytes in unit tests are explicitly fixtures; the retained integration results use the actual pinned official PDF.

The standalone adapter checks input files only. Workflow kind `hvac_regulations` now binds both variants of an earlier `energy` producer to its recorded IDF/OSM/SQL hashes and rechecks native completion evidence. It rejects replacement IDFs and selection of only one variant. Declare `depends_on` for the energy producer and `requires_pass` on downstream tasks that need this check. Other energy kinds, arbitrary model controls and automatic mandatory-check discovery remain unsupported. Zone humidity drift, load-method recognition, equipment efficiency, controls, other HVAC clauses and statutory applicability remain separate unresolved checks. Full conformity stays `not_established`.


## Workflow execution

A task has `kind: hvac_regulations`, `depends_on: energy-task-id`, `basis`, `pack` and `sources`. Its producer must be an earlier design-day `energy` task. Missing engine execution leaves the check pending; changed native artifacts fail it; scoped rule violations remain pending with per-zone/day review results. The task checks both variants before downstream gates may proceed.

Run `scripts/run_hk_hvac_demo.py --out runs/new-hk-hvac-demo --official runs/hk-regulation-sources/emsd-bec-2024.pdf --energyplus <executable>`; add `--negative` for the retained winter-minimum counterexample. The script stages copies within this repository, runs actual engines and writes workflow blocker diagnosis. Its final manual review intentionally stays pending, so an overall nonzero exit is expected even when supported checks pass. Positive and negative integration evidence is retained in `docs/evidence/hvac-regulatory-workflow`; original PDFs remain in ignored local storage.
