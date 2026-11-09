# Closed circulation with finite return bends

The independent `examples/circulation-elbows` variant replaces the two idealized return corners and their node envelopes with two source-parametric 90-degree hollow bends. It retains the pump, suction/supply nodes and pressure-reference connection so their unresolved physical interfaces remain visible.

```powershell
.venv/Scripts/python -m bsa.bim examples/circulation-elbows/model.json --out runs/new-bend-model
.venv/Scripts/python -m bsa.water_binding examples/circulation-elbows/project.json --ifc runs/new-bend-model/model.ifc --binding examples/circulation-elbows/binding.json --out runs/new-bend-hydraulics
.venv/Scripts/python -m bsa.clash runs/new-bend-model/model.ifc --policy examples/circulation-elbows/clash-policy.json --out runs/new-bend-clash
```

The single return link has three straight pieces of 1.8, 0.6 and 1.8 m and two radius-0.2 m quarter circles: total centreline length 4.2 + 0.2*pi m. All pieces have 65 mm bore and 80 mm OD. Two explicitly synthetic excess-loss coefficients of 0.4 sum to K=0.8; straight-piece excess losses are zero. These assumptions differ from the old aggregate-K fixture: this is a new scenario, not an isolated experiment attributing a flow change solely to geometry or a product optimization claim.

Every pipe/fitting has reversible native port relationships. Saved IFC geometry and per-piece loss metadata are rechecked before real EPANET circulation. Pump/reference interfaces remain idealized, and the clash policy provides no contact exceptions. End-face contacts may fail the 50 mm synthetic clearance requirement even without material overlap. Any remaining overlaps or clearances keep installation/drawing acceptance unresolved.

## Observed native results

Saved geometry derives length 4.828318531 m and excess K=0.8. Native mass balance and pipe energy checks pass, but the pump operates at approximately 5.379 L/s beyond the supplied curve endpoint of 5 L/s. The native extrapolation/warning is retained and pump-domain/engine checks fail. No operating-point acceptance or product suitability is claimed; a properly sourced pump curve or revised design is needed before hydraulic release.

Full geometry coverage passes. Positive-volume overlap pairs fall from 15 in the original ideal-corner fixture to 9 here; none involve BEND_A, BEND_B or CROSS. Remaining overlaps concern the pump, suction/supply/reference node interfaces and nearby pipes. Clearance also remains failed with no contact exceptions. This resolves the return corner material geometry but does not establish full collision-free installation or drawings.

Native IFC, bound network, failed hydraulic evidence, clash report and hash-linked material-overlap comparison are retained in docs/evidence/circulation-elbows. Failed results are intentional retained evidence of the current design state, not a completed design.
