# Independent water-riser execution evidence

Produced by the source-linked `examples/water-riser/plan.json` with existing unchanged adapters. All inputs are synthetic; the original completed coursework remains untouched.

`workflow.json` records electrical, water-model sizing and saved-IFC QA execution. `model-design.json`, `candidates.csv` and `water-analysis.json` retain the baseline, all four size choices and selected D32 result. `selected.ifc` is the actual saved revision with two vertical hollow pipe bodies and preserved equipment/port identities. `clash.json` retains four-body coverage and three conservative outside-joint proofs. `electrical.json` and `electrical.dxf` are the separate steady-load result and generic three-device metre overlay. They are not a water-riser drawing or proof of pump efficiency/operating point.

`negative-network-input.json`, `negative-model-design.json` and `negative-workflow.json` retain an actual 140 kPa supply variant: no feasible size, preserved baseline and dependent QA pending. Both original run directories passed workflow byte-integrity verification before archiving. Paths and artifact hashes in the JSON refer to those original ignored run directories; this selected evidence is not a standalone complete run archive. Reproduce the positive case with the example plan and the negative case with the integration test.

`regression.log` records full local tests with actual optional AutoCAD, EnergyPlus, Radiance and OCR adapters enabled. Numeric geometry/calculation evidence does not replace source/product, native plotting, BIM-viewer or complete engineering acceptance.
