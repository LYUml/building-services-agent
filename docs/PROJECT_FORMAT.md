# Electrical project JSON v1

All geometry is metres in a common WCS. Supply voltage is line-to-neutral volts. Each device has a unique id, circuit id, electrical_kw, power_factor in (0,1], x_m/y_m and source. Each single-phase circuit has a phase L1/L2/L3, demand_factor [0,1], breaker_a, tabulated_ampacity_a, correction_factor (0,1], route_length_m, vd_mv_a_m, max_vd_percent, and source. The voltage-drop coefficient must already correspond to the applicable single-phase circuit convention; the tool does not add an extra factor of two. A source can cite an explicit synthetic assumption, manufacturer document or exact regulation edition/table. Nonempty sources are traceability assertions, not automatic verification of their truth.

`name`, `supply_voltage_v`, `devices`, `circuits`, `sources` are required. `sources` maps source IDs to descriptions. All referenced source IDs must exist. Distances and electrical inputs must be finite. This first slice does not model three-phase individual circuits, motors, harmonics, protective fault disconnection or incomer diversity. Summed phase VA is a diagnostic, not a complete main-switch or transformer selection.

Use one project folder per assignment. Keep original documents under inputs and generated runs separate. Do not infer area or cable route from device coordinates. Record the route explicitly and cite how measured or assumed.
