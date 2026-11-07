# Outside-joint clearance evidence

Synthetic selected circular-network IFC from `../circular-network/selected.ifc`, with the separately sourced policy in `examples/clash-local-policy.json`. No real assignment files are used.

`pass.json` and `pass.html` retain the 0.18 m joint-region checks: both directions for each of two connected pairs pass the conservative 0.05002 m proof threshold for a 0.05 m clearance requirement. Reported capped gap values are lower bounds, not exact distances. `not-proven.json` and its HTML retain the stricter check with the original 0.15 m radii, which does not pass. The original example policy is unchanged.

`workflow.json` records actual model production and saved-IFC QA execution. Report paths and artifact hashes refer to original ignored run directories; this selected evidence is not a standalone portable run archive. Reproduce using `examples/clash-local-plan.json`. Tests also exercise a connected return arm approaching a second location by 20 mm, explicit mask resolution validation and unchanged source IFC bytes.

These are numerical checks on QA meshes with synthetic policy settings. Source/product fidelity, applicable clearances, BIM-viewer inspection and complete engineering acceptance remain pending.
