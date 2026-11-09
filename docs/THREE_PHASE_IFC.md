# Straight electrical IFC correspondence investigation

Status 2026-11-10: **not a verified integration**. The straight cable fixture passes saved IFC schema validation, but all eight actual cable/settings cases fail the mandatory Manifold solid check. No geometry correspondence, connected electrical installation or engineering acceptance is claimed. The adapter is not registered as a workflow task.

The author reuses pinned IfcOpenShell 0.8.5 (LGPL-3.0-or-later), its official API and ShapeBuilder swept-disk implementation, plus the existing Manifold 3.5.4 (Apache-2.0) checker. No replacement geometry engine is implemented. Existing upstream license attribution remains applicable. Official references: [ShapeBuilder](https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/shape_builder/index.html), [IFC4 IfcCableSegment](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2/HTML/schema/ifcelectricaldomain/lexical/ifccablesegment.htm), and [geometry settings](https://docs.ifcopenshell.org/ifcopenshell/geometry_settings.html). Online documentation describes newer versions too; installed versions and executed outcomes are recorded separately.

Reproduce with new output names:

```powershell
.venv/Scripts/python scripts/author_three_phase_ifc_fixture.py examples/three-phase-network/project.json --geometry examples/three-phase-network/cable-geometry.json --out runs/new-cable-fixture
.venv/Scripts/python scripts/probe_cable_mesh.py --ifc runs/new-cable-fixture/cables.ifc --out runs/new-cable-probe.json
.venv/Scripts/python -m bsa.three_phase_ifc examples/three-phase-network/project.json --ifc runs/new-cable-fixture/cables.ifc --binding runs/new-cable-fixture/binding.json --out runs/new-cable-binding
```

The last command currently raises a solid-validation error; it must not be advertised as a successful command. The read-only probe completes even when all geometry cases fail: its process success means diagnosis completed, not geometry passed. Inspect each `accepted` field. It neither edits IFC nor repairs triangles.

[Executed diagnostic evidence](evidence/pandapower/cable-mesh-probe.json) retains the original IFC hash, runtime versions, all cable GUIDs, edge/triangle statistics and failures under default settings, `reorient-shells`, `unify-shapes`, and `no-clean-triangulation`. These documented upstream options were exercised independently; none resolved the failure. Closed undirected edge counts and a plausible volume are insufficient to override orientation/solid rejection.

The fixture uses synthetic 40 m and 25 m straight paths and a 10 mm envelope radius. This radius is not conductor area, cable selection or manufacturer data. Ports are not externally connected; bus anchors are analysis correspondence references, not authored boards. The draft reader compares saved Axis, Body directrix, placed ports, system membership, world bounds/centroid/volume and project lengths. It rejects unsupported bends rather than approximating them by chords. Because native solid validation fails first, later checks are not yet positively validated. Length derivation into a new numerical study, revision invalidation, workflow gating, viewer review and real installation topology remain future work.

Next investigate the upstream swept-disk tessellation with a minimal reproducer, or evaluate the existing analytic extrusion path for genuinely straight cable bodies. Preserve this failing swept-disk case; do not relax tolerances or silently flip faces to obtain a pass.
