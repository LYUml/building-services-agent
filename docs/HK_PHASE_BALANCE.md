# Hong Kong selected current-balance rule

The [EMSD BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/BEC_2024_ENG.pdf) selected clause 7.6.3 applies to three-phase four-wire circuits with single-phase loads at a protective-device rating of at least 400 A, and sets a 10% current-unbalance limit at designed circuit current. Section 2 defines the percentage as maximum absolute deviation from the three-phase average, divided by that average, times 100. The design-current definition requires normal-service RMS design conditions. PDF pages 10 and 56 (printed pages 4 and 50) were visually inspected. This is a selected-clause implementation, not legal applicability advice or full electrical conformity.

The independent official [TG-BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/TG-BEC_2024.pdf), PDF pages 159–160, also discusses the selected clause, unbalance and harmonics. Its downloaded SHA256 is `2fce4b30773f1899635ee985876f418972fb3cacfccb176ba0df7283c4e61186`; it is supporting research, not an additional executable rule or a substitute for the primary code. Full PDFs and page renders remain in ignored repository runs.

## Source-pinned calculation binding

Pack `regulations/hk/phase-balance-2026.11.10/pack.json` reuses the existing generic jurisdiction evaluator. The original thin `bsa.three_phase_regulations` adapter derives phase-current unbalance from an actual saved numerical study and binds it to that pack. The formula stays in the calculation adapter; jurisdiction/source/clause/threshold/limit/applicability facts stay in pack data. Pack-defined applicability fact names are supported without changing the calculation engine. No new solver or regulatory engine is introduced.

```powershell
.venv/Scripts/python -m bsa.three_phase_regulations examples/three-phase-network/project.json --study runs/three-phase-native-workflow-v1/power-flow --basis examples/three-phase-network/hk-basis.json --pack regulations/hk/phase-balance-2026.11.10/pack.json --sources runs/hk-three-phase-sources --out runs/new-hk-phase-balance
```

The selected cached primary PDF must match SHA256 `9fae5eb2134caa7f5645735d618d82da0cf3f284e576a9f6402de9b8357f95b7`. Its filename is `emsd-bec-2024.pdf`. A missing or changed official PDF leaves checks pending. The source/edition decision remains explicit; choosing a pack does not independently establish statutory scope or applicable dates. The new pack is not yet added to the older regulatory-coverage snapshots or registered as a workflow task, so retain it and all remaining requirements explicitly when planning.

The basis requires exact circuit/line coverage, source file hashes/kinds/locators, edition decisions, a separate sourced protective-device rating and sourced circuit classifications. Missing data can remain pending; phase-current and percentage overrides are rejected. The input schema is illustrated in `examples/three-phase-network/hk-basis.json`. `design_normal_service_rms_confirmed` and `sinusoidal_design_model_applicable` are mandatory model prerequisites: a fundamental-frequency network result is not automatically a real RMS design-current assessment where harmonics or a different operating condition matter. The adapter does not verify those assertions in the physical installation.

The network's `max_current_a` field remains a study target and is never used as protective-device rating. Unknown protective rating does not default to that target. A zero average current produces no defined percentage and cannot pass by being assigned zero unbalance. Outside-scope circuits remain `not_applicable`; if none is applicable, supported checks do not become true automatically. Exceedance remains `review_required`, which prevents a supported pass. Even a passing selected rule cannot clear failed numerical-study targets, and a numerically unverified study is rejected.

## Executed evidence and limits

The official-PDF-backed synthetic fixture assumes 400 A feeder/63 A branch classifications solely for software testing. Those are not selected devices and do not establish valid protection against the example's separate 100 A study target. Its feeder has approximately 0.87% unbalance and passes the selected conditional check; its branch has approximately 50.01% but falls outside the selected protective-rating path. Other requirements remain unresolved, and `regulatory_compliance` stays `not_established` with design acceptance false.

Eight targeted tests cover the formula, inclusive rating/percentage boundaries, source tampering, missing basis, false waveform applicability, metric override rejection, pack-defined fact names and preserving failed study targets. Four existing schematic tests also pass after extending saved-study inspection to allow diagnostics on target-failed but numerically verified studies; drawing still requires targets to pass. No harmonic, physical neutral, TPF/THD, protection coordination or full installation acceptance is claimed.
