# Saved same-file source and route chain

`bsa.route_join` appends a passing `route_ports` candidate into its exact original
source IFC using pinned IfcOpenShell's `project.append_asset`. It reuses the
existing fitting-chain native representation/property fingerprint helpers and
saved endpoint-frame check. No geometry or pressure solver is added. Asset
append receives shared reuse identities and disables name-only asset reuse.
Both input projects must use IFC4 metre units; no conversion is inferred.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/route-search/port-joined-plan.json --out runs/new-joined-route-workflow
```

The public synthetic plan preserves the original source-port study requirements
and adds same-file merging. The join task inherits the passing `route_ports`
producer; replacement source/model files are forbidden. The exact selected
route geometry and original cap frames are rechecked. Both selected source
owners must share one existing distribution system and spatial container.
Imported elements join that system/container without moving their geometry.
Original source elements and relationships remain in the working copy, while
the source file itself is unchanged. Original route links are explicitly rebuilt
and the two source/route interface pairs receive directed SOURCE-to-SINK links.

The adapter saves `joined.ifc`, reopens it and checks exact element/port inventory,
native representation/property fingerprints, world frames, port ownership,
original root identities, system membership and complete directed connection
set. Every connected port has one peer; linked port stations coincide and normals
oppose. All new route bodies and both selected source owners must form one
connected local chain. Saved IFC schema/EXPRESS validation must also pass.
Unrelated source geometry is retained, not declared part of the local chain.

The standalone entry accepts an existing passing source-port output folder:

```powershell
.venv/Scripts/python -m bsa.route_join runs/source-port-route-workflow/route --out runs/new-joined-route
```

Recorded producer inputs/methods and selected pressure/native artifacts must
still match. Changed inputs, occupied source ports, identity collisions, wrong
native endpoint frames or failed upstream pressure cannot authorize a join.
`source-snapshot.json` records the expected saved geometry and links;
`route-join.json` pins source files, methods, snapshot and joined IFC. These are
replay/provenance records, not authenticated manufacturer data or proof of an
installed system. See evidence/joined-route.json for actual executions.

Workflow kind `route_join` uses `depends_on` on an earlier `route_ports` task.
Its saved IFC can feed existing IFC readers through the standard producer map.
The example's route-only DXF still consumes the exact original selected route
and is gated by the join. It does not depict all source elements and is not a
complete joined-model drawing. No new native DWG or visual plot acceptance is
claimed for this sheet.

All fixture geometry and pressure inputs are explicit synthetic assumptions.
Same-file logical connectivity does not establish physical joint construction,
material union, whole-model clearance, full-network airflow/pressure, equipment
selection, installation applicability or Hong Kong regulatory acceptance.
Pressure calculations still cover their original route/boundaries; the added
source-wall lengths are not silently incorporated into fan duty. Original
terminal-model coordination failures remain unresolved.
