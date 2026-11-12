# Source-guided circular-wall endpoint routing

`bsa.route_ports` replaces manually copied route endpoints with exact selected
owner/port GUIDs from a saved IFC4 model. It is a thin adapter over pinned
IfcOpenShell 0.8.5 placement/system utilities, existing rigid-frame validation,
directed finite-grid search and fixed-bore prescribed-flow pressure optimization.
It introduces no geometry engine, solver or dependency.

The implemented source boundary is deliberately explicit: one model, two distinct
straight hollow pipe or duct walls, the same distribution system, an open SOURCE
at the supply and open SINK at the receiver. The native extrusion profile supplies
the bore/OD comparison, not a nominal-size text property. Actual cap positions
and outward normals must match the selected native port frames. Proper rigid
frames are required; the two cap stations and travel tangents must lie in the
declared signed-cardinal routing plane and grid. No unit conversion, arbitrary
rotation, automatic reducer, joint allowance or equipment connector inference
is supplied. Unsupported/missing source geometry rejects before route output.

The routing template must omit `start_m`, `end_m` and `endpoint_directions`.
The adapter derives them as `geometry-derived` with original owner/port GUIDs
in their provenance. SOURCE outward normal is the starting travel tangent;
receiving SINK travel is minus its outward normal. After optimization and saved
IFC geometry checking, the generated route endpoints are compared again with
these original source frames. Sources/methods remain hash-pinned and unchanged.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/route-search/port-routing-plan.json --out runs/new-source-port-workflow
```

The public source-only example authors two synthetic hollow source walls,
then `route_ports` inherits the exact producer IFC using `depends_on`. A
replacement `ifc` in that task rejects. The resulting `ifc_route_drawing`
inherits its exact selected route IFC and generated canonical model. Failed
source generation blocks routing; failed pressure blocks drawing. Final manual
review remains pending. A standalone CLI also accepts an existing source IFC:

```powershell
.venv/Scripts/python -m bsa.route_ports runs/port-route-source/model.ifc --basis examples/route-search/port-routing-basis.json --routing examples/route-search/port-routing-template.json --settings examples/route-search/vertical-air-settings.json --network examples/route-search/vertical-air-network.json --out runs/new-source-port-route
```

The source fixture is an assumed synthetic study, not real equipment. Ports,
wall bore, outside diameter, grid, bends, clearance, fluid properties and pressure
targets are not measured installation or manufacturer claims. Pressure retains
the existing common-elevation-datum contract; it is not ambient-referenced fan
duty. The isolated route and original source walls remain in separate IFCs:
there are no merged same-file logical links or physically approved joints.
Equipment families, full volumetric source/obstacle coordination, multibranch
networks, installation applicability, native plot review and complete Hong Kong
regulatory acceptance remain pending. This step does not clear existing terminal
study clash failures. See evidence/source-port-routing.json for executed results.
