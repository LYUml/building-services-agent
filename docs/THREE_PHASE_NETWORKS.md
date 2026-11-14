# Source-bound three-phase networks

Fresh explicit-runtime regression executes36numerical/source/IFC workflow
controls without skips. Both terminal receipts independently verify; the
existing pinned pandapower engine and isolated host are reused. This is bounded
synthetic evidence, not actual protection/product/code or project acceptance.
See [regression evidence](evidence/three-phase-regression-opt-in.json).

The passing workflow study can now feed [calculation-bound schematics and phase schedules](THREE_PHASE_DRAWINGS.md), including independently reopened DWG and reviewed PDF for the synthetic fixture. That standalone drawing path is separate from installation design, BIM topology and protection/regulatory acceptance.

This standalone adapter reuses pinned pandapower 3.5.6, selected through the [executed upstream trial](THREE_PHASE_TRIAL.md). It accepts connected single-voltage networks of sequence-impedance lines and constant-PQ wye loads with one external source. It supports multiple buses/loads/branches and has executed a three-bus radial fixture, a mesh control and nonzero inductive/capacitive reactive loads. It is not a general electrical design or protection tool.

```powershell
tools/pandapower-runtime/Scripts/python scripts/run_three_phase.py examples/three-phase-network/project.json --out runs/new-three-phase-network
tools/pandapower-runtime/Scripts/python -m unittest discover -s tests -p test_three_phase.py -v
```

Set up the isolated runtime with the exact platform-specific lock in THREE_PHASE_TRIAL.md. The adapter is registered as workflow kind `three_phase`; CAD/BIM binding remains pending. Do not run it with arbitrary model code from an assignment. Input is JSON only; engine calls remain original repository code.

## Requirement workflow

```powershell
.venv/Scripts/python -m bsa.cli workflow examples/three-phase-network/plan.json --out runs/new-three-phase-workflow --three-phase-python tools/pandapower-runtime/Scripts/python.exe --review runs/new-three-phase-review.json
```

The source-linked synthetic plan executes `{"id":"power-flow","kind":"three_phase","project":"project.json"}` and preserves full design review as a separate manual requirement. It therefore returns unresolved execution (exit 2) even when the numerical study passes. Use `requires_pass` for downstream consumers that must wait for this narrow study. Current/voltage target failure blocks them; missing `--three-phase-python` leaves the study and dependent tasks pending without creating study artifacts.

The main agent runtime invokes only the fixed repository runner, with a bounded 120-second subprocess, and retains process.log plus the native study/network. It verifies pinned runtime versions, adapter/source/model hashes, expected node/line inventories, the complete numerical checks with fixed tolerances, actual phase values versus targets and exit/status correspondence before recording `three-phase.json`. The report is evidence under a trusted local execution assumption, not authenticated third-party measurements. The plan's input inventory includes source records and repository runner/adapter/bridge bytes. The explicit interpreter hash is retained in the bridge report, not inferred from assignment text or embedded in plan commands.

Actual tests cover a passing study, a converged failed current target with blocked dependent review, absent runtime, exit 0 without artifacts, missing check inventories and contradictory residual/current/source/version reports. This integrates numerical study execution and source integrity; it does not make the manual design, protection, code or drawing review automatic.

## Input and source contract

[The complete example](../examples/three-phase-network/project.json) is an explicitly synthetic software fixture. Version 1 requires the exact model string `three-phase sequence-line constant-PQ wye` and these sections:

| Section | Declared inputs |
|---|---|
| `sources` | relative project-local file path, SHA256, nonempty locator and kind: course_given, measured, manufacturer, design_target or assumption |
| `supply` | source bus, line-line volts, frequency Hz, positive-sequence voltage pu and angle degrees, external source short-circuit/sequence parameters, source ID |
| `buses` | unique IDs, all connected to source |
| `lines` | unique IDs/from/to, length metres, positive/zero-sequence resistance/reactance ohm/km, maximum phase-current target A, impedance/length source ID and separate current-limit source ID |
| `loads` | unique IDs/bus, phase A/B/C electrical active kW and reactive kvar arrays, source ID |
| `voltage_limits` | explicitly sourced positive minimum/maximum phase-voltage pu study targets |

Active demand must be nonnegative with positive total; reactive demand may have either sign. No PF, demand factor, route length, impedance, equipment rating or regulatory limit is inferred. A physical neutral conductor and harmonic loading are not represented by the sequence model. Zero line shunt capacitance, negative-sequence impedance equal to positive sequence, scaling 1, no parallel-count multiplier/temperature correction and one common voltage level are explicit model scope. No delta loads, generation, transformers, switches or alternative device types are accepted through this schema. Do not map those systems into wye loads to force validation.

Source hashes and locators establish a declared file association, not that the values were interpreted correctly or the source is authoritative. Source kinds are retained in the report; an assumption is not promoted to a measurement. All project and generated files must stay in this repository; source files must stay under the project directory. Previous runs and source files are not overwritten.

## Actual execution and independent audit

The adapter builds with upstream APIs, saves `network.json`, reopens it through upstream `from_json`, solves and creates `study.json`. A failure after creating the run retains `failure.json` and no successful study report. `network.json` is the saved input model, not a claimed saved result or Revit/IFC deliverable. Source changes during execution prevent success output.

The audit checks the native bus/line/load/source parameters against the declared schema, exact row inventories, phase-domain line voltage equations reconstructed from sequence impedances, both-end current consistency, load-result PQ, every bus's complex KCL, complex line loss and total active/reactive power balance. All used upstream results must be finite. Numerical residual limits are fixed verification tolerances (1e-5 V/A and 1e-3 VA); native parameter comparisons use 1e-12 relative/absolute numeric tolerance. These are software verification tolerances, not physical installation tolerances or regulations.

The status is pass only when independent checks and every declared voltage/current target pass. A converged overload returns fail/exit 2 while retaining the actual numerical results. Design acceptance remains false even for a passing study. Result-corruption controls cover phase angle, active/reactive power, current, native line impedance, source sequence parameters, changed load type and nonfinite results. Disconnected buses, unknown fields, negative active generation, source tampering, source changes during solving and overwrite attempts are rejected.

Full regulatory applicability, actual source impedance/cable data, neutral/harmonic/protection/motor-starting studies, manufacturer selection, native electrical topology, drawing schedules and physical installation acceptance remain unresolved. Link these results to the complete requirement matrix and other tools before treating them as assignment evidence.

Lines may optionally declare length_source referencing an existing source record, separately from source (sequence impedance and other baseline data) and current_limit_source. Unknown length-source IDs fail validation. The saved-IFC derivation adapter in THREE_PHASE_IFC.md uses this field and preserves original source kinds; it never treats numerical geometry as certified site measurement.
