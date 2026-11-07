# Saved-model drawing execution evidence

Actual execution of `examples/water-riser/delivery-plan.json` in `runs/ifc-drawing-release-v3`. `workflow.json` records electrical, water sizing, saved-IFC clash and drawing tasks. Original run source/artifact byte-integrity verification passed before copying this selected evidence.

`source.ifc` is the actual saved selected model used by the drawing task. `drawing.json`, `segments.csv`, `segments.dxf` and `preview.svg` retain two hollow segment rows and two model-linked centreline entities. Both lengths are 2.5 m, with 32 mm bore and 40 mm outside diameter. Non-segment pump and terminal envelopes are explicitly excluded, not silently counted as drawn. The independent drawing adapter reopens the DXF and checks identities, coordinates, labels and counts.

`preview.png` is a real isolated headless Edge rendering of the generated SVG. It was visually inspected for readable separated labels and visible scope legend; artifact hashes and the limited review scope are recorded in `visual-review.json`. This is not native CAD, PDF, printed-scale or BIM-viewer acceptance.

`conflicting-metadata.json` retains an actual negative test where metre diameter properties contradict both saved hollow profiles. Both segment errors remain visible and no partial DXF was emitted. Reproduce using `tests/test_ifc_drawing.py`.

The regression log records enabled local engine tests. JSON paths/hashes refer to original ignored run locations; this selection is not a standalone complete run archive. Full installation details, equipment/fittings/insulation, native DWG/plotting, real product suitability and complete engineering acceptance remain pending.
