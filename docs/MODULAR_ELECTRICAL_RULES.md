# Bind common electrical results to whole-path voltage-drop rules


Scoped native electrical schematic now inherits the exact passing rule task via
`module_electrical_native`. The module explicitly inventories its DXF and replays
source device IDs, XY coordinates and symbolic styles before isolated AutoCAD
save, independent reopen and PDF plotting. Coincident symbols reject before CAD.
The public builder accepts `--drawings`; it stages an explicit presentation-only
layout and records original/chosen coordinates without changing electrical
quantities. This is a fit-to-page device schematic, not physical cable routing,
a complete electrical drawing set or full engineering acceptance. Actual PDF
visual review remains separate from native execution. See
[evidence](evidence/module-electrical-native.json).


Latest automatic-workflow validation:48related tests pass. Five actual
official-source scenarios preserve pass/fail/pending and upstream-disabled gates;
workflow/delivery correspondence verifies. See
evidence/module-electrical-rule-workflow.json. This does not establish native
release,other electrical rules or complete engineering acceptance.

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

The consumer now also runs as workflow kind module_electrical_rules. Declare
depends_on for the exact earlier electrical module plus topology,basis,pack and
sources. Replacement project/result inputs reject. Results are rechecked against
that producer and declared sources before downstream tasks and at completion;
delivery repeats those checks. Use requires_pass for intended consumers.

Stage the public source-only example with an existing official-source cache:

```powershell
.venv/Scripts/python examples/modular/build_electrical_rules_inputs.py --sources runs/official-sources --out runs/new-electrical-rules-inputs
.venv/Scripts/python -m bsa.workflow execute runs/new-electrical-rules-inputs/plan.json --out runs/new-electrical-rules
```

Missing official files remain absent/pending;changed cache hashes reject staging.
The builder records original public source hashes and the explicit removal of
the standalone demonstration metric from the basis. No unknown calculation value
is supplied in its place. Disabled/failed upstream analysis produces no rule
report;failed/pending checks block required dependent review. Coverage scheduling
recognizes the new task but does not turn it into full regulatory coverage.

It is not yet a registered replaceable electrical rule provider. Unsupported
numerical/authoring/legacy-native release consumers reject rather than borrowing this
rule gate with replacement sources. The source-bound device schematic is now supported as described above;physical-route release remains
unfinished. The original legacy electrical_regulations workflow remains available.

Initial standalone evidence:twenty-seven related tests pass across electrical/
water/common contracts.
Actual synthetic two-circuit data with unchanged pinned official sources passes
the scoped check. Deliberately longer feeders fail,unknown applicability and
missing official sources remain pending. Independent Decimal feeder/path sums
reconcile;manual metric overrides and coherently rehashed bound-fact changes
reject. These are scoped integration controls,not a completed electrical design.

To stage the native example, add `--drawings` to the public
`examples/modular/build_electrical_rules_inputs.py` builder, then execute its
plan with an explicit `--autocad` Core Console path. The early electrical
contract now requires a hashed `schematic_dxf` artifact. Regenerate old results
rather than rewriting historical manifests. The original coincident public
source remains unchanged;the staged source and source-manifest record the
chosen schematic-only layout. No physical layout is inferred.
