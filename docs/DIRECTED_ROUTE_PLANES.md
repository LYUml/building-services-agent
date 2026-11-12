# Directed pipe and air-duct routes in declared planes

The existing finite cardinal-grid search accepts optional `endpoint_directions`
records for `start` and/or `end`. Each contains a local cardinal `axis`, a nonempty
`source` and explicit `classification`. These are travel directions, not outward
connector normals. Search and compiled finite-bend tangents both enforce them.
An impossible direction yields no path; the compiler produces no model.

For non-XY studies set routing `coordinate_plane` to `declared-local-frame` and
provide settings `plane_frame`: `origin_m`, perpendicular signed-cardinal
`u_axis`/`v_axis`, `source` and `classification`. Omit `elevation_m` in this mode.
Legacy world-XY settings retain their explicit fixed elevation. This supports
one declared plane in world coordinates, not arbitrary 3D routing. Local obstacle
rectangles refer to that plane; the existing world-XY obstacle extrusion rejects
these inputs rather than misplacing them in the building.

Settings `element_family: duct` creates actual IfcDuctSegment/IfcDuctFitting
entities and requires an explicit AIRCONDITIONING or VENTILATION system.
The default remains pipe. Requested endpoint positions and orthonormal
port frames are read from saved IFC after existing geometry checks: start travel
is minus its SINK outward normal; end travel equals its SOURCE outward normal.
This checks generated endpoints; it does not bind independently selected equipment.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/route-search/vertical-air-plan.json --out runs/new-directed-air-workflow
```

The public example is synthetic. Bore, wall, bend coefficient, obstacle, fluid
properties, pressure supply and targets are declared assumptions. No real
equipment performance or building dimensions are implied. The optimizer reuses
the existing fixed-bore/prescribed-flow pressure objective. World Z elevations
come from generated geometry. Air pressure uses the existing common-elevation
datum contract, not an ambient-referenced fan-duty model.

`ifc_route_drawing` may omit `model` when its direct producer is `route_model`
or `route_optimize`. It then consumes that producer's exact generated canonical
model and saved IFC, including the optimizer's `selected/` directory. A failed
producer blocks drawing. Explicit legacy model inputs remain supported. The
generic drawing uses explicit X/Z projection here; no new native DWG/plot
acceptance is established by producing a DXF.

Executed standalone studies retain a shorter six-bend pressure-failing baseline
and a lower-loss two-bend alternative. A second case with endpoint raised 0.5 m
retains a failed pressure check with unchanged supply/targets: the geometric
pressure term is 1.25 * 9.80665 * 0.5 = 6.12915625 Pa. A saved-IFC control with
the same endpoint position but a wrong normal rejects. An impossible first
heading rejects before creating an IFC output directory. Legacy native pipe
geometry and pressure replay also pass. See evidence/directed-route-planes.json
for full-workflow outcomes and exact local evidence hashes.

Complete obstacle inventory/correspondence, self-clearance, physical joints,
manufacturer dimensions/losses, air-pressure reference applicability, native
plot review and Hong Kong engineering acceptance remain pending. This isolated
route study does not resolve existing terminal-model clearance failures or
provide a complete multibranch air network.
