# Saved connected local duct chains

`bsa.duct_fitting_chain` regenerates and verifies a source-bound straight span,
imports the two source fitting compositions and that straight into one IFC4
metre project, and rebuilds their directed port connections and ventilation
system. Existing IfcOpenShell0.8.5 project.append_asset, placement, system and
native geometry APIs plus Manifold3D3.5.4 are reused without copying an engine.

```powershell
.venv/Scripts/python -m bsa.duct_fitting_chain runs/span-project.json --out runs/local-chain
```

The project is the same explicit source project described in DUCT_FITTING_SPANS.md.
All local fitting/native-source checks execute freshly. A failed/overrun span
blocks merging. Original source models and generated component evidence remain
unchanged and hash-tracked. The resulting chain.ifc and source-snapshot.json have
their own hashes; design_accepted remains false.

## Geometry-first port placement

The admitted source bodies are the previously verified ideal rectangular core
tee, centred section-plane-offset transition and straight hollow extrusion. Raw
source ports are checked against their actual native cap stations. Their source
world-to-local placement can contain floating-point round-trip error. The new
model uses frames read from those native caps, not rounded source port offsets,
to solve parent-relative product placements along the directed tree. Every saved
product/source port still must match its original world frame within1e-9 for
matrix entries (metres for translation and dimensionless rotation components);
the observed differences are recorded.
No wall dimension, route length, physical joint gap or clearance is invented.

This distinction matters for exact butt faces. The initial actual merge preserved
source shapes and logical links but failed connected-material union because raw
port offsets introduced tiny separations. Reading native cap stations restored
the unchanged source material topology. No snapping of wall vertices or inflated
material tolerance was used. This is consistent with the upstream
[Manifold precision warning](https://manifoldcad.org/jsdocs/) about nearly coplanar
faces and floating-point drift; executed evidence uses pinned3.5.4 rather than
assuming the current online runtime.

Stable source product/port identities, native forward-geometry attributes and
source properties are preserved. Source shape hashes omit STEP IDs and context
identity; they include the actual profiles, Booleans, coordinates and extrusion
parameters. Duplicate GUIDs, extra products/ports, changed source shapes/properties,
wrong ownership/directions/frames or unexpected imported systems/connections
reject. The append operation's source contexts are reused through its upstream
API, not manually reconstructed geometry.

## Saved checks

The source/target schema must pass EXPRESS validation. Exact saved component and
port inventories, owned frames, one-peer connections and the complete directed
product tree are checked. One VENTILATION system must contain exactly those
products with the source section metadata. Original directed internal links are
retained, and two real same-file IfcRelConnectsPorts interfaces join the new span
to its source fittings. This replaces the previous inter-file boundary-only span
for this local output; it does not modify the originals.

Native material checks cover each saved body, pairwise interpenetration, one
connected union, and independent volume summed from the freshly verified source
component integrals. The closed union must retain the topology implied by its
external boundary ports. The actual local case has seven products,16 owned
ports,six directed interfaces,four boundary ports and Euler characteristic-4;
all21 material pairs pass. This is local geometry/connectivity evidence, not a
pressure solution or installed/product/clearance acceptance.

Two native test cases within one method cover identity and translated oblique
frames, unchanged source files, native cap/source-port correspondence, independent
volume and saved missing-link/body/pose/port/system/extra-object rejection. Separate
workflow controls retain failed producers and block IFC readers. Actual source
execution and official IfcMCP inventory remain separate executed evidence rather
than mocked geometry.

## Workflow and independent inventory

Workflow kind duct_fitting_chain takes project and ordinary task/gate fields.
It pins the nested source plan/workflow, its actual input/runtime/artifact files,
fitting projects,bindings and component models. Generic readers inherit chain.ifc
through depends_on; replacement IFC inputs are forbidden. For example:

```json
[
  {"id":"chain","kind":"duct_fitting_chain","project":"span-project.json"},
  {"id":"inventory","kind":"ifc_query","depends_on":"chain","requirements":"duct-counts.json"}
]
```

Pass the established isolated tools/ifcmcp-runtime/Scripts/python.exe through
--ifcmcp-python when using the official query reader. That runtime remains
separate from the0.8.5 engineering environment. Minimum-count contracts now also
accept IfcDuctFitting and IfcDuctSegment, verified through the upstream exact-class
summary. The actual six-fitting/one-segment/16-port/one-system contract passes;
an intentional seven-fitting shortage fails. Counts do not prove connectivity:
the saved native graph and material checks above provide that separate evidence.

The whole-model diagnostic plan/side preview includes all seven source-checked
bodies. It is not a hidden-line drawing or a BIM-viewer acceptance. The existing
labelled ifc_preview tool's12-port budget still applies to selected subsets;
do not omit components or expand its budget merely to call a whole-model review
complete. Real installation elevation/roll, source construction assumptions,
product allowances, full network pressure, remaining branches and the complete
coursework requirement matrix stay pending.
