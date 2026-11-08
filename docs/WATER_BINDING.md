# Saved IFC to EPANET water graphs

`water_coordination` binds the [steady water graph](WATER_GRAPHS.md) to a saved IFC, with GUIDs and physical port connections. It derives lengths from actual hollow extrusion depths, bore from profile radius/wall thickness, and elevations from world-coordinate ports. It reads and copies the source IFC unchanged; no geometry is inferred from names, envelope widths or the separate schematic coordinates.

```powershell
.venv/Scripts/python -m pip install -e ".[bim,water]"
.venv/Scripts/python -m bsa.workflow execute examples/water-loop-ifc/plan.json --out runs/water-ifc
.venv/Scripts/python -m bsa.workflow verify runs/water-ifc
# Or bind an independently supplied saved IFC:
.venv/Scripts/python -m bsa.water_binding examples/water-loop-ifc/project.json --ifc runs/water-ifc/model/model.ifc --binding examples/water-loop-ifc/binding.json --out runs/water-ifc-direct
```

## Binding contract

The version-1 binding explicitly names one project and distribution-system GUID, node element/all-port GUIDs, ordered pipe-element/start-port/end-port chains, pump element and inlet/outlet GUIDs, provenance and the exact node idealization. Every selected-system distribution element must have exactly one hydraulic role. Every selected port must have one connected peer; actual connections must match the bound node/chain/pump connections exactly. Cross-system, unbound or multiply assigned elements fail. Other systems remain explicitly excluded; whole-building scope is not implied.

The water template must omit all junction/reservoir connection elevations and all pipe lengths/diameters. Repeating those fields is an error. It still supplies sources, independent schematic coordinates, demands/targets, roughness, aggregate route K, fluid, global PDA law, solver budgets/tolerances and pump curves. Derived groups cite both original hydraulic provenance and the saved IFC SHA256. Geometry does not supply a manufacturer curve or applicable fitting K.

Each physical pipe must have a supported direct circular hollow extrusion whose two placed ports match its real profile ends. Imported rigid placements may rotate; explicit length units must resolve to metres. Native millimetre input is tested and normalized. Contradictory metre diameter metadata fails. A chain may turn at coincident connected ports, but its bore must remain constant; split hydraulic links at diameter changes. Ordered port GUIDs define the signed reference direction, independently of GUID sorting or display names.

Pipes require explicit `SOURCEANDSINK` ports because the free-flow solver permits reversal; no one-way/check-valve behavior is inferred. The authoring adapter now creates these connections using both native directed relationship arcs and verifies both after reopening. Standard `SOURCE` to `SINK` connections remain supported. Pumps require actual sink/inlet and source/outlet ports matching their curve direction. Node ports may combine directed pump connections and reversible pipe connections, but connection directions must agree.

All ports on each bound node element must be coincident within 1e-8 m. The binding explicitly declares them a **zero-loss hydraulic node**, with separately sourced withdrawals/boundary heads. A finite-size fitting with separated ports cannot silently collapse into that node. Bends within a chain are ideal geometric junctions whose losses must be covered by supplied aggregate K; this does not author or accept actual elbow/tee products. Noncoincident connections or implicit realizing-element connections fail.

## Output and evidence

The adapter retains an unchanged `model.ifc`, geometry/GUID evidence, derived `network-input.json`, a per-piece flow schedule (`pipe-results.csv`) and real native EPANET evidence under `analysis/`. Each piece carries its own GUID, oriented ports, length and bore and inherits its route's signed flow. A saved IFC re-read reconciles the derived input; original sources and copied IFC are hash checked. Engine failures and failed targets fail the task. Workflow inputs/artifacts remain integrity checked, and failed IFC producers leave analysis pending. The output IFC is registered for downstream saved-model tools; a passing water task does not imply those later tools pass.

The synthetic spatial example has twelve distribution elements and six physical pipe pieces forming four hydraulic routes: lengths 5, 7, 7 and 5 m, all with 40 mm bore and 50 mm outside diameter. Node elevations are 1 or 3 m. It demonstrates unequal branch splitting and reverse flow; values are declared assumptions, not measured building data. [Execution evidence](evidence/water-ifc/README.md).

Pending: general source IFC schema/visual/product applicability, finite fittings and K validation, clashes/clearances, detailed installation drawings, pump efficiency/NPSH, regulations and full engineering acceptance. The current axis-pair drawing adapter cannot depict every segment of this three-axis example in one view; complete multiview/native sheet delivery is a remaining task. No BIM-viewer visual acceptance is claimed by geometry checks.
