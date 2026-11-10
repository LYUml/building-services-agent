# Ideal equal-section rectangular tee

Standalone `bsa.rectangular_tee` authors an explicitly sourced sharp90-degree
equal-section tee wall using upstream IFC extrusions, Boolean UNION/DIFFERENCE,
system ports and existing native/Manifold checks. It does not select products or
loss coefficients. Reuse investigation is in MEP_FITTING_REUSE.md; no engine,
dependency or upstream function body is rebuilt/vendored.

```powershell
.venv/Scripts/python -m pip install -e '.[tee]'
.venv/Scripts/python -X utf8 -m bsa.rectangular_tee examples/rectangular-tee/project.json --out runs/new-rectangular-tee
```

Use a new repository-local output. CLI exit2 retains full acceptance pending.
The example is synthetic. Output contains rectangular-tee.ifc and a pinned JSON
report, not an accepted actual-building fitting.

Exact inputs are project_uuid, source, classification
(given/assumed/secondary_transcription), internal_width_m, internal_height_m,
wall_thickness_m, main_half_length_m, branch_length_m, port_directions and placement.
Dimensions are positive and explicit; placement has source/origin_m/rotation and
must be right-handed rigid. Arm ends must lie beyond the junction. Three port
directions must all be SOURCEANDSINK or an explicit SOURCE/SINK mixing/splitting
arrangement. These declarations do not calculate flow or prove duty.

Local main axis is Z from-L to+L; branch axis is+X. Main width is X and height Y;
branch width is-Z and height Y. All three bores have the same width/height.
The material is outer prism union minus inner air union, with sharp ideal corners.
Thickness is a declared intersecting-prism parameter, not authenticated manufacturer
construction. Radius, taper, optimized takeoff and fabrication seams are absent.

Saved checks cover schema/EXPRESS, exact Boolean tree and prism values,
source/classification metadata, rigid placement, stable owned port identities and
full frames/directions. Mesh checks include positive accepted Manifold material,
one connected component, independent prism-intersection volume, bounds, closed
edges and Euler characteristic-2 for the three-port wall. Main/branch centre-bore
probes must be clear. GUIDs derive from project_uuid; design_accepted remains false.

Two native test methods cover two dimension sets, rotated/translated placement,
independent volume values, rejected inner-width/port/filled-wall mutations,
invalid arm lengths and reflected frames. The actual public fixture has zero
schema/EXPRESS issues, three ports and0.0087195m3 material volume; metadata is in
evidence/rectangular-tee.json. Adjoining assemblies,
variable-section fittings, loss analysis, products and full regional acceptance
remain pending. A real variable-section supply tree cannot be replaced by this
equal-section local example.

Unified workflows accept `rectangular_tee` with an explicit `project` source and
ordinary `requires_pass` gates. The recorded IFC artifact is rectangular-tee.ifc;
generic IFC readers inherit it through `depends_on`, with no replacement input.
The public plan deliberately requests a clash check on the isolated fitting:
authoring passes, but clash checking rejects fewer than two represented physical
elements. This is an executed rejection example, not a coordination pass.
Four related test methods cover native geometry, this inherited handoff, source
and artifact integrity, forbidden replacement inputs, simulated producer failure
blocking its consumer, and the existing circular tee workflow.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/rectangular-tee/plan.json --out runs/rectangular-tee-workflow
```

Expect incomplete execution and design acceptance false. This workflow adds no
adjacent ducts, clearance proof, pressure coefficients or engineering approval.
