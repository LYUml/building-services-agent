# Hong Kong selected current-balance rule

An 18-case explicit-runtime check now passes without skips against the exact
pinned official BEC cache. It executes actual numerical studies, source-bound
phase-balance checks and IFC-derived workflow gates, including missing-basis,
exceeded-target and changed-source controls. The terminal receipt independently
verifies; full regulatory/design acceptance remains unestablished. See
[evidence](evidence/three-phase-hk-regression.json).

The [EMSD BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/BEC_2024_ENG.pdf) selected clause 7.6.3 applies to three-phase four-wire circuits with single-phase loads at a protective-device rating of at least 400 A, and sets a 10% current-unbalance limit at designed circuit current. Section 2 defines the percentage as maximum absolute deviation from the three-phase average, divided by that average, times 100. The design-current definition requires normal-service RMS design conditions. PDF pages 10 and 56 (printed pages 4 and 50) were visually inspected. This is a selected-clause implementation, not legal applicability advice or full electrical conformity.

The independent official [TG-BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/TG-BEC_2024.pdf), PDF pages 159–160, also discusses the selected clause, unbalance and harmonics. Its downloaded SHA256 is `2fce4b30773f1899635ee985876f418972fb3cacfccb176ba0df7283c4e61186`; it is supporting research, not an additional executable rule or a substitute for the primary code. Full PDFs and page renders remain in ignored repository runs.

## Source-pinned calculation binding

Pack `regulations/hk/phase-balance-2026.11.10/pack.json` reuses the existing generic jurisdiction evaluator. The original thin `bsa.three_phase_regulations` adapter derives phase-current unbalance from an actual saved numerical study and binds it to that pack. The formula stays in the calculation adapter; jurisdiction/source/clause/threshold/limit/applicability facts stay in pack data. Pack-defined applicability fact names are supported without changing the calculation engine. No new solver or regulatory engine is introduced.

```powershell
.venv/Scripts/python -m bsa.three_phase_regulations examples/three-phase-network/project.json --study runs/three-phase-native-workflow-v1/power-flow --basis examples/three-phase-network/hk-basis.json --pack regulations/hk/phase-balance-2026.11.10/pack.json --sources runs/hk-three-phase-sources --out runs/new-hk-phase-balance
```

The selected cached primary PDF must match SHA256 `9fae5eb2134caa7f5645735d618d82da0cf3f284e576a9f6402de9b8357f95b7`. Its filename is `emsd-bec-2024.pdf`. A missing or changed official PDF leaves standalone checks pending; workflow preflight requires the declared cached file to exist. The source/edition decision remains explicit; choosing a pack does not independently establish statutory scope or applicable dates. Select the new coverage snapshot `regulations/hk/coverage-2026.11.10-phase-balance.json` explicitly when this topic is required; older snapshots remain unchanged. The partial pack cannot clear other electrical or fire/HVAC/plumbing topics.

## Workflow prerequisite and repeatable scenarios

Workflow kind `three_phase_regulations` requires an earlier `three_phase` producer through `depends_on`, plus `basis`, `pack` and a relative plan-local `sources` directory. The numerical project and result are inherited; replacement project/current inputs are rejected. Original basis documents, official PDF and calculation code enter source integrity tracking. Put the rule task in the drawing's `requires_pass`. Direct and transitive rule gates must refer to the exact same numerical producer as the drawing, and modified rule/study artifacts block authoring. Missing model basis or selected-limit exceedance prevents a pass; it cannot be cleared by an unrelated calculation's rule result.

```powershell
.venv/Scripts/python scripts/run_hk_three_phase_demo.py --source runs/hk-three-phase-sources/emsd-bec-2024.pdf --python tools/pandapower-runtime/Scripts/python.exe --graphviz tools/freecad-1.1.4/FreeCAD_1.1.4-Windows-x86_64-py311/bin/dot.exe --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe' --out runs/new-regulated-three-phase-suite
```

The runner stages source-linked synthetic briefs/plans for conditional pass, in-scope unbalance exceedance and missing design-current basis. Actual execution generated native DWG/PDF only for the conditional-pass scenario; the other two retained pending rule checks and no drawing artifacts. The positive PDF was rendered and visually inspected separately. Coverage planning finds the selected scheduled rule but preserves `partial_rule_coverage`, and other topics stay unresolved. `expected_behaviors_pass` describes observed software behavior, not design acceptance or automatic statutory-check discovery. Model/limit definitions must be reviewed before replacing this rule pack for another region; not every current-unbalance convention uses this formula.

The basis requires exact circuit/line coverage, source file hashes/kinds/locators, edition decisions, a separate sourced protective-device rating and sourced circuit classifications. Missing data can remain pending; phase-current and percentage overrides are rejected. The input schema is illustrated in `examples/three-phase-network/hk-basis.json`. `design_normal_service_rms_confirmed` and `sinusoidal_design_model_applicable` are mandatory model prerequisites: a fundamental-frequency network result is not automatically a real RMS design-current assessment where harmonics or a different operating condition matter. The adapter does not verify those assertions in the physical installation.

The network's `max_current_a` field remains a study target and is never used as protective-device rating. Unknown protective rating does not default to that target. A zero average current produces no defined percentage and cannot pass by being assigned zero unbalance. Outside-scope circuits remain `not_applicable`; if none is applicable, supported checks do not become true automatically. Exceedance remains `review_required`, which prevents a supported pass. Even a passing selected rule cannot clear failed numerical-study targets, and a numerically unverified study is rejected.

## Executed evidence and limits

The official-PDF-backed synthetic fixture assumes 400 A feeder/63 A branch classifications solely for software testing. Those are not selected devices and do not establish valid protection against the example's separate 100 A study target. Its feeder has approximately 0.87% unbalance and passes the selected conditional check; its branch has approximately 50.01% but falls outside the selected protective-rating path. Other requirements remain unresolved, and `regulatory_compliance` stays `not_established` with design acceptance false.

Eight targeted tests cover the formula, inclusive rating/percentage boundaries, source tampering, missing basis, false waveform applicability, metric override rejection, pack-defined fact names and preserving failed study targets. Four existing schematic tests also pass after extending saved-study inspection to allow diagnostics on target-failed but numerically verified studies; drawing still requires targets to pass. No harmonic, physical neutral, TPF/THD, protection coordination or full installation acceptance is claimed.

The same-study rule now also consumes the registered three_phase_ifc_project producer. Its project/study paths resolve to the newly derived project and fresh solve together. Actual IFC-driven stale-length scenarios and native drawing are documented in THREE_PHASE_IFC.md. The declared protective-device/RMS/model basis remains separate and conditional; geometry derivation does not supply or validate those facts.
