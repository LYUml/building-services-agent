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

The saved model can now feed [orthographic drawing sets](IFC_VIEWS.md), including explicit end-on symbols and native/printed verification for the three-axis example. The older single-view adapter retains its end-on rejection. Pending: general source IFC schema/visual/product applicability, finite fittings and K validation, clashes/clearances, detailed installation drawings, pump efficiency/NPSH, regulations and full engineering acceptance. No BIM-viewer visual acceptance is claimed by geometry checks.

## Closed chilled-water circulation fixture

`examples/circulation-ifc` supplies an independent CHILLEDWATER model, GUID binding and zero-withdrawal circulation template. Author model.json with bsa.bim, then run bsa.water_binding with project.json, the saved model.ifc and binding.json. Saved hollow profiles produce 65 mm bore and four physical lengths of 1, 2, 1 and 2 m; actual node ports produce elevation 1 m. The pressure reference connects on a side branch; a pump and explicit three-pipe return form the circulating loop. All geometry and hydraulic values are synthetic assumptions.

Native IFC and EPANET checks pass with positive circulation and zero reference exchange within declared numerical tolerances. A negative test exposed loss of one native direction being hidden by undirected connection deduplication. The binding now rejects missing reverse relationships for reversible ports and duplicate directed relationships, while preserving one SOURCE-to-SINK relationship for pump connections.

Evidence is retained in docs/evidence/circulation-ifc. Junction envelopes are coincident zero-loss idealizations, not physical fitting products; no clash, viewer, installation or engineering acceptance is claimed. The derived network can be inspected independently, but thermal/regulatory workflow inheritance from this saved IFC remains to be integrated.

## Saved circulation to thermal and jurisdiction checks

`bsa.ifc_circulation_checks` accepts `--producer` (water_binding output), `--template`, `--binding`, `--thermal-basis`, `--rule-basis`, `--pack`, `--sources` and a new `--out` directory. It verifies original input identities and all inventoried native files, rederives geometry from the saved IFC and compares the complete hydraulic input. It checks density consistency, then freshly reruns thermal transport and scoped pipe rules on that exact derived input. Both results remain visible even when one fails. Combined status cannot pass a thermal or hydraulic failure, missing rule evidence or unresolved rule review.

The source template and binding must be the originals referenced by the producer. The adapter accepts no replacement hydraulic project. Geometry reconciliation detects changed derived dimensions even if the caller rewrites that artifact's recorded hash. Hashes are integrity records, not signatures authenticating engineering truth.

The real synthetic run in docs/evidence/ifc-circulation-checks uses examples/circulation-ifc/regulatory-bases.json, the 40 kW synthetic thermal basis and the pinned official BEC pack. It passes scoped thermal/rule checks while retaining full engineering acceptance as false. Workflow kind `ifc_circulation_checks` now inherits an earlier `water_coordination` task through `depends_on`. Supply thermal_basis, rule_basis, pack and sources; project/template/binding/ifc/producer replacements are forbidden. A failed producer prevents execution. Add requires_pass to subsequent delivery tasks; unresolved combined checks block them. The workflow inventories both bases and official sources, and the coverage planner recognizes the selected pack. Detailed fittings/clashes, native drawings and full regulatory coverage remain unresolved.

## Physical coordination gate: intentionally failed fixture

Run `python -m bsa.workflow execute examples/circulation-ifc/coordination-plan.json --out runs/new-circulation-clash`. This is a retained negative engineering fixture: hydraulic binding passes but full represented-solid clash inspection fails. The generic centred junction envelopes intersect pipe walls and pump bodies; perpendicular straight walls also overlap at idealized corners. Manifold confirms positive shared volume, including approximately 0.004 m3 between pump and suction node envelope. These are modeled material intersections, not waived connection contacts.

The 50 mm clearance is an explicit synthetic policy, not a code-derived requirement. No contact exceptions are supplied. Geometry coverage passes, so the failure cannot be dismissed as missing meshes. Downstream drawing is pending and no drawing directory is created; workflow integrity still passes because faithfully recorded design failure is not data corruption.

Evidence: docs/evidence/circulation-clash-gate. Resolving this fixture requires physical fitting/equipment interfaces and consistent hydraulic treatment of their finite geometry. Relaxing overlap limits or suppressing node solids would not establish installation acceptance. Existing thermal/rule passes remain scoped numerical evidence only.

## Finite circular elbow routes

Bindings may now include `fitting_sources` keyed by the exact fitting GUID with the full source-parametric elbow device definition, and `piece_losses` keyed by every physical piece GUID on any route containing a fitting. Each loss record has value, source and basis `excess over centreline Darcy friction`. Template aggregate minor_k must be absent on these routes. Saved per-piece K metadata must agree with those explicit sources; missing/extra piece coverage is rejected.

Only the existing metre-based, source-parametric 90-degree circular hollow elbows are supported. The adapter verifies native wall mesh, bore, arc, placement and metadata against source geometry, then independently reads saved arc length and checks reversible ports against both arc ends. It sums straight lengths plus physical arc lengths and adds only declared excess K. Geometry never supplies manufacturer loss coefficients. Different bores still require separate hydraulic links. Non-metre finite-fitting files and arbitrary imported fitting products remain unsupported.

The isolated examples/epanet-elbow fixture provides a 0.3 m centreline-radius bend between two 1.5 m straight pieces, with 80 mm bore, 100 mm OD and synthetic excess K=0.4. It exercises the native EPANET binding independently of the closed circulation fixture. Its endpoint node envelopes are still idealizations; this extension alone does not fix the circulation fixture's tees, pump interfaces or physical clash failures.
