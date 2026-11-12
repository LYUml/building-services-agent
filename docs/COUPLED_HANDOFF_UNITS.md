# Shared water, pump and electrical handoff

The separate optional native-DWG/plot supplement has now been executed and
visually inspected; see [native handoff](COUPLED_NATIVE_HANDOFF.md). The original
base trial below remains DXF-only and does not acquire retrospective acceptance.

The source-to-adapter handoff now has an authored shared-model case rather than
only independent discipline examples. The host interpretation binds seven source
paragraphs to water sizing/native IFC, clearance checks, fixed-speed pump solving,
electrical operating-load binding, revised-model checking and saved-IFC drawing.
The existing engineering engines and GUID/port correspondence are reused.

```
python scripts/run_coupled_handoff_demo.py --out runs/NEW_PROJECT
python scripts/run_coupled_handoff_demo.py --out runs/NEW_CONTROL --wrong-pump-identity
```

Original JSONs are copied into a separate archived source directory and working
inputs; hashes and the deliberate negative revision are retained. The script
contains an explicit host interpretation of this particular brief and rejects
changed passage text. It is not semantic interpretation of an arbitrary assignment.

## Explicit native property units

Previously the pump/electrical properties mainly expressed units in names. New
`pump_electrical` executions use typed measures and per-property units:

| Property category | IFC nominal type | Explicit property unit |
|---|---|---|
| Baseline/operating electrical and hydraulic kW | IfcPowerMeasure | POWERUNIT / WATT / KILO |
| Nominal voltage | IfcElectricVoltageMeasure | ELECTRICVOLTAGEUNIT / VOLT |
| Operating device current | IfcElectricCurrentMeasure | ELECTRICCURRENTUNIT / AMPERE |
| Flow | IfcVolumetricFlowRateMeasure | VOLUMETRICFLOWRATEUNIT, metre cubed per second |
| Pump total-pressure rise | IfcPressureMeasure | PRESSUREUNIT / PASCAL |
| Operating PF and wire-to-water efficiency | IfcRatioMeasure | Dimensionless; no unit entity |
| Device/circuit identity | IfcIdentifier | No unit |
| Scenario and source/provenance | IfcText | No unit |

The small `ifc_property_units` adapter uses the existing pinned IfcOpenShell API;
it does not implement a conversion or calculation engine. Native dependency import
is deferred until authoring. It inspects exact property coverage, nominal types,
values and SI/derived-unit signatures before and after save/reopen. Project unit
assignment and every original STEP entity remain unchanged. Existing scenario
namespaces are rejected rather than overwritten. New source/method pins include
the property adapter. Historical runs remain historical; regenerate them for the
new contract rather than changing their hashes.

The new `OperatingDeviceCurrent_A` is the bound device's single-phase steady
current from estimated input kW, explicit operating PF and source voltage. It is
not a nameplate, starting-current or final cable-selection value. The independent
0.75 kW baseline and all circuit hardware remain retained, even when the operating
estimate is lower. Baseline design failures still fail the combined result.

## Executed evidence and limits

[Evidence](evidence/coupled-handoff-units.json) records the actual positive and
wrong-identity runs, independent source reconstruction and IFC reopening. The
positive trial yields approximately 0.437828 electrical kW and 2.239527 A at the
explicit assumed PF 0.85 / 230 V, retaining the 0.75 kW baseline. Seven engineering
tasks pass; final review stays pending. Its same-model DXF has two saved 2.5 m pipe
segments, selected 32 mm bores / 40 mm outside diameters, and GUID links.

Replacing the declared pump GUID with its port GUID fails coupling and blocks
revised-model QA and drawing. Four separately saved corrupt IFCs remain schema
valid but fail the stronger property check: removed KILO prefix, missing power
unit, millisecond denominator on flow, and PF encoded as untyped IfcReal.
The original saved IFC is unchanged. Thirty-one related tests pass, including
these controls, source/gap preservation and existing baseline-hardware gates.

This is a synthetic declared curve/efficiency/PF/clearance scenario. Logical pump
identity and property coupling do not create the remaining electrical port system,
real equipment geometry or motor-protection design. Physical products/joints,
NPSH/controls, installation and full Hong Kong compliance remain pending. The
drawing is a schematic DXF: no new native DWG reopening/visual plot acceptance is
claimed. Original upstream attribution/licenses in the repository remain unchanged.
