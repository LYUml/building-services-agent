# Source-replayed calculated airflow in BIM

`circular_fan_metadata` consumes a passing native circular fan operating result,
reconstructs the original pressure/curve scenario and writes a new IFC4 copy.
It uses pinned IfcOpenShell 0.8.5 property-set APIs, existing geometry/property
snapshots and saved schema checks. The isolated official MCP pump-text metadata
adapter retains its different runtime/contract. No new engine or dependency is
introduced.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/route-search/port-airflow-state-plan.json --out runs/new-airflow-state-workflow
```

The plan retains the preceding selection/model/pressure/duty requirements and
adds a saved calculated-state requirement. `state` depends on the independent
fan operation; failed or unavailable fan duty produces no state model. The
route-only DXF remains sourced from its original canonical geometry and additionally
requires this state task. It does not depict all joined source bodies or introduce
flow annotations. Full joined/native drawing review remains pending.

Standalone use accepts the exact operating-output folder:

```powershell
.venv/Scripts/python -m bsa.circular_fan_metadata runs/airflow-state-operation --out runs/new-airflow-state
```

Fan results now carry explicit `input_roles` for the pressure producer and curve.
Older reports without those roles must be regenerated, not relabelled or rehashed.
The reader verifies source/method/artifact bytes, native body/port binding, fluid
runtime, a fresh curve/network solve, saved operating input and selected-curve
ranking when present. A convergence flag or an edited pass flag cannot supply a
calculated BIM state if the original minimum flow or other criteria fail.

New properties use `BSA_CalculatedAirflowScenario` on local bodies and
`BSA_CalculatedPortAirflowScenario` on their exact owned ports. Flow values are
IfcVolumetricFlowRateMeasure with an explicit derived metre^3/second unit.
Pressure values are IfcPressureMeasure with explicit Pascal units. Text source
and classification records use IfcText. The original project unit assignment is
unchanged; no default unit interpretation is required for these new quantities.

Body properties include operating/minimum flow, inlet/outlet common-reference
total pressures, the following inlet pressure, straight/body/interface pressure
contributions and the signed elevation term. Port values use the actual inlet
or outlet side of that body. With an extra interface K, the preceding outlet and
following inlet can have different assumed pressures at coincident coordinates;
the interface loss is not assigned to both sides twice. Negative common-reference
values are not reinterpreted as measured ambient-gauge/static pressure.

Original source/K/fluid/curve assumptions remain in the pinned source chain.
Each scenario property set carries source IFC, fan result and curve hashes, a
curve candidate identifier and a calculated/not-measured scope. Fan air power
is not written onto duct bodies as motor or electrical input. No whole-system
flow is inferred for unrelated elements and no fan equipment is invented.

The writer preserves original element/port inventories, shape/property/placement
records, predefined types, existing directed links, system membership, project
units and original simple-property/quantity datatypes and explicit units.
Unrelated existing scenario data is retained. A reserved scenario name already
on a target rejects rather than overwriting source values. The saved model is
reopened, all expected values/types/units checked, and schema/EXPRESS validated.
Source files remain unchanged. `scenario-snapshot.json` is JSON-roundtrip replayable.

The synthetic seven-body case writes 196 properties on seven bodies/fourteen
ports. Outputs are `Operating Airflow Study.ifc`, `scenario-snapshot.json` and
`fan-metadata.json`. See evidence/circular-fan-metadata.json for complete executed
workflows, unit-scale/false-pass controls and preserved requirement coverage.
Source copies and outputs stay outside immutable operating/native/selection
producer folders.

These are calculated local study properties, not measured operation, certified
manufacturer parameters or a host application's automatic MEP flow solution.
Actual fan geometry/ports, motor/electrical input, system effects, full multibranch
balancing, native drawing acceptance and complete Hong Kong/engineering checks
remain pending.
