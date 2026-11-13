# Finite circular elbows

[Source-checked planar route drawings](IFC_ROUTE_DRAWINGS.md) now include the finite elbow as editable circular axes and OD outlines, with native DWG reopen, PDF-scale and inspected-sheet evidence. Product/installation detail and BIM-viewer acceptance remain pending.

`examples/circular-elbow` adds explicit constant-bore 90-degree pipe/duct fittings to the existing straight-wall contract. These are generic numerical geometry, not manufacturer fittings. Supply inside/outside diameters, centreline radius, arc centre, two perpendicular signed cardinal axes, bounding origin/size, two actual end-face ports and provenance. The radius must exceed the outside radius. Opt into `axis-aligned envelopes, straight circular walls and explicit 90-degree elbows` and `body_shape: circular 90-degree elbow wall`.

The IFC4 Body is a parameter-derived closed `IfcTriangulatedFaceSet` (legacy polygonal files remain readable); the separate Axis is an exact three-point circular `IfcIndexedPolyCurve` with `IfcArcIndex`. Body faces approximate the circular surfaces. This deliberately does not claim an analytic swept Body. Sampling respects the existing 10 micrometre chord and 0.02 radian angular limits, with a size budget. Reopening checks source coordinates/face indices, schema, placements, tangent port axes, bounds, diameter/radius properties, connected oriented closed wall, through-bore Euler characteristic zero and independent quarter-torus volume within the unchanged 0.1% tolerance.

Local Windows IfcOpenShell 0.8.5 experiments with an analytic hollow swept disk and a fixed-reference hollow-profile sweep produced inconsistent triangle winding. A Boolean subtraction experiment failed independent wall-volume/topology checks. They were rejected; the verifier does not repair winding or relax its checks. This is a local conversion observation, not a claim that the IFC standard prohibits those representations.

```powershell
.venv/Scripts/python -m pip install -e ".[bim,network]"
.venv/Scripts/python -m bsa.workflow execute examples/circular-elbow/plan.json --out runs/elbow-model
.venv/Scripts/python -m bsa.network_binding examples/circular-elbow/network.json --model examples/circular-elbow/project.json --binding examples/circular-elbow/binding.json --out runs/elbow-route
.venv/Scripts/python -m unittest discover -s tests -p test_circular_elbow.py -v
```

The existing constant-density directed tree binding derives straight lengths plus actual circular arc lengths. Reconciliation independently reconstructs the saved Axis circle from its three points and checks that saved ports span its ends. For any route containing an elbow, every piece must explicitly provide `LocalLossCoefficient` and `LocalLossBasis: excess over centreline Darcy friction`. The network must omit aggregate `minor_k`. This avoids counting a total fitting K together with Darcy friction over its physical arc. Use only a justified excess-K source; the example's 0.4 is a synthetic assumption, not a product correlation.

The example has 0.08 m bore, 0.10 m outside diameter, 0.30 m bend radius and two 1.5 m straight pieces. At 0.0001 m3/s, density 998 kg/m3 and viscosity 0.001 Pa s, length is 3.471238898 m, Reynolds number 1588.366 and dissipative pressure loss 0.424289379 Pa. The test independently evaluates `128 mu L Q / (pi D^4) + K rho v^2 / 2`; saved arc and K tampering must fail reconciliation. This tree uses total pressure and is distinct from the EPANET static-head graph adapter, which still rejects finite separated-port junction idealizations.

Pending: BIM-viewer visual review, manufacturer connectors and bend correlations, other angles/cross-sections, EPANET finite fitting integration, full fitting schedules/installation drawings and engineering acceptance. Existing straight-segment projections do not automatically provide elbow installation detail. Design acceptance remains false.

## Saved-route coordination

The separate `coordination-plan.json` preserves the original model/pressure plan and adds a requirement-linked `ifc_clash` task depending on its saved model. Install `[bim,network,clash]`, execute that plan into a new output directory, then run `bsa.workflow verify` on it. The checking policy declares synthetic 10 mm clearance outside two 0.10 m spherical joint regions, 0.1 mm contact/intersection tolerances and 1e-10 m3 overlap tolerance. These are explicit scenario assumptions, not a standard or manufacturer recommendation.

```powershell
.venv/Scripts/python -m pip install -e ".[bim,network,clash]"
.venv/Scripts/python -m bsa.workflow execute examples/circular-elbow/coordination-plan.json --out runs/elbow-coordination
.venv/Scripts/python -m bsa.workflow verify runs/elbow-coordination
```

The top-level workflow now records the bound network project itself as an input, alongside its model, mapping and brief. Previously only the pressure adapter's nested report retained that source hash; the top-level integrity check could miss a later network-source edit. A regression executes actual workflow input collection with only the native adapter mocked, then changes the source pressure and requires top-level verification to fail. The native coordinated example is also rerun without mocks. Historical archived workflows are retained as observed and do not acquire this fix retroactively.

All three physical elements form accepted closed solids. The two tangent end-face contacts have zero reported contact distance. Their axis-aligned bounds merely meet at the end planes, so no positive-overlap Boolean candidate is required for the baseline. Both nonempty outside-to-full directions at each joint establish the guarded 0.01002 m threshold. This is a capped lower bound for the approximate mesh, not an exact measured gap or a connector-compatibility result.

Four native regression tests cover the ordinary route, straight-wall intrusion with unchanged connected ports, a 20 mm cube in the empty curved bore, and mid-arc material/clearance failures. Extending the incoming wall by 20 mm must produce a positive Manifold overlap with the elbow and cannot receive a contact exception. A cube centred on the circular axis passes despite overlapping bounds; moving a cube into the wall fails the material test, while a separate small cube near the bore wall fails clearance without a material intersection. The original saved fixture bytes stay unchanged. Run `python -m unittest discover -s tests -p test_elbow_clash.py -v` with the clash dependencies installed. Numerical evidence and the actual coordinated IFC are retained separately under `docs/evidence/elbow-coordination`.

Retained evidence is in [validation.json](evidence/circular-elbow/validation.json) and `workflow.zip` beside it. The archive contains the actual saved IFC, native/schema and pressure reports, derived inputs and workflow artifact hashes. The complete 219-case run passed all 215 prior cases and three new cases; its sole error was a misplaced variable reference in the new cardinal-frame test. After correcting only that test, all four elbow cases passed (including 24 source frame combinations). Both logs are retained without relabelling the initial failed run green. The source-linked workflow was then executed and its artifact integrity verified separately. No BIM-viewer or plotted fitting drawing acceptance is claimed.

Representation references: [buildingSMART indexed circular-arc geometry](https://technical.buildingsmart.org/projects/2024tunnel/schema/ifcgeometryresource/lexical/ifcarcindex.htm) and [swept disk definition](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_1/FINAL/HTML/schema/ifcgeometricmodelresource/lexical/ifcsweptdisksolid.htm). These explain the concepts; generated files remain IFC4 and undergo their own IFC4 schema validation.

Compact triangle storage preserves the exact mesh and all checks; see IFC_MESH_STORAGE.md for actual controlled comparison and workflow evidence.
