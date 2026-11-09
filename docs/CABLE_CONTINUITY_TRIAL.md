# Continuous cable native geometry trial

Executed 2026-11-10 using pinned IfcOpenShell 0.8.5 and the existing Manifold mesh validator. This is a synthetic geometry probe, not an engineering design or registered workflow capability.

`scripts/probe_cable_union.py --out <new repository directory>` creates a quarter-circle envelope (centreline radius 0.3 m, envelope radius 0.01 m) and a tangent 2 m straight, all explicitly assumed. The existing revolution probe supplies the first solid. Upstream `geometry.add_boolean` performs UNION; no custom triangles, mesh repair, contact waiver or tolerance widening is used. The independent expected centreline length is 2.471238898038469 m. Analytic volume, volume-weighted centroid and tight bounds are compared to the saved, reopened native tessellation using existing tolerances.

Actual execution: `runs/cable-union-probe-v1/probe.json`. IFC schema/EXPRESS validation, positive oriented single-connected-solid validation, volume, bounds and centroid checks passed. Measured volume was 0.0007763485753805562 m³. This establishes only this tangent union, not arbitrary routes or physical distribution joints.

Reuse: [official IfcOpenShell add_boolean API](https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/geometry/add_boolean/index.html). Existing repository upstream attribution/licenses remain applicable. The installed 0.8.5 lacks the documentation's suggested `validate_csg` helper; the probe explicitly assigns standard CSG representation and executes full saved schema/EXPRESS validation instead. No dependency was upgraded.

Pending: independent composite Axis, source-driven piece contracts, endpoint/tangent/profile checks, ports, saved electrical length extraction, bend-limit coverage, numerical/workflow integration, negative controls and visual review. The old multi-cable distribution-node clearance failure remains a failure: a loaded intermediate board cannot be replaced by an uninterrupted cable to hide missing hardware.
