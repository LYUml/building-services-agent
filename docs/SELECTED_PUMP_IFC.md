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

The runner verifies the official PDF against the unchanged pinned pack, stages synthetic source files and a deliberately changed pump curve, and executes model → water binding → screen → new IFC → fresh combined checks / IDS → selected water solve. All seven stages passed the recorded native trial; source/artifact integrity passed. Evidence is in `docs/evidence/selected-pump-workflow` (the official PDF is not redistributed). Regression tests use clearly labelled synthetic source bytes instead of claiming official regulatory evidence and verify no-feasible blocking, input replacement rejection, retained GUIDs and changed source detection.

Current limitation: workflow inheritance requires a passing baseline water task; a hydraulically failed baseline is not yet an automatically recoverable iteration state. The standalone screener can retain failing baselines, but this workflow does not waive its parent gates. The source model's physical clashes remain unresolved, and no drawing release is included in this demonstration. Passing IDS only verifies the declared information fields; it does not certify the selected product or the source claims. Fresh scoped thermal/pipe checks do not establish full regulatory conformity.
