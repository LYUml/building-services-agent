# Geometry-bound thermal and supply-air balance

`bsa.spatial_air_balance` consumes a verified common box/polygon-space result and
an explicit per-space load basis. It reuses air_load.calculate unchanged apart
from permitting `geometry-derived` classification for the inherited area only.
No cooling-load simulation engine or new numerical solver is introduced.

Each basis maps every source space ID exactly to five classified quantities:
cooling_allowance,sensible_fraction,density,specific_heat,temperature_difference.
Use the existing air_load.UNITS and value/unit/source/classification records.
Omit area:the consumer binds the actual neutral-space floor_area_m2 with its
source identity and geometry-derived classification. Missing/extra rooms and
replacement areas reject. Geometry-derived density or other unsupported physical
classification is not accepted. Separate given-area workflows remain available;
this consumer does not override a brief's different governing load-area basis.

```powershell
.venv/Scripts/python -m bsa.spatial_air_balance runs/space-result/result.json --basis runs/air-balance-basis.json --out runs/new-air-balance
```

Workflow task `spatial_air_balance` takes an earlier module_exchange `depends_on`
and plan-local `basis`,with optional requires_pass/description. It retains source
and method pins,whole space coverage,thermal kW versus L/s and pending full
acceptance. Disabled or failed geometry does not produce downstream calculation.
Delivery checks the exact declared producer/basis relationship and replays the
calculation;stripped method pins,rewritten totals and missing passing reports
reject. Explicit host project-workspace selection applies to execution/verification.

The public builder accepts `--air-balance` to add the task and its synthetic basis:

```powershell
.venv/Scripts/python examples/moosas-transform/build_workflow.py --out runs/new-air-inputs --ifc runs/native-fixture/polygonal-spaces.ifc --length-tolerance-m 1e-6 --area-tolerance-m2 1e-8 --sources runs/official-cache --air-balance
.venv/Scripts/python -m bsa.workflow execute runs/new-air-inputs/plan.json --out runs/new-air-workflow --module-provider recognition=ifcopenshell.polygon-spaces
```

Actual native/MOOSAS replacement runs produce identical calculation records
for14/24/30m2synthetic spaces:13.6kW thermal total allowance,10.88kW thermal
sensible trial and870.4L/s. Independent Decimal recomputation agrees. These
numbers belong to the explicit synthetic200W/m2,0.8fraction and declared air
properties/temperature difference,not actual coursework room loads. Nineteen
distinct related tests pass,including external workspace and disabled gates.
See evidence/spatial-air-balance.json.

Output `bsa.spatial-air-balance/1` is this domain adapter's replayable report,
not a newly registered generic module-runner payload. Numeric task pass means
the existing constant-property balance executed;room_sensible_load_verified,
simulation_executed and design_accepted remain false. Detailed room loads,
latent conditions,ventilation,ADPI,terminal design,duct pressure/fan duties,
plant electricity,annual energy and full physical/regulatory acceptance remain
separate obligations. The selected office lighting check in the example does
not establish HVAC conformity.
