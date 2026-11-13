# Compact circular-elbow IFC triangle storage

Profiling the retained 23.2 MB joined-route IFC showed 36.3 of 41.1 profiled
seconds in structural/EXPRESS validation. IfcOpenShell's installed geometry HDF5
cache addresses mesh iteration, not this schema workload; exact-file validation
reuse also misses fresh replays whose IFC bytes differ. No cache was enabled and
no validation was disabled.

The existing elbow tessellator already outputs triangles. Its default authoring
now reuses pinned IfcOpenShell0.8.5 ShapeBuilder.triangulated_face_set rather than
creating one IfcIndexedPolygonalFace entity for every triangle. The wrapper checks
all faces have exactly three indices because the upstream helper takes the first
three entries. Existing unit conversion, exact vertices/indices, closed flag,
Axis/arc, placement, bounds, diameter/radius, ports, bore topology, independent
volume and schema/EXPRESS checks remain. Mesh chord/angular resolution and the
0.1% volume tolerance are unchanged. Legacy polygonal models remain supported by
the geometry reader with those same checks; historical receipts are not rehashed.

The same public synthetic elbow has 66,360 coordinates and 132,720 triangles in
both formats, compared exactly. In one controlled full author/save/reopen/native/
schema trial, compact storage used 6,821,662 bytes/171 entities and 28.26 seconds;
legacy upstream polygonal storage used 12,307,662 bytes/132,891 entities and 33.45
seconds. This is a single illustrative trial under host load, not a general
speed guarantee. A separate profiled route inspection is not the timing baseline
for that authoring comparison.

Sixteen native geometry/join/material tests pass with zero skips, including
legacy-format creation/reopen, changed triangle coordinates/indices, changed Axis
and source losses. Mesh tampering is checked by the saved geometry verifier;
network binding reconciliation separately checks topology/arc lengths/losses.
The complete existing public circular-air workflow executes nine scoped tasks
in 164.85 seconds, including routing, material, pressure, selection, operating
flow, saved IFC metadata and DXF drawing. Final manual review remains pending.
There is no matched full-workflow legacy timing, so no whole-graph speedup is
claimed. Native DWG plots, other viewers, products and installation remain open.

Reproduce with scripts/benchmark_elbow_storage.py and
scripts/run_compact_airflow_demo.py using fresh --out runs directories. The
benchmark deliberately switches between two existing upstream builders in-process;
it is a controlled synthetic comparison, not a production provider substitution.
No installed upstream source/binary is modified or vendored. Existing IfcOpenShell
notices apply. See evidence/ifc-mesh-storage.json.
