# Full-plan pump curve iteration

For bounded automatic comparison of an explicitly supplied curve catalogue
before this full-plan revision, use [pump catalogue iteration](PUMP_CATALOGUE_ITERATION.md).
It reuses the same solver and retains downstream failures and missing equipment facts.

The existing catalogue iteration orchestrator now also accepts a ready failed
`pump_operating_point` task and an explicit host-supplied replacement curve.
It reuses the existing single-terminal pump/system solver and fluids pressure
engine; it does not substitute the different EPANET circulation-pump catalogue
model or invent manufacturer points. Only the selected task's `curve` reference
changes. All requirements, dependencies, sources, unresolved inputs, baseline
electrical loads and engineering targets remain unchanged.

```powershell
python -m bsa.catalogue_iteration ORIGINAL_PLAN ORIGINAL_RUN --task PUMP_TASK --curve REPLACEMENT_CURVE --target FRESH_SIBLING_PLAN --out FRESH_RUN
python -m bsa.catalogue_iteration_verify FRESH_RUN
```

The Python API retains its historical `catalogue` parameter name for both input
types. CLI `--curve` and `--catalogue` are mutually exclusive aliases. The source
task kind determines the validated input contract. A replacement must be inside
the source plan tree and differ from the failed source. Preserve original data;
a new curve is an explicit engineering design choice, not an automatic approval.
Blocked upstream networks, missing source evidence, unsupported fluid/curve or
unchanged replacement inputs cannot start the recovery. Fresh output locations
and the existing host workspace/runtime controls apply.

Before changing the plan, the orchestrator reruns the old curve on the exact
original inherited network (or explicit direct network input) and compares the
failed operating result with the original report. It then builds a fresh common
requirements inventory, executes the complete revised plan and diagnoses its
dependencies. Verification reconstructs that failure from source, checks exact
curve-only plan modification, every original obligation and evidence pin, and
independently replays any passing selected pump report. Other failed tasks and
engineering review remain pending; no target is relaxed to make a result pass.

Run the public authored controls with:

```powershell
python scripts/run_pump_curve_iteration_demo.py --out runs/new-pump-recovery
python scripts/run_pump_curve_iteration_demo.py --out runs/new-weak-pump-recovery --still-weak
```

These explicitly synthetic controls archive the original example curve and make
a deliberately insufficient curve by scaling its pressure points by 0.65. The
positive replacement restores the supplied synthetic curve; the negative retains
the insufficient curve with distinct sourced control provenance. Neither is a
manufacturer product or real installed selection.

Actual positive execution reproduces the old failure, then passes all eight
existing water/electrical/IFC/DXF tasks. Coupled calculation retains the original
0.75 kW baseline and hardware, updates typed operating properties on the same
pump identity, and regenerates the dependent schematic. The negative keeps pump
failure and blocks coupled IFC, its QA and its drawing; no such output folders
are created. All eight source requirements survive both trials. Independent
verification passes, and removed-requirement/omitted-original-pin controls reject.
Twenty-six related tests pass, including a converged-but-insufficient direct
network baseline and preservation of an ordinary equipment-review gap. See [evidence](evidence/pump-curve-iteration.json).

This is an explicit source revision followed by automatic full-graph execution,
not autonomous catalogue search. Motor rating/start/protection, NPSH, real curve
and efficiency applicability, physical products, native DWG/plot acceptance and
complete Hong Kong/engineering review remain unresolved. An empty numerical
recovery queue is not acceptance. Older receipts pinned to previous methods or
scope must be rerun, not rehashed. No new dependency, solver or regulation clause
is added; existing upstream licenses and attribution remain unchanged.
