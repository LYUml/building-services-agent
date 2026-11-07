---
name: mep-network-analysis
description: Calculate source-linked flow and pressure budgets for prescribed-demand circular air or water tree networks, including critical paths, local losses and elevation. Use for supported duct and pipe pressure calculations.
---

# Network pressure analysis

Read docs/NETWORKS.md before interpreting pressures. Use `python -m bsa.network <project.json> --out <new-run>` or the `network` workflow adapter. Install the optional network dependency. Source every flow, internal diameter, route length, roughness, fitting K, fluid property and allowable velocity/pressure. Do not derive a route length from unrelated coordinates or manufacture a regulation table value.

This adapter supports only connected directed trees with prescribed withdrawals, constant-density Newtonian fluid and fully filled circular sections. It rejects transitional Reynolds numbers and loops. Do not map a closed chilled-water loop, partially filled drain, pressure-dependent sprinkler network or rectangular laminar duct into it merely to obtain a result.

The pressure contract is total (static plus velocity), common-reference, with elevation potential separate. Convert a supplied static requirement only when velocity/basis are justified; otherwise retain it as unresolved. Level air examples do not validate vertical ambient/stack pressure treatment. Use fittings K referenced to each local segment velocity. Do not confuse a Darcy factor with a Fanning factor.

Review segment calculations and node margins, source-required pressure and critical path. Failed targets must remain failed or trigger a versioned design iteration. A passing budget does not prove passive flow splitting, balancing, a fan/pump operating point, motor electrical power, cavitation, acoustics or code compliance. Keep these gates explicit.

Keep IDs aligned with actual project schedules and models. The synthetic network fixtures are not automatically reconciled with the separate IFC ventilation fixture. Validate geometry binding and routing separately before claiming a coordinated MEP model.
