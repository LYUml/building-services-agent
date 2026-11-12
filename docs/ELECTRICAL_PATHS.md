# Source-bound electrical voltage-drop paths

An explicit independent-phase grouping extension now reuses this same-phase
calculator without changing original labels, loads or hardware. It requires
dedicated returns, exact coverage and separate feeder/non-origin identities;
shared-neutral/phasor coupling remains unsupported. Read
[the executed HK handoff](COUPLED_HK_ELECTRICAL.md). The original default method
and its same-phase restriction below remain unchanged.

The branch electrical engine does not represent the route from installation origin through distribution feeders. `bsa.electrical_paths` adds an explicitly declared single-phase radial feeder tree, computes each feeder current from all attached downstream circuit design currents once, and sums feeder plus branch voltage drops for each terminal circuit.

```powershell
.venv/Scripts/python -m bsa.electrical_paths examples/electrical-paths/project.json --topology examples/electrical-paths/topology.json --basis examples/regulations-hk/project.json --out runs/new-electrical-paths
```

The topology declares the installation origin, sourced feeder endpoints/lengths/full single-phase mV/A/m coefficients, and the supplying node for every circuit. Coefficients must already include the applicable single-phase return-path convention; the tool applies no extra factor of two. All circuits must be on the same phase. A node has one incoming feeder, every circuit has exactly one path to the declared origin, and every feeder must serve represented loads. Cycles, parallel feeds, omitted circuits, unused feeders and mixed phases are rejected. It does not infer connections or lengths from CAD and cannot prove the declared origin or actual building load inventory is complete.

The method uses nominal-voltage scalar currents from the existing electrical engine, sums simultaneous branch demand currents without further feeder diversity, and applies mV/A/m Ãƒâ€” A Ãƒâ€” m / 1000 per segment. Every branch load is conservatively lumped at its declared terminal route length. Coefficient, load simultaneity and branch-length applicability remain engineering inputs; this is not a phasor/load-flow, three-phase, neutral or motor-starting solver. Branch protection/ampacity failures remain in the output. Feeder protection and ampacity are not evaluated.

`electrical-paths.json` records inputs and per-feeder/per-circuit values. `regulation-projects.json` contains one project basis per circuit with its numeric full-path metric replaced by the computed result and a hash-bound report reference. The supplied regulatory basis applies to every represented terminal: its normal-service, fixed-equipment, full-path and edition decisions are retained rather than inferred or set true. Use separate appropriate bases for heterogeneous applicability. The binding does not independently authenticate those assertions. Pass each project object to `bsa.regulations.evaluate` with the selected pack and official cache. This standalone path module supplies bound inputs; for direct execution from original sources use the integrated task below. Imported result-file replay remains pending; explicit task prerequisites are available as described in WORKFLOWS.md.

The synthetic two-branch example independently gives shared feeder current 15 A, secondary feeder current 10 A and total drops 4.4 V / 2.3 V at 230 V. With the shared feeder increased from 30 m to 300 m, branch checks still pass but both full-path checks require review under the selected Hong Kong pack. Actual source-pinned rule evaluation and test evidence are retained in `docs/evidence/electrical-paths`. No cable coefficient, route or rating in this example is measured or an official tabulated value. Complete regulation, topology, product and engineering acceptance remain pending.

## Integrated calculation and rule task

```powershell
.venv/Scripts/python -m bsa.electrical_regulations examples/electrical-paths/project.json --topology examples/electrical-paths/topology.json --basis examples/regulations-hk/project.json --pack regulations/hk/2026.11.08/pack.json --sources runs/hk-regulation-sources --out runs/new-electrical-regulations
```

This adapter recalculates original electrical/topology sources and binds each circuit's metric directly from that invocation's in-memory result. It accepts no supplied calculation-result file. The project basis retains edition/applicability assertions, while its prefilled numeric metric is replaced. Original input and actual official-file hashes are checked across execution. Missing sources remain pending in the standalone command; workflow preflight requires downloaded source files.

Use workflow kind `electrical_regulations` with `project`, `topology`, `basis`, `pack`, and `sources` paths under the plan directory. A failed branch check makes the task `fail` even if its selected regulation check passes. Unresolved rule paths make it `pending`; only passing branch and selected rule checks make it `pass`. CLI exit 2 preserves unresolved/failed reports. Use requires_pass on a downstream task to explicitly require this check before authoring; no prerequisite is inferred for independent tasks. The adapter does not authenticate actual site topology, check feeder protection or establish full conformity. Evidence: `docs/evidence/electrical-regulations`.
