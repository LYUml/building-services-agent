# Finite circular fan catalogue screening

The adapter composes existing native circular fan trials with the shared finite
screening loop extracted from `rectangular_fan_selection`. Both domains now use
the same candidate retention, declared preference, lexical tie break, unresolved
mechanical-priority and selected-rerun rules. There is no new pressure solver or
dependency. Rectangular numerical/native and published mechanical-table
regressions execute alongside the new circular screening tests.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/route-search/port-fan-selection-plan.json --out runs/new-circular-selection
```

The new source brief explicitly changes the single-curve input to a selected
catalogue curve, retaining the earlier geometry, material, pressure and minimum
duty obligations. The earlier single-curve example remains available. Workflow
kind `circular_fan_selection` inherits one passing `route_pressure` producer and
a local `catalogue`. A subsequent `circular_fan_operating_point` depends on the
selection and omits `curve`. A replacement curve or model is rejected.

The catalogue reuses the exact existing contract: objective `lowest declared
preference among passing candidates`, source text and 1..100 unique candidates
with `id`, `source`, finite `preference` and complete sourced total-pressure
`curve`. Lower preference ranks first, with lexical candidate ID breaking ties.
This is a declared ordering, not an inferred price, efficiency or motor-power
objective. Malformed curves reject before trials; valid but inapplicable curves,
such as a fluid mismatch, remain explicitly unsupported candidate results.

Every candidate is run on the same reconstructed native pressure scenario.
Converged insufficient airflow remains failed. All rejected records and trial
artifacts are retained. The preferred eligible curve is freshly rerun in
`selected/`; no feasible candidate means no selected folder. The source native
geometry, original minimum airflow, velocity and terminal-pressure requirements
are not modified to obtain a selection.

Optional `mechanical` data uses the existing sourced product record/PDF and
complete per-candidate class association contract from
[rectangular fan selection](RECTANGULAR_FAN.md). Published limits are evaluated
separately from numerical duty. An unresolved higher-priority mechanical identity
blocks selection, while known failed candidates stay rejected. Without that
optional source basis, the catalogue is numerical screening only. A declared
product/curve association is not authenticated manufacturer performance.

The independent selected operating consumer reconstructs every candidate from
the original catalogue, native pressure source and current methods. It rechecks
eligibility, preference, mechanical status, curve/operating-network equality and
saved analysis against a fresh solve. It verifies the source/artifact pins before
and after the independent operating rerun. Consumer outputs must stay outside
the immutable selection folder. Changed selection IDs, false capacity flags or
rehashed replacement curves cannot authorize a consumer.

Standalone APIs are `circular_fan_selection.run(pressure, catalogue, out)` and
`run_selected(selection, pressure, catalogue, out)`. The CLI screens an existing
pressure producer:

```powershell
.venv/Scripts/python -m bsa.circular_fan_selection runs/source-port-pressure-final-workflow/pressure --catalogue examples/route-search/circular-fan-catalogue.json --out runs/new-circular-selection
```

The public synthetic catalogue contains a preferred weak curve, an incompatible
fluid curve and a supported curve. Actual trials retain these results, select
`supported` and reproduce approximately 0.08029227424 m3/s in the independent
consumer. A no-feasible control blocks the consumer and drawing. See
evidence/circular-fan-selection.json for complete workflow outcomes, executed
source-tamper controls, method pins and regressions.

Curves, preferences and local geometry remain synthetic assumptions. Real
vendor curve accuracy, stable/installation applicability, actual fan body/ports,
flow metadata, motor electricity, multi-terminal balancing, native joined drawings
and full Hong Kong/engineering acceptance remain pending. Source screening does
not release a complete building-services design.
