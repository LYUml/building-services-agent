# Explicit pressure boundaries around a joined local chain

`route_pressure` consumes a passing `route_material` output. It reuses the
existing pinned fluids/network prescribed-flow calculator, saved circular
profile depths, canonical circular specifications and native finite-elbow arc
reader. It adds no fan solver and does not write assumed loss coefficients into
the source IFC.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/route-search/port-pressure-plan.json --out runs/new-local-pressure-workflow
```

The public synthetic plan retains all earlier source/model/material requirements
and adds extended pressure before the route-only DXF. Failed material QA skips
pressure; a failed pressure budget blocks drawing. Manual full engineering
review stays pending. Standalone calculation can reuse an existing verified
material output:

```powershell
.venv/Scripts/python -m bsa.route_pressure runs/source-port-material-workflow/material --basis examples/route-search/extended-pressure-policy.json --out runs/new-extended-pressure
```

The exact policy is mandatory. It explicitly applies the original numeric
supply/terminal targets at the two different outer source-wall cap stations,
uses the original roughness across all local walls and declares both source-wall
excess K values and an additional K for each ideal logical interface. Every new
K has a dimensionless unit, classification, source and the existing excess-over-
centreline-Darcy-friction basis. Zero is an explicit assumption, never a missing
coefficient default. Existing native source K/basis cannot be silently replaced.
Original route body K remains source-bound. All quantities in the fixture are
synthetic assumptions, not manufacturer ratings or measured building inputs.

Source/method/artifact hashes are checked before and after calculation. The
adapter follows actual saved directed links through every local body, requiring
one uniform-bore path between the two source walls. It reads native cap elevations,
straight depths and finite arc lengths. Lengths, bore and elevations cannot be
repeated in the inherited skeleton. A matching compiler-generated straight-route
aggregate K is reconciled to its canonical body values and included once.
The two outer boundary ports must have no actual external peers. Both ports of
every native straight wall must match its true profile/extrusion cap stations
and outward normals through proper rigid frames. A false port at the correct
distance is rejected; an existing connection outside the local subset cannot be
silently treated as an open pressure boundary. Canonical curved/straight route
stations, normals, lengths and bore remain independently source-matched.

`route-pressure.json` records the body order, GUIDs, native inlet/outlet stations,
original construction sources, body and additional interface K decisions, and
per-body friction/minor/elevation pressure components. Their sum must reconcile
with the unchanged network engine. There is no inferred pressure criterion at
intermediate stations: their acceptance remains null. The extra two source walls
are included in this local budget; unrelated services/branches are not included.
Additional interface K is charged once to the upstream body row; that row's
downstream pressure includes the assumed interface loss at the coincident station.

The seven-body example extends the old approximately 5.828 m route to 6.428 m.
A nonzero-interface-loss control keeps the geometry/fluid/flow/numeric supply and
targets fixed while explicitly assuming an additional K0.2 at each of six links.
That control retains its inadequate pressure and drawing gate. See
evidence/extended-route-pressure.json for executed values and source hashes.

Pressures retain a common elevation datum, with rho*g*dz separate from
dissipation. They are not ambient-referenced vertical-air fan duty. Applying
the same numeric target at another station does not establish equivalence with
the old boundary. Product K applicability, actual hydraulic clear bore, individual
roughness, entry/development effects, intermediate pressure suitability, fan
curves/operating points, full multibranch balancing, installation, native joined
drawings and Hong Kong engineering acceptance remain pending.
