# Independent vertical water-riser brief

This is a new synthetic test project, not a copy of the finished coursework. Inputs are authored explicitly for this example and labelled as assumptions. It reuses the existing tools without changing their code or inheriting ventilation flow, fluid properties, dimensions, catalogue, equipment IDs or project UUID.

```powershell
python -m pip install -e ".[dev,network,bim,clash]"
python -m bsa.workflow execute examples/water-riser/plan.json --out runs/water-riser
python -m bsa.workflow verify runs/water-riser
python -m bsa.workflow execute examples/water-riser/delivery-plan.json --out runs/water-delivery
python -m unittest discover -s tests -p test_water_riser.py -v
```

The source-linked brief dispatches independent steady electrical calculations/DXF, model-derived water sizing and saved-IFC clash/clearance checks. Two 2.5 m vertical hollow pipe bodies connect a pump envelope to a terminal envelope. Both pipe endpoints and object/port identities survive sizing. The prescribed demand is 0.001 m3/s; the total elevation rise is 5 m. The electric pump input is a separate explicit assumption, not an inferred hydraulic-to-electric conversion.

| Choice | Inside / outside diameter mm | Score points | Required source total pressure kPa | Feasible |
|---|---|---|---|---|
| D15 baseline | 15 / 22 | 5 | 344.351 | No: velocity and pressure |
| D25 | 25 / 32 | 10 | 165.917 | No: velocity |
| D32 selected | 32 / 40 | 15 | 154.362 | Yes under supplied assumptions |
| D40 | 40 / 50 | 20 | 150.911 | Yes under supplied assumptions |

The objective minimises abstract length-weighted material score, so D32 wins over the lower-pressure but higher-score D40. Scores are not prices. Required source pressure includes 100 kPa residual total pressure, `998 * 9.80665 * 5 = 48935.1835 Pa` elevation potential and approximately 5426.992 Pa dissipative loss for D32. Velocity is approximately 1.243398 m/s. With 180 kPa supplied, outlet total pressure is approximately 125637.825 Pa. Reducing supply to 140 kPa makes every option infeasible and leaves dependent IFC QA pending; baseline and candidate failures are retained.

The selected IFC has four physical bodies and three explicitly sourced joint regions. Both conservative outside-to-full checks pass for each connected pair under the synthetic 50 mm general clearance policy. Regions are QA assumptions, not manufacturer fitting or access requirements. The electrical drawing contains three generic device symbols on two circuits, in metre units; it is an editable schematic overlay, not a water-riser drawing or an accepted installation plan.

The separate delivery-plan adds a saved-IFC pipe schedule and X/Z projected centreline DXF. Both 2.5 m segments retain their model GUIDs, 32 mm bore and 40 mm outside diameter; this diagram is not an installation drawing. See `docs/IFC_DRAWINGS.md` for extraction scope and `docs/evidence/ifc-drawing` for the rendered preview and actual output evidence.

Remaining gates include demand/route evidence, pump curve and electrical/hydraulic coupling, starting/fault protection, real fittings and insulation, water-service rules, full installation drawings/schedules, native DWG/PDF and BIM-viewer inspection. This run exercises reusable numeric/model adapters; it does not establish full cross-domain project acceptance. See `docs/evidence/water-riser` for retained actual outputs.
