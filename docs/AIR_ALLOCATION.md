# Classified load and terminal flow allocation

`bsa.air_allocation.prepare(boundary, terminals, load_inputs, turndown)` composes
the existing `air_load.calculate` and `service_areas.allocate` adapters.
It returns classified thermal inputs/results, clipped service polygons, maximum
and minimum terminal flows, and area/flow conservation checks.

Supply a planar-metre GeoJSON polygon, unique terminal `id` and `center_m` pairs,
and an explicit turndown in (0, 1]. Each load input has `value`, `unit`, `source`,
and `classification` (given, measured, assumed, secondary_transcription).
Required quantities are area (m2), cooling_allowance (W/m2), sensible_fraction (1),
density (kg/m3), specific_heat (J/(kg K)), temperature_difference (K).

The separately given load area is proportionally allocated across the interpreted
net polygon. This preserves an explicit design choice when a drawing label and
interpreted geometry differ; it does not resolve their discrepancy. Uniform
allowance and nearest-centre partition are assumptions, not measured air coverage
or a spatial room-load model. No ADPI characteristic length is inferred.

Eight composition/load/geometry tests pass. Actual replay reconciles 240 terminal
flows across three private 80-terminal variants. Moving a terminal changes its
allocation while preserving the total; downstream VAV/tree flows and duct sizes
must be recomputed. Native drawing and final acceptance remain separate.
The unified producer and terminal-flow binding are described below; full design automation remains incomplete.

## Source-bound command

Run `python -m bsa.air_allocation project.json --out runs/new-allocation`.
Project fields are `boundary` (relative GeoJSON path), `boundary_sha256`,
`geometry_basis` (units and interpretation), `terminals`, `load_inputs`, and
`turndown`. Output `allocation.json` records both input hashes and preserves
the source classifications. Changed boundary bytes and output reuse are rejected.
Input geometry remains an interpretation requiring review; a matching hash does
not establish source-drawing correspondence. Nine focused tests pass, and actual
private CLI execution generates 80 updated terminal allocations.


## Unified producer and inherited lookup

Workflow kind `air_allocation` accepts `project`, optional `requires_pass` and
`description`. Geometry must stay inside the plan root, its hash must match,
and the project, geometry and three calculation modules enter run integrity.

A `terminal_throw` task can set `depends_on` to an earlier `air_allocation`.
Its project must omit `turndown` and every `maximum_flow_L_s`; both are inherited
from the exact new allocation artifact, whose hash is checked before lookup.
Terminal IDs must match exactly. Catalogue and reviewed characteristic lengths
remain explicit inputs. Allocation failure leaves lookup pending, changed producer
bytes or replacement flows fail, and neither path infers ADPI acceptance.

42 focused allocation, lookup, schedule, executor and diagnosis tests pass.
Actual private execution preserves all brief requirements, calculates 80 allocations
and 640 direction/flow lookup cases, and matches the prior trial within
2.85e-14 L/s. The 47 supplied duct-section calculations also run, but do not yet
inherit their section flows from this producer; VAV/tree aggregation and automatic
size/drawing regeneration remain separate integration work. Regulatory and full
engineering/delivery acceptance remain pending.


## Inherited tree flow for duct schedules

`duct_schedule` can also set `depends_on` to an earlier `air_allocation`.
Omit every section's `flow_m3_s` and add project `tree` with exactly:
`root`, `sections` (each id/from/to), `leaf_terminals` (node to terminal ID list),
and nonempty `basis`. Schedule and tree section IDs must match exactly.
All allocated terminals occur in exactly one leaf group. Every leaf is covered;
cycles, disconnected components, repeated parents, omitted/duplicate terminals
and replacement flow inputs reject. Leaf demand is summed upstream through the
declared directed tree, with a conservation check. The inherited allocation hash
is checked before and after calculation and recorded beside the schedule.

This is flow/identity binding for a declared supply tree, not a pressure-dependent
network solve or evidence of physical connections. The existing equivalent-round
adapter still checks supplied sizes; it does not automatically select sizes or
regenerate drawings. Unknown VAV characteristics, fittings, actual lengths and
fan pressure stay unresolved. Source geometry/group interpretation requires review.

45 focused tests pass, including analytical branch balance, layout-to-schedule
propagation, invalid graph/membership, failed upstream blocking and exceeded section
limits. Actual private 80-terminal / 20-leaf / 47-section execution reconciles all
section flows with the prior trial within 1.78e-15 m3/s, preserving all original brief
requirements and pending engineering/regulatory work packages.
