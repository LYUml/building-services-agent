# Shared fixture geometry and photometry

`electrical_lighting` joins the existing electrical/geometry contracts to Radiance. Electrical data owns fixture IDs, XY, power and circuit. Geometry owns envelope bottom Z and the selected rectangular space. Optical input owns sourced IES assignments, world-axis offsets from electrical XY/envelope bottom Z, yaw, maintenance, reflectances, world sensor positions, targets and numerical settings. It cannot repeat fixture positions or electrical power.

```powershell
.venv/Scripts/python -m bsa.lighting_binding examples/office-electrical/project.json --geometry examples/office-electrical/geometry.json --optical examples/shared-lighting.json --out runs/bound-demo --radiance-bin tools/radiance-6/bin
```

Install optional BIM dependencies as well as the pinned Radiance engine. Output paths must be new. The source-linked `examples/shared-lighting-plan.json` also chains native AutoCAD conversion and an explicit pending manual review. Pass engine paths to workflow execute; absent engines remain pending.

Every selected-space IfcLightFixture must have exactly one optical assignment. Nominal IES input watts must match shared electrical watts within an explicitly sourced tolerance. Watts never determine candela. Maintenance scales the optical calculation only. Original IES bytes are copied without conversion and hashed. World positions are transformed into the selected room's local coordinate system; translated-room tests verify this transformation.

Outputs contain reconciled electrical calculations/DXF/IFC under `shared`, a derived lighting input, copied photometry, actual Radiance results and `lighting-binding.json`. The example's photometry and all geometry are synthetic. IFC envelopes are not automatically converted into optical obstructions. Physical optical reference points, manufacturer photometry, actual room geometry, sampling coverage and visual/code acceptance remain separate review gates. The example's native PDF has been generated but has not received a separate visual review.
