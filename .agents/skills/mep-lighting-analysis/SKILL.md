---
name: mep-lighting-analysis
description: Run IES-backed Radiance direct and reflected sensor illuminance calculations with numerical-stability checks for supported rectangular rooms and downlights. Use for electric-light photometric analysis.
---

# Lighting analysis

Read docs/LIGHTING.md. Use `python -m bsa.lighting <project.json> --out <new-run> --radiance-bin <bin>` or the lighting workflow adapter. Install the pinned engine with scripts/setup_radiance.py on Windows. Discover actual engine/tool availability; missing binaries are pending, not simulated success.

Require source-linked IES files, room geometry/reflectances, fixture positions/orientation, maintenance factors, sensor grid and targets. Do not derive candela or lumens from electrical watts. The repository IES example is synthetic and must never be presented as measured or manufacturer data. Current adapter supports Type C LM-63-2002 TILT=NONE, rectangular diffuse rooms and untilted downward luminaires only; unknown scene inputs are rejected.

Trace both direct and reflected light with the real engine. Review the verification run at increased bounces/divisions and preserve a failed stability/target check. Recorded parameter stability does not prove a room's geometric fidelity or a regulatory sampling method. The reported mean is over supplied sensors; do not call it task-area average unless coverage/weighting is justified.

For shared electrical/CAD/IFC projects, read docs/LIGHTING_BINDING.md and use `bsa.lighting_binding` or the `electrical_lighting` workflow adapter. Keep IDs/XY/power in electrical data, envelope heights in geometry and explicit world-axis photometric offsets in optical input. Never infer the emitting origin from an envelope without a source. Require nominal IES/electrical watts reconciliation and preserve original photometry bytes.

Inspect original room, obstruction and luminaire details, numerical outputs and source hashes. Preserve unresolved daylight, glare, emergency lighting, furniture, spectral colour and code checks. The binder supports one rectangular selected space; IFC envelopes do not automatically become optical obstructions. Never claim full lighting acceptance from a passing synthetic point-grid test.
