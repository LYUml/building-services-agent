# Pump, electrical and IFC operating scenarios

New native scenario properties now use explicit typed measures/units, including
operating device current, with saved type/unit/scale checks. Original project
units remain unchanged. See [shared handoff and units](COUPLED_HANDOFF_UNITS.md)
for the executed source-to-task workflow, positive/wrong-identity runs and controls.

`pump_electrical` explicitly binds a passing pump operating point to an electrical device and a saved IFC pump. It preserves the original electrical project, baseline load assumptions and all circuit hardware. A separate operating scenario and property-only IFC revision carry the derived input power; neither is a motor rating or a new cable-selection basis.

```powershell
python -m pip install -e ".[network,bim,clash]"
python -m bsa.workflow execute examples/water-riser/coupled-plan.json --out runs/coupled
python -m bsa.workflow verify runs/coupled
```

The eight-task example calculates baseline electrical loads, sizes/reconciles the water model, checks/draws the saved IFC, solves the pump operating point, binds its power, then rechecks/draws the revised IFC. The original completed coursework is not an input. The pump method remains limited to the separately declared boundary/curve scope in PUMPS.md.

## Identity, evidence and geometry

The task requires `project` (baseline electrical), `network_binding`, `link`, an earlier `pump_operating_point` `depends_on`, and an earlier supported IFC producer `ifc_from`. Nonpassing pump/model producers leave binding pending. It emits `model.ifc`, which is registered for subsequent IFC checking/drawing tasks. The standalone CLI also accepts explicit report/model inputs:

```powershell
python -m bsa.pump_electrical electrical.json --pump-report pump-run/pump.json --ifc selected.ifc --network-binding binding.json --link link.json --out runs/bound
```

The link supplies source text, electrical device ID, actual pump and outlet-port GUIDs, explicit operating power factor, a positive position tolerance at most 0.01 m, and exact load/position basis declarations. The required load basis is `steady operating estimate; retain baseline design load and hardware`. The position basis is `electrical XY equals pump body bounding-box centre`. This is an explicit symbol-placement convention, not a measured motor centre. Actual pump body geometry is read through IfcOpenShell; matching centre XY and a real connected SOURCE port are required.

The source outlet must belong to an IfcPump, match the mapped network supply node and connect to the first mapped segment's SINK port. The saved IFC must have explicit metre units and unambiguous distribution element names/GUIDs. Existing network reconciliation independently checks saved segment lengths, diameters, elevations and world endpoints. Similar names, a nearby unrelated pump or disconnected coincident geometry are insufficient.

The pump report must contain explicit network/curve input roles, recorded hashes and complete selected-state artifacts. Older reports without roles must be rerun. All recorded source/artifact bytes and the pinned fluids version are checked. The original network/curve calculation is replayed; source metadata, selected point, root bounds/checks and saved operating input must agree. The adapter uses the replayed power, rather than trusting a report scalar. Missing combined wire-to-water efficiency, failed pump checks, changed artifacts or contradictory metadata stop binding.

## Retained baseline and operating state

The baseline project is calculated independently and remains unchanged. The new `operating-electrical.json` changes only the explicitly bound device's electrical kW, supplied operating PF and provenance, plus the scenario name/source register. Other devices, positions, circuit assignments and all breaker/ampacity/route/drop/demand parameters are retained. Both scenarios generate their own calculations and DXF overlays. The operating current is conditional on the supplied PF and the existing single-phase voltage contract; it is not starting/nameplate current. Raw electrical-engine `design_current_a` fields in this operating scenario are steady scenario currents, not design-rating validation.

The IFC revision adds a separate `BSA_PumpElectrical` property set: electrical device/circuit identity, baseline electrical input, operating electrical input/PF, nominal voltage, flow, pump-added pressure, hydraulic kW, combined efficiency and hash-bound provenance. Every existing STEP entity must remain unchanged after save/reopen; identities, geometry, ports and original property sets are preserved. The new saved properties, network reconciliation and schema/EXPRESS validation must pass. An existing reserved property set is not silently overwritten: rebuild a new revision from the retained canonical source inputs.

This stage binds only the selected pump. Other electrical IDs remain explicitly listed as unbound. Circuit identity in the new property set does not create an electrical distribution system or port topology in the hydraulic IFC. Cross-domain properties are not a complete coordinated electrical model.

The synthetic case retains the 0.75 kW baseline and approximately 3.836 A baseline current. Its pump estimate yields approximately 0.437828 kW and 2.239527 A with explicitly assumed PF 0.85 at 230 V. The 10 A breaker and all cable coefficients remain unchanged. A negative 3 A breaker fixture fails the baseline check even though its lower operating current passes; overall binding remains failed. The tool never lowers hardware requirements to make an operating estimate pass.

Outputs include both scenario runs, `operating-electrical.json`, the revised `model.ifc`, `schema-validation.json`, `pump-electrical.json`, report and source/artifact hashes. Root checks are conditional data/numeric consistency, not design acceptance. Real nameplate and part-load evidence, motor starting, overload/fault protection, operating PF, curve/efficiency applicability, electrical IFC topology, NPSH/control checks, native plotting and BIM-viewer/professional acceptance remain pending.

For the distinction between input/load estimates and load-dependent motor characteristics, see [US DOE, Determining Electric Motor Load and Efficiency](https://www.energy.gov/sites/prod/files/2014/04/f15/10097517.pdf). No default motor PF/efficiency or regulatory values are imported from that reference.
