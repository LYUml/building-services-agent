# Source-bound straight spans between fittings

`bsa.duct_fitting_span` derives a straight candidate between two independently
saved tee/transition compositions. It reuses the existing pinned IfcOpenShell0.8.5
rectangular hollow-wall/port authoring, native mesh checks and Manifold3D3.5.4
material intersection APIs. No new geometry engine or upstream source is copied.

```powershell
.venv/Scripts/python -m bsa.duct_fitting_span runs/span-project.json --out runs/span-study
```

The source project has exactly project_uuid, source, plan, workflow, native_task,
section and endpoints. All paths are relative within that project directory.
endpoints contains two distinct declarations with project, model and binding
paths for the previously generated compositions. The selected source section
must occur once at each fitting and connect different source nodes. New output
must remain repository-local and outside the immutable workflows/models/sources.

Both endpoints undergo fresh duct_fitting_fit checks: saved component geometry,
source/model hashes, the same native-sheet/sizing/binding ancestry, exact source
node/rays and selected nominal sections. The physical end ports are read from
the actual saved IFCs. SOURCE and SINK determine upstream/downstream, independently
of endpoint declaration order. Matching inside dimensions and wall parameters,
opposed normals and matching rectangular width/height axes are required. A 180-degree
roll is materially equivalent for this unkeyed sharp rectangle; a 90-degree roll
is not silently accepted. Actual installation roll remains unverified.

Source centreline length minus both independently checked outward fitting reaches
must leave a positive span. The saved port-plane separation must independently
agree with that length along the source ray. Overrun is retained as fail with no
span.ifc; no length is silently shortened, expanded or borrowed from another
section. Single-end remaining centreline is not used as an installed straight
length. Wall thickness is inherited only when both source-model parameters agree;
there are no inferred gauges, flanges, joints or allowances.

The resulting span.ifc contains one native IfcDuctSegment RIGIDSEGMENT with an
IfcRectangleHollowProfileDef extrusion and two stable owned ports. Saved checks
cover schema/EXPRESS, source/end-port metadata, exact profile/length/local solid,
world placement, end frames/directions, independent wall volume, centroid, bounds,
connected closed mesh and Euler characteristic0. Actual material is also compared
against every distribution component in both supplied endpoint models; overlap
fails the study. This is not a general obstacle, insulation or clearance review.

The endpoint compositions remain in their separate source files. Source-port GUID
metadata and matching coordinates are not saved inter-file IfcRelConnectsPorts
connections. The adapter explicitly forbids claiming such fabricated logical
connections. Merging products into one connected system, full viewer/CAD drawing,
installation elevation/roll, product allowances, pressure and regional acceptance
remain pending. CLI exit2 preserves engineering review when the candidate passes;
failure exits1. Source/component hashes are rechecked after generation.

The fresh node-review source hashes are inherited as well as the fitting-model
hashes. Conflicting snapshots between the two endpoint reviews reject before
authoring; source mutation during authoring rejects before span.json is written.
The complete source workflow integrity check runs again at the end. Tests isolate
these handoff failures; they do not use mocked geometry as native evidence.

An actual private adjacent-node study derives one candidate from an unchanged
source section after deducting both trial fitting extents. The local core/transition
construction and elevation assumptions remain those declared by the two source
studies. No original route or coursework drawing is modified. Detailed model
coordinates and private source records remain in ignored runs; aggregate evidence
is recorded in evidence/duct-fitting-span.json.

Targeted tests check independent two-end arithmetic, endpoint order, positive-span
and retained-overrun cases, section/wall/roll/direction/collinearity rejection,
native identity/oblique placement and saved length/wall/port/source/connection
mutations. Identical overlapping material is rejected and translated disjoint
material passes. The actual source workflow, rather than mocked AutoCAD evidence,
provides native reopening for the real span study.
