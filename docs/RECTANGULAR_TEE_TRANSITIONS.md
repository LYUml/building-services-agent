# Tee and centred-transition composition

`bsa.rectangular_tee_transitions` composes the existing source-declared equal-section
core tee and one to three centred rectangular transition components. Geometry
engines are unchanged: pinned IfcOpenShell0.8.5 authoring/asset append/system APIs,
Manifold3D3.5.4 and existing native/source checks are reused. See REUSE_SURVEY.md,
RECTANGULAR_TEES.md and RECTANGULAR_TRANSITIONS.md for upstream evidence and limits.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/rectangular-tee-transitions/plan.json --out runs/tee-transitions
```

Standalone CLI accepts a project and --out. Project fields are exactly source,
classification, tee and arms. tee is a relative source JSON within the project
source directory. arms must explicitly cover main-a, main-b and branch. Each is
either `{"kind":"bare"}` or a transition with kind, end_section_m,
start_length_m, end_length_m, upstream_angle_degrees and transition_length_m.
At least one transition is required. Bare means the existing core port remains an
external boundary, not an inferred straight segment or joint.

Every transition inherits the core inside section and section-plane wall offset.
Its namespace is deterministically derived from the core project UUID and arm,
so bodies/owned ports are stable and distinct. Its source/classification stays
separate from the core source. Outward placement/section roll derives from the
declared core port; the start flow direction opposes that port and the external
end inherits its direction. Directed and bidirectional declarations are supported.
No elbow, eccentric adapter, general branch loft or direct abrupt unequal tee is
inferred. The layout is a core tee plus separate centred transitions.

Upstream project.append_asset imports the actually saved component and owned
ports. Parent-relative placements are saved explicitly to preserve coincident
interfaces under rigid transforms. The source component IFCs, logs and specs are
kept and hash-checked. Saved checks cover whole-file schema/EXPRESS, individual
core/transition native geometry and source values, exact component/port inventory,
system source/membership, stable identities and full opposed/coincident port frames.
Standalone transition inspection still rejects extra distribution elements;
component inspection is only used with the composer's complete inventory check.

Material checks use actual saved local meshes and relative placements: no
interpenetration, a single connected union, independent sum of source-integrated
volumes, closed edges and Euler characteristic-2. Main and branch centre probes
must be empty. These probes do not prove minimum clear bore. The public two-arm
fixture has three fittings, seven ports, two directed interfaces and material
volume0.02323721723m3. Its same-model clash consumer checks explicitly synthetic
contact regions plus outside-region clearances; these tolerances are not code or
product criteria. Full construction, loss and installation acceptance remain pending.

## Bind a local study to actual source rays

`bsa.duct_fitting_fit` freshly verifies the composition model and inherits the
exact native-sheet/sizing/binding ancestry through duct_junction_review:

```powershell
.venv/Scripts/python -m bsa.duct_fitting_fit PLAN WORKFLOW NATIVE_TASK COMPOSITION_PROJECT MODEL_DIRECTORY ARM_BINDING --out runs/local-fit-review
```

ARM_BINDING has exactly source, node and arms (three unique arm-to-section IDs).
The selected source node must have three incident sections. XY origin, outward
planar rays, supply directions and external nominal sizes must match. Each fitting
end must lie forward on its exact source ray. The resulting outward reach is
compared with saved source centreline length. Overrun is retained as fail; it is
not truncated or hidden. No source drawing or existing immutable run is modified.
Current project/model/component pins and source workflow integrity are checked
again after the review. The new output remains in the repository or explicit host-selected project workspace, separate from original runs.

This is a necessary local **plan extent** test. Remaining centreline is not an
installed straight length or proof of available space. Opposite-end fitting
consumption, elevations, section roll, insulation/obstacles, product joints,
fabrication and pressure/network acceptance remain explicitly unverified. Model Z
does not become a measured installation elevation through a two-dimensional plan.

An actual private node study now preserves source-selected nominal sizes and saved
XY/rays while declaring core reaches, wall offset, straight ends and taper angle
as separate software-study assumptions. Its saved three-component model passes
native checks and all three ends remain within their source segments. It is one
local candidate, not a replacement for the15 unequal connections or approval of
the coursework network. Source files and detailed positions stay in ignored runs.

Two native test methods exercise two/three-arm, bare-boundary, directed and
translated non-axis-aligned bidirectional cases plus saved gap/wall/link/system/
extra-element rejection and failed upstream length. Workflow tests exercise actual
same-model clash inheritance and real producer failure blocking the consumer.
Plan-fit tests independently verify reaches, retained overrun and size/ray/origin/
direction/mapping rejection. Existing standalone transition workflow tests remain
passing. Evidence is in evidence/rectangular-tee-transitions.json.

Transition arms may explicitly declare geometry_method as documented in RECTANGULAR_TRANSITIONS.md. For source-wide candidate compilation and both-end budgets, see SOURCE_TEE_CANDIDATES.md; isolated assemblies do not replace the original connected backbone.
