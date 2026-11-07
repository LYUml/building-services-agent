---
name: mep-network-analysis
description: Calculate source-linked circular air/water tree pressure budgets and single-line fixed-speed liquid pump operating points. Use for supported duct/pipe pressure, sizing and sourced pump-curve checks.
---

# Network pressure analysis

Read docs/NETWORKS.md before interpreting pressures. Use `python -m bsa.network <project.json> --out <new-run>` or the `network` workflow adapter. Install the optional network dependency. Source every flow, internal diameter, route length, roughness, fitting K, fluid property and allowable velocity/pressure. Do not derive a route length from unrelated coordinates or manufacture a regulation table value.

This adapter supports only connected directed trees with prescribed withdrawals, constant-density Newtonian fluid and fully filled circular sections. It rejects transitional Reynolds numbers and loops. Do not map a closed chilled-water loop, partially filled drain, pressure-dependent sprinkler network or rectangular laminar duct into it merely to obtain a result.

The pressure contract is total (static plus velocity), common-reference, with elevation potential separate. Convert a supplied static requirement only when velocity/basis are justified; otherwise retain it as unresolved. Level air examples do not validate vertical ambient/stack pressure treatment. Use fittings K referenced to each local segment velocity. Do not confuse a Darcy factor with a Fanning factor.

Review segment calculations and node margins, source-required pressure and critical path. Failed targets must remain failed or trigger a versioned design iteration. A passing budget does not prove passive flow splitting, balancing, a fan/pump operating point, motor electrical power, cavitation, acoustics or code compliance. Keep these gates explicit.

For geometry-linked work, read docs/NETWORK_BINDING.md and use the `network_coordination` adapter or `bsa.network_binding`. Keep elevations, length and internal diameter out of the network input; derive these from explicitly bound model ports and source-backed diameter properties. Require connected straight axis-aligned port-centre chains and saved IFC reconciliation. Do not derive circular diameter from an envelope width. The standalone synthetic network fixtures remain independent unless explicitly bound.

Keep IDs aligned with actual schedules and models. Geometric binding does not prove circular product solids, junction shape, fitting K, clashes, balancing or professional acceptance. Preserve those gates separately.

For bounded sizing/design iteration, read docs/NETWORK_DESIGN.md and use `network_design` or `bsa.network_design`. Require a sourced finite catalogue and explicit allowed options for every segment, objective and search bound. Keep demands/routes/K/limits fixed under a sourced size-invariance assumption; never relax acceptance to make a choice pass. Preserve the baseline, all failed/error candidates and the selected rerun. No feasible option means report failure and request revised source/design constraints. A finite-catalogue material-score optimum is not a cost/carbon estimate or full engineering optimum. Explicitly update/reconcile BIM after sizing; do not infer outside dimensions from internal diameters.

For authored-model iteration, read docs/NETWORK_MODEL_DESIGN.md and use `network_model_design`. Require a shared canonical project UUID and separately sourced outside-envelope catalogue. Preserve world endpoints and original model data; retain space-containment rejection reasons before hydraulic ranking. Verify saved IFC internal/outside dimensions, stable device/port IDs and the model-derived pressure rerun. This supports fixed straight centrelines and bounding envelopes, not automatic rerouting, fitting resizing or collision acceptance.

For a fixed-speed liquid pump curve, read docs/PUMPS.md and use `pump_operating_point`/`bsa.pump` only with an explicit single-terminal fixed-total-pressure/free-flow assumption. Preserve the full source curve and separately declare a positive solver bracket; never cross an unsupported Reynolds transition or extrapolate. Review residual/flow bounds, capacity, upper-bound velocity and selected rerun. Source the equal pump-port elevation basis and fluid applicability. Only explicitly combined wire-to-water efficiency permits an electrical-input estimate; keep pump-only efficiency, nameplate rating, starting current and the separate electrical project distinct. Branch flow, controls, NPSH and complete acceptance remain pending.

To carry a passing pump estimate into a new electrical scenario and IFC properties, use docs/PUMP_ELECTRICAL.md. Bind actual source-port/pump GUIDs and the electrical device explicitly, replay source data and preserve the baseline load/hardware. Do not copy the operating estimate over the canonical design input or infer motor rating/PF from hydraulic power.
