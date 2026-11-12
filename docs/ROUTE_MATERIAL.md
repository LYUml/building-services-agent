# Local circular-chain material QA

`route_material` checks a source-bound saved `route_join` result through the
existing IfcOpenShell mesh, Manifold3D Boolean and circular volume engines.
It adds no geometry authoring, mesh repair, routing solver or dependency.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/route-search/port-material-plan.json --out runs/new-material-workflow
```

The source-only synthetic plan retains all prior requirements and adds material
QA after joining. Its route-only DXF requires passing join and material tasks.
Upstream failure skips the QA; a failed QA blocks drawing without deleting the
joined model or numeric findings. Final engineering review remains pending.
Standalone use accepts an exact joined-output folder and explicit QA policy:

```powershell
.venv/Scripts/python -m bsa.route_material runs/source-port-route-joined-source-pinned --basis examples/route-search/material-qa-policy.json --out runs/new-material-qa
```

Before analysis, the adapter verifies original source/method hashes, saved IFC
and snapshot hashes, then replays the joined model's source-preservation and
logical-chain checks. The join receipt now also pins the native selected report
and original network-binding inputs, including the generated canonical route
model. A changed canonical model rejects before another merge is attempted.
Historical join receipts missing those inputs must be regenerated; their hashes
must not be patched to pretend that the inputs were previously verified.

The checked subset contains the exact canonical searched route and its two
source-wall owners. Native straight-source hollow profiles supply analytic
area-times-depth volumes; canonical straight/elbow specifications supply route
volumes from their original parameters. Shapes and world placement remain
unchanged. Saved meshes are translated by one common analysis origin solely
for numerical conditioning, with no vertex snapping or geometric tolerances
used to repair contacts. Other original building elements are not included in
this local material analysis.

Checks cover all local material-pair intersections, one connected material
union, union volume against independent analytic source volume, closed-edge and
two-boundary-bore Euler topology, and finite cylindrical centre-core probes at
every saved local interface. Raw signed intersection residuals are retained.
The public policy declares 1e-12 m3 numeric intersection tolerance, 0.001 relative
volume tolerance, quarter-bore-radius probes with 5 mm half-length and a one
million triangle budget. These are scoped synthetic kernel/tessellation checks,
not installation gaps, regulatory clearances or manufacturer tolerances.

Executed standalone QA on the seven-body curved case reads 272,904 triangles,
21 material pairs and six interface probes. The union has one component and the
two-boundary topology. See evidence/route-material.json for complete workflow
outcomes, retained volume differences and the strict-volume negative control.
That control changes only the declared numeric volume tolerance to 1e-8; it
tests failure retention against finite tessellation accuracy, not a claim that
the physical installation is defective. Unit controls separately show real gap,
interpenetration and centre-plug geometry failures.

Passing a finite central-core probe does not establish the complete bore flow
domain, leakage, CFD or comfort. Ideal wall union does not establish actual
fittings, gaskets, flanges, fabrication or manufacturer applicability. Whole-model
clearance, physical installation, complete network pressure including source
walls, joined-model/native drawing review and Hong Kong acceptance remain pending.
Existing terminal-study clearance failures are not waived by this analysis.
