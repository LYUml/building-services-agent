# Source-bound duct connection requirements

The single-line drawing and selected schedule do not establish physical fitting
geometry. `bsa.duct_junction_review` identifies the connection requirements at
every node of their conserved directed tree, using the exact AutoCAD-reopened
DXF and its sizing/binding ancestry. It generates a review, not fittings.

```powershell
.venv/Scripts/python -m bsa.duct_junction_review runs/project-plan.json runs/project-workflow native-sheet --out runs/project-junction-review.json
```

The output must be a new repository-local file outside the immutable workflow.
There is no replacement geometry/schedule option. Workflow hashes, plan identity,
passing native-sheet/sheet/schedule ancestry and schedule-project correspondence
are verified before inspecting saved LINEs and again after inspection.

Section IDs, unique handles, model-space geometry, drawing units, endpoint node
identities, shared-node positions, positive sizes/flows, rooted connectivity and
individual node/root/leaf flow conservation must agree. LINE orientation may be
reversed relative to the flow tree. Planar XY geometry only is supported; drawing
Z=0 does not establish actual installation elevation. Source binding and tree
bases are retained with file hashes.

Each node records incident section IDs/handles, saved source position, nominal
width/height, flow direction/demand, outward unit vectors, measured centreline
lengths and pair angles. Classification distinguishes straight continuation,
transition, equal/different-size bends, nominal equal-section tee candidates,
unequal-section tees, nonorthogonal junctions and multiple branches. Equipment
source and terminal boundaries remain separate. Nominal size equality is not a
verified cross-section roll or physical connection.

There are no inferred arm lengths, trim allowances, product ratings, wall or
insulation thicknesses, elevations or loss coefficients. A centreline length is
not an available manufactured fitting length. Required end stations, construction,
installation frames and loss/network data remain listed. Every node retains
fitting_authored=false and pending engineering acceptance, including a straight
continuation or equal-section tee candidate.

An HVAC package can include this review with
`--junction-review-native-task native-sheet`. The task must already be declared
as duct_sheet_native. Its review JSON and count table appear in the package
index; review errors remain explicit. The report, drawing and acceptance checks
retain their existing scopes.

Three targeted test methods exercise metre/millimetre and reversed drawings,
independent angle/length/flow expectations, differing/equal-section classifications,
stale/disconnected geometry, duplicate coverage, failed sizing, bad flow/topology,
inherited ancestry, changed project rejection and immutable output boundaries.
Native reopening itself is verified in the actual project execution, not mocked
by those unit tests.

The actual 47-section private HVAC plan identifies 48 nodes: one source boundary,
20 terminal boundaries, ten bends, 15 unequal-section tees and two multi-branch
connections. This changes the next authoring action: the equal-section tee
fixture cannot represent any of those 15 differing-size branch connections.
The VAV boundaries still lack actual product port geometry. No project geometry
is reconstructed or released by this review.
