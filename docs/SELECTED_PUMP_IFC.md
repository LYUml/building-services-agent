# Selected pump curve back to saved IFC

`bsa.selected_pump_ifc` accepts --producer (water_binding output), --screening (circulation_pump_design output), --template, --binding, --catalogue and a new --out directory. Screening must have consumed that exact producer network-input.json. Unrelated hydraulic inputs, different source identities and modified producer/screening artifacts are rejected before output is created.

The adapter preserves original files, copies the IFC, and adds BSA_ScreenedPumpCurve to the bound pump GUID with candidate ID, explicit m3/s/metre curve JSON, source and screening-report hash. A reserved existing property set is rejected instead of overwritten. It generates a new hydraulic template by changing only the selected curve/source, then reopens the IFC and performs fresh geometry-bound EPANET analysis. The rebound physical hydraulic input must equal the screened selection after removing provenance strings. Existing equipment and port identities are preserved.

This is a hydraulic curve/property revision, not replacement of the manufacturer's physical pump geometry. Shape, speed, efficiency, motor, NPSH, connector/product compatibility, clash and visual acceptance remain pending. Thermal/regulatory checks were made on the screened numeric scenario; final combined delivery checks on the new producer remain explicit. The standalone adapter is also available through the source-linked workflow described below.

Evidence in docs/evidence/selected-pump-ifc retains an official-BEC-backed synthetic screen and native IFC rebound. The integration test also exercises a genuinely changed synthetic curve, unchanged original IFC hash and stable equipment/port GUIDs, plus rejection of a different catalogue source identity. No real product suitability or full engineering acceptance is claimed.


## Source-linked workflow

`circulation_pump_design` may use `depends_on` referencing an earlier passing `water_coordination` instead of an explicit `project`. The saved model/native artifact bundle is reverified and its geometry rederived before and after screening. The actual derived `network-input.json` is the screening source; replacement project input is rejected. Catalogue validation happens against that derived network at execution, since the geometry template intentionally lacks the derived dimensions.

`selected_pump_ifc` takes only its `depends_on` screening task and optional ordinary gates. The screening must itself inherit `water_coordination`. Template, binding and catalogue identities are inherited; explicit replacements are forbidden. A failed/no-feasible screen produces no revised IFC. The existing standalone revision adapter verifies the original saved model, screening artifacts and selected physical scenario before and after native rebind.

The resulting `selected-model.ifc` is registered as an IFC producer for `ids_check` and other existing consumers. `ifc_circulation_checks` can depend on `selected_pump_ifc`: it reads that task's `rebound` producer and `selected-template.json`, inherits the original binding, and freshly runs thermal/scoped pipe checks on the reverified revised model. Downstream `water_network` may also inherit the screen, verifying the same derived baseline and selected source identity.

Run the complete synthetic demonstration with:

```powershell
.venv/Scripts/python scripts/run_selected_pump_workflow.py --bec-pdf runs/hk-regulation-sources/emsd-bec-2024.pdf --out runs/new-selected-pump-workflow
```

The runner verifies the official PDF against the unchanged pinned pack, stages synthetic source files and a deliberately changed pump curve, and executes model â†’ water binding â†’ screen â†’ new IFC â†’ fresh combined checks / IDS â†’ selected water solve. All seven stages passed the recorded native trial; source/artifact integrity passed. Evidence is in `docs/evidence/selected-pump-workflow` (the official PDF is not redistributed). Regression tests use clearly labelled synthetic source bytes instead of claiming official regulatory evidence and verify no-feasible blocking, input replacement rejection, retained GUIDs and changed source detection.

Default inheritance requires a passing baseline. Explicit verified target-failure iteration is now supported as described below. The source model's physical clashes remain unresolved, and no drawing release is included in this demonstration. Passing IDS only verifies the declared information fields; it does not certify the selected product or the source claims. Fresh scoped thermal/pipe checks do not establish full regulatory conformity.


## Iterating a verified target-failing baseline

Set `allow_failed_baseline: true` on inherited `circulation_pump_design` only when the plan intentionally asks to investigate alternatives to the failed baseline. This is not a generic failure override. The adapter verifies the saved IFC geometry and native artifact bundle, then reevaluates recorded raw EPANET results against the derived input. Only pressure-target, delivery-target or velocity-limit failures qualify. Engine cleanliness, input serialization, finite values, mass/energy identities, fixed heads, demand law, curve domain/head/status and circulation conditions must pass. Unknown/missing checks, engine errors, source changes and geometry failures cannot qualify.

The baseline task remains `fail`; a `baseline_recovery` record pins geometry/raw hashes and the exact failed targets in the screening report. Candidates and selected reruns still need all ordinary hydraulic, thermal and scoped regulatory checks. New IFC revision/combined checks/IDS proceed only after a passing selection. If `requires_pass` explicitly includes the failing baseline, that gate takes precedence and screening stays pending.

`bsa.workflow_status` independently rechecks the baseline evidence before diagnosing a passing recovery screen. It reports the iteration baseline separately without declaring the original failure resolved. Aggregate `execution_pass` and design acceptance remain false for a workflow retaining that failed task; final acceptance needs an appropriately scoped new delivery plan and actual engineering evidence, not edited statuses.

Reproduce the official-PDF-backed synthetic case by adding `--target-failure-baseline` to `scripts/run_selected_pump_workflow.py`. The explicit software-test velocity target is 1.3 m/s, not a regulation or manufacturer limit. Native baseline velocity is approximately 1.397 m/s; the supplied revised synthetic curve yields approximately 1.242 m/s and passes the selected downstream checks. The runner exits nonzero because the original baseline remains failed. Evidence: docs/evidence/pump-target-recovery. Regression controls retain the ordinary strict gate and reject raw numerical errors even after report/check hashes are refreshed.
