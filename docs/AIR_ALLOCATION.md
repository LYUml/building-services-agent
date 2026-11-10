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
This is a callable composition, not yet a complete workflow producer binding.
