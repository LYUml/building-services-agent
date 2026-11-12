# Geometry-bound terminal flow allocation

Workflow task `spatial_air_allocation` inherits a passing spatial_air_balance
producer and a plan-local per-room `basis`. The standalone CLI is:

```powershell
.venv/Scripts/python -m bsa.spatial_air_allocation runs/air-balance/air-balance.json --basis runs/terminal-design-basis.json --out runs/new-terminal-allocation
```

The adapter reuses air_allocation.prepare,air_load and the pinned Shapely
nearest-centre partitioner. It supplies inherited room boundaries and classified
thermal inputs;caller replacement geometry,areas and flows are forbidden. Every
balanced space needs a basis with terminal choices and a dimensionless turndown.
Each terminal declares id,center_m,unit m,source and classification. Turndown
declares value,unit1,source and classification. Given/measured/assumed/secondary
transcription/design_choice records remain distinguishable;none sets installation
or engineering verification true merely by being asserted.

One terminal now receives the whole original boundary and load area;multiple
terminals retain existing Voronoi allocation. Concavities and holes in supported
input boundaries are not filled. Centres must lie inside the service region,
IDs are unique across rooms,and total maximum flow must conserve the inherited
model total. Per-room floor elevation is retained separately from the planar
terminal coordinates;mounting heights are not invented. Polygon representation
normalization stabilizes winding/start order without moving coordinates or
loosening source tolerances.

Output bsa.spatial-air-allocation/1 is a replayable domain report,not a newly
registered generic payload. Source/method pins,exact balance/basis lineage and
task dependency states are rechecked at delivery. Disabled upstream geometry
produces no allocation report;rewritten terminal flow fails source replay.

The public workflow builder adds this stage with both --air-balance and
--terminal-allocation. Its one interior-point outlet per room and40%turndown are
explicit synthetic software choices,not an optimized distribution design or
equipment specifications. Actual three-space native/MOOSAS workflows agree on
all allocation records. Maximum/minimum totals are870.4/348.16L/s under that
fixture's assumptions;independent Decimal turndown checks agree. Twenty-two
related tests pass. See evidence/spatial-terminal-allocation.json.

ADPI_verified,installed_geometry_verified,simulation_executed and design_accepted
remain false. Nearest-centre service area is not measured air coverage or a
verified characteristic room length. Diffuser catalogue selection,ceiling/jet
interactions,flex/VAV/duct routing,pressure/fan duties,editable MEP drawings and
full source/physical/regulatory acceptance remain separate work.
