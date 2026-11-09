# Native 90-degree circular cable envelopes

The electrical saved-IFC reader now supports one canonical circular 90-degree bend per analysis line, alongside existing straight circular extrusions. This is a solid round envelope, not conductor material/area, manufacturer cable selection or an installation design. General polylines, arbitrary-angle bends, composite routes and multiple bodies per line remain unsupported; there is no endpoint-chord fallback.

## Upstream reuse

The body uses standard IFC4 IfcRevolvedAreaSolid through pinned IfcOpenShell 0.8.5 (LGPL-3.0-or-later). Native triangulation and solid checks reuse the existing IfcOpenShell/Manifold 3.5.4 (Apache-2.0) path. The original thin quarter_cable module provides parameter/Axis correspondence and independent analytic QA; it is not another meshing engine. Existing attribution and dependency pins remain unchanged. The failed swept-disk case remains retained, without mesh flipping or widened tolerances.

Primary references: [IFC4 revolution geometry](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcgeometricmodelresource/lexical/ifcrevolvedareasolid.htm) and [IfcOpenShell geometry APIs](https://docs.ifcopenshell.org/ifcopenshell-python/geometry_creation.html). The installed ShapeBuilder has no revolution helper, so the adapter creates standard schema entities through IfcOpenShell; it does not substitute a custom geometry kernel. The initial native trial ran both saved schema/EXPRESS validation and independent mesh/analytic checks, with results in the retained [probe evidence](evidence/pandapower/cable-revolution-probe.json).

## Geometry contract

The canonical profile is an IfcCircleProfileDef with envelope radius a and centre (R,0) in the solid's XY plane. Its revolution axis is positive local Y through the origin, and the angle is exactly pi/2. Require 0 < a < R to avoid a self-intersecting envelope; this is a geometry condition, not a manufacturer minimum-bend rule. The solid's proper rigid placement may rotate/translate the bend in three dimensions. The fixture authors explicit metre and radian units.

The independent Axis must be one three-point IfcIndexedPolyCurve with a single IfcArcIndex(1,2,3) and SelfIntersect false. Its endpoints/midpoint must correspond to the native revolved solid. Changed midpoint with unchanged ends, changed angle/radius/placement, hollow or tapered profiles, unsupported revolution axes and polyline/chord substitutions are rejected. Cable ports must match source bus anchors and curved-body end centres; their local Z axes must agree with outward end-face normals. This orientation check is specific to this supported quarter-circle path, not blanket physical-connection acceptance.

Actual length is R*pi/2, never sqrt(2)*R. Native accepted mesh volume must match pi*a^2*length. The volume centroid differs from the mean centreline: in the canonical frame it is (k,0,-k), where k=(R+a^2/(4R))*2/pi. Exact world bounds use extrema of rotated radial coordinates across the quarter interval; rotating a local bounding box is insufficient. Existing 20 micrometre bounds/centroid and 0.001 relative volume tolerances remain unchanged. These are numerical QA tolerances, not installation tolerances or code limits.

## Reproduce

All values in examples/three-phase-bend are explicit synthetic assumptions/study targets. Its feeder has R=0.3 m, a=0.01 m and true length 0.471238898 m; the chord is 0.424264069 m. The branch is a separate 2 m straight segment. Sources distinguish original electrical parameters/targets from the declared envelope geometry. Device/board physical joints, coordination and manufacturer applicability remain pending.

```powershell
Copy-Item -LiteralPath examples/three-phase-bend -Destination runs/new-bend-source -Recurse
.venv/Scripts/python scripts/author_three_phase_ifc_fixture.py runs/new-bend-source/project.json --geometry runs/new-bend-source/geometry.json --body-kind mixed-revolution --out runs/new-bend-source/cable-fixture
Copy-Item -LiteralPath runs/new-bend-source/plan.json.in -Destination runs/new-bend-source/plan.json
.venv/Scripts/python -m bsa.workflow execute runs/new-bend-source/plan.json --out runs/new-bend-workflow --three-phase-python tools/pandapower-runtime/Scripts/python.exe --graphviz tools/freecad-1.1.4/FreeCAD_1.1.4-Windows-x86_64-py311/bin/dot.exe --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe'
```

The geometry source adds quarter_bends, keyed by explicit analysis line ID; each entry has radius_m, centre_m and a proper 3x3 rotation. Other lines use native circular extrusion. Endpoints must match independently supplied bus anchors, and declared fixture lengths must match the analytic arc/straight lengths. The fixture remains a synthetic test author, not a general instruction-to-installation-model generator.

The existing three_phase_ifc_project producer derives fresh lengths and solves; geometry and same-model drawing gates remain mandatory. A deliberately stale chord-length test generates a new arc-length project and actual fresh pandapower results without overwriting the original. The output schematic remains abstract: a rounded 0.47 m label is not a physical cable route drawing; exact lengths remain in the project/analysis inputs. No Hong Kong rule is automatically selected by this example.

Verification includes actual native volume/centroid/bounds, compound rotation/translation, changed arc midpoint, shifted Body, wrong angle, incorrect end-port orientation, self-intersecting radius and chord substitution controls. End-to-end native execution and actual PDF review are recorded in [workflow evidence](evidence/pandapower/cable-quarter-workflow.json). Full engineering/manual review remains pending. Older straight-only notes in other guides describe earlier scope; hollow pipe/duct elbows still use their own separate source/bore/loss contracts.

Final execution: 10 quarter-circle tests and 41 related straight/native workflow/derivation/delivery-source-plan tests pass. The final staged workflow in runs/three-phase-bend-native-workflow-v2 passes study, geometry and native drawing; manual review stays pending. Its actual PDF was rendered and inspected, its 50 mm reference measures 49.995667 mm, and current delivery context plus complete recorded-file integrity pass. The saved quarter-body multi-view preview was also inspected, with the other segment explicitly omitted; this does not constitute a full BIM-viewer or installation review.
