# Bind common electrical results to whole-path voltage-drop rules

`bsa.module_electrical_rules` reuses electrical_paths.calculate_paths/bind_facts
and the existing regulation evaluator. It requires a passing verified
single-phase electrical module,explicit sourced radial topology,fact/edition
basis,selected voltage-drop rule pack and official-source cache.

```powershell
.venv/Scripts/python -m bsa.module_electrical_rules runs/project/electrical/result.json --topology runs/project/topology.json --basis runs/project/basis.json --pack regulations/hk/2026.11.08/pack.json --sources runs/official-sources --out runs/project-electrical-rules
```

The upstream module supplies the original electrical project and checked branch
result. The existing radial calculator replays that source and must reproduce
the inherited branch report exactly. All circuits must share one phase under
the existing scalar method. Feeders require explicit origin,connections,lengths
and complete single-phase mV/A/m coefficients. The source must cover every
circuit;cycles,disconnected or unused feeders reject. Branch-only voltage drop
is never relabelled as the full installation path.

The basis supplies sourced applicability facts and edition decisions. It must
omit installation_origin_to_fixed_equipment_voltage_drop:the consumer binds
that value from the computed branch-plus-feeder path and rejects overrides.
Unknown applicability/edition or missing official bytes stays pending;exceeded
selected rules stay fail. Source/model/calculation/pack agreement is not actual
route,product,legal applicability or full electrical acceptance.

Outputs retain path-calculation.json,bound-projects.json and the detailed
electrical-module-rules.json with common bsa.rule-assessment/1. The same generic
assessment projection is now shared with the existing water consumer;its pending
coverage is preserved per entity. Verification reconstructs path quantities,
bound facts,source availability and checks. Updated output hashes cannot clear
changed facts. This is source replay,not independent physical validation.

This initial consumer is CLI/API only. It is not yet a registered replaceable
electrical rule provider or automatic workflow task. Do not infer automatic
same-model CAD release gates from standalone execution. The original legacy
electrical_regulations workflow remains available;other required electrical
protection/native/code obligations remain unfinished.

Twenty-seven related tests pass across electrical/water/common contracts.
Actual synthetic two-circuit data with unchanged pinned official sources passes
the scoped check. Deliberately longer feeders fail,unknown applicability and
missing official sources remain pending. Independent Decimal feeder/path sums
reconcile;manual metric overrides and coherently rehashed bound-fact changes
reject. These are scoped integration controls,not a completed electrical design.
