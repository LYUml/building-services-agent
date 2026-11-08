# Conditional TN fault verification

`electrical_fault` adds source-backed bolted-earth-fault loop, standalone breaking-capacity and CPC adiabatic proof checks to the existing single-phase electrical data. It is a conditional verification adapter, not a default breaker selector or a complete electrical design certificate.

```powershell
python -m bsa.workflow execute examples/fault-plan.json --out runs/tn-faults
python -m bsa.workflow verify runs/tn-faults
# Standalone:
python -m bsa.electrical_fault electrical.json --faults fault-data.json --out runs/fault-only
```

The workflow task takes `project` and `faults`. Both refer to common circuit IDs; voltage, breaker current and one-way route length come from the existing electrical project. Every circuit needs exactly one fault row. No course-specific numbers, B/C/D trip multipliers, disconnection limits, voltage factors, k factors or material tables are embedded.

## Explicit input assumptions

The model declaration is `TN bolted-fault final-circuit source-envelope verification`. Supply voltage is explicitly declared phase-to-earth U0. Both phase and CPC follow the project one-way route length. This is a negligible-fault-impedance, lumped series R/X TN model; it does not establish the actual earthing system or model TT/IT, RCD operation, arcing faults, parallel return paths or a full sequence-network study.

The root fault data supplies source descriptions and a row for every circuit. Each row has a source and six separately sourced groups. A complete group or an explicit `null` is required; null means unknown, not zero or a successful check:

| Group | Required meaning |
|---|---|
| loop | external maximum/hot-case L-PE R/X; hot phase and CPC ohms per metre; **combined-loop** reactance per metre of one-way route; minimum voltage factor |
| device | source device current rating matching the circuit; nominal-system voltage range; standalone breaking capacity; lower current and upper fault-current bounds for a guaranteed **total** clearing-time envelope |
| limits | sourced required maximum disconnection time |
| max_fault | independently supplied maximum prospective RMS fault at the protective device, covering all relevant fault modes/conditions |
| cpc | explicit section in mm2, adiabatic k in A sqrt(s)/mm2 and maximum sourced adiabatic time applicability |
| energy | guaranteed maximum complete let-through integral in A2s over the entire stated fault-current interval |

See examples/fault-data.json for exact field names and synthetic sources. Device voltage bounds refer to nominal-system applicability, not instantaneous fault voltage. The device/energy source must also cover the declared minimum-voltage and maximum-prospective cases, waveform/X/R, duty and installation conditions. This source applicability is not inferred from current rating or a product-family name. Breaking-rating type/duty and the chosen required time/k must be traced to the actual applicable source/code edition before real use. No cascading/backup rating is substituted for standalone capacity.

The maximum fault input is **not** obtained from the minimum L-PE loop. It must include the relevant worst cases at the protective-device position. Conversely, a large upstream maximum current does not prove far-end automatic disconnection. Inconsistent minimum/maximum envelopes fail the data check.

## Calculations and dispositions

Hot loop resistance is external R plus route length times the sum of phase/CPC resistance per metre. Reactance is external X plus route length times the supplied combined-loop reactance per metre. Minimum bolted earth-fault current is `c_min * U0 / abs(R + jX)`. The source trip threshold also gives a conditional maximum loop magnitude `c_min * U0 / I_a`. Source voltage factor and impedance conditions must represent a coherent minimum-current case.

Standalone breaking capacity is compared with the separately supplied maximum prospective current only within the source device voltage applicability. Automatic disconnection is proven only if the full minimum-to-maximum interval lies inside the guaranteed clearing envelope and its total clearing-time upper bound is no greater than the sourced required time. An uncovered interval or insufficient upper-time guarantee stays **unverified/pending**; the tool does not invent a thermal curve or claim an actual measured trip time/failure.

CPC capacity is `(k*S)^2`. The required section from the supplied energy bound is `sqrt(I2t_max)/k`. Comparison is made only when device/current/energy/time applicability is covered. The energy bound must cover the **whole relevant current interval**, not just one high-current point. No prospective-current-squared-times-clearing-time approximation is substituted for manufacturer let-through energy, particularly for current-limiting devices. This thermal result does not include mechanical minimum section, installation arrangement, material/temperature proof, phase/neutral thermal protection or complete earthing design.

Boolean false means a defined criterion failed (for example insufficient standalone capacity, insufficient CPC energy capacity under the supplied bound or an inconsistent fault envelope). Unknown data/applicability gives null and pending. Known failures take precedence over pending items. The original load/ampacity/drop checks must also pass for overall conditional success. No protection hardware or source project file is changed automatically. `design_accepted` stays false; actual source/code review, selectivity, overload conventions, other conductor protection and full design acceptance remain pending.

Outputs are faults.json, checks.csv, report.html and source/artifact hashes. Workflow status is pass/fail/pending; pending/failed CLI runs return 2 while preserving available evidence. Delivery review cannot clear a pending automated fault task by a plain pass assertion.

## Synthetic evidence

The explicit test fixture uses 20 m one-way route, R=0.8 ohm and X=0.054 ohm, giving approximately 272.504905 A at the stated reduced voltage. Its independently supplied maximum is 4000 A, compared with a synthetic 6000 A standalone capacity. A declared 60..6000 A total-clearing guarantee of 0.1 s fits the synthetic 0.4 s target. These are test assumptions, not manufacturer or regulation data.

The supplied 20000 A2s energy bound compares with `(115*1.5)^2 = 29756.25 A2s`; the thermal bound alone gives approximately 1.229751 mm2. Do not present that value as a complete CPC selection. Tests cover independent complex/resistive calculations, inclusive boundaries, every missing group, uncovered guarantees, insufficient capacity/section, contradictory current envelopes, invalid/foreign-rating sources, pending review and artifact tampering.

Method references: Schneider Electric's [TN system principle](https://www.electrical-installation.org/enwiki/TN_system_-_Principle), [circuit-breaker characteristics](https://www.electrical-installation.org/enwiki/Other_characteristics_of_a_circuit-breaker), and [short-circuit thermal withstand](https://www.electrical-installation.org/enwiki/Verification_of_the_withstand_capabilities_of_cables_under_short-circuit_conditions), plus Siemens' [miniature circuit-breaker primer](https://cache.industry.siemens.com/dl/files/304/109482304/att_866617/v1/MiniatureCircuitBreakers_primer_EN_201601250852395217.pdf). These support the method, not the fixture's values or any current jurisdiction-specific compliance claim.
