# Conditional TN source-envelope evidence

Actual execution of `examples/fault-plan.json` in `runs/fault-release`. The original source/task-artifact integrity check passed before copying this selected evidence. Original electrical inputs and completed coursework were not modified.

`source-data.json` contains all explicitly synthetic hot-loop, device, time-limit, maximum-fault, CPC and energy guarantees. It is not manufacturer data or a regulation table. `faults.json`, `checks.csv`, `report.html` and `workflow.json` retain actual results: hot loop R=0.8 ohm, X=0.054 ohm, minimum bolted L-PE current approximately 272.504905 A, independently supplied maximum 4000 A and synthetic standalone capacity 6000 A. The full interval fits the supplied total-clearing and energy guarantees.

The CPC supplied bound is 20000 A2s versus `(115*1.5)^2 = 29756.25 A2s`, giving approximately 1.229751 mm2 from the thermal bound alone. This is not a complete conductor selection or proof of mechanical minima, actual material/temperature conditions or applicable-code compliance.

`capacity-failed.json` and its input retain a real negative fixture: 4000 A source maximum exceeds the supplied 3000 A standalone capacity/coverage. `cpc-failed.json` retains a synthetic 1.0 mm2 CPC whose supplied energy criterion fails. `pending.json`, its data and `pending-workflow.json` retain an intentionally absent device guarantee: partial known values survive, but the automated task remains pending. Tests additionally cover all missing groups, uncovered voltage/current/time/energy conditions and a review assertion that cannot clear missing automatic fault evidence.

`regression.log` records full enabled local tests. Paths/hashes point to original ignored run directories; this is selected evidence, not a complete portable archive. All passes are conditional on explicit source assumptions. Actual source/code-edition/clause and product applicability, selectivity/overload, other conductor protection, earthing and full engineering acceptance remain pending; design_accepted is false.
