# Source-checked planar route drawings

`ifc_route_drawing` extends the drawing pipeline to finite circular 90-degree elbows and tangent straight walls. The original `ifc_drawing` remains a straight-segment schematic reader and still lists fittings as omitted. Use this separate adapter when the original source-model JSON is available and every physical route element is an explicitly supported straight circular wall or finite elbow.

```powershell
.venv/Scripts/python -m pip install -e ".[bim,network,clash]"
.venv/Scripts/python -m bsa.workflow execute examples/circular-elbow/delivery-plan.json --out runs/elbow-delivery --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
.venv/Scripts/python -m bsa.workflow verify runs/elbow-delivery
# Drawing only, from a saved IFC:
.venv/Scripts/python -m bsa.ifc_route_drawing source.ifc --model project.json --settings examples/circular-elbow/drawing-settings.json --out runs/route-drawing
```

The source-linked delivery plan retains pressure and clash requirements and adds drawing/native requirements. The drawing task takes `model` (original authoring JSON), `settings`, and exactly one of `ifc` or an earlier supported IFC producer through `depends_on`. A later `ifc_native` task may depend on it. All source inputs join workflow integrity records. Unavailable AutoCAD leaves native output pending; a failed drawing producer blocks native execution.

## Geometry and identity

Require one project with explicit unprefixed SI metre units and exact coverage of physical route elements by source device IDs. This reader rejects converted/millimetre units, noncoplanar routes, other equipment and unsupported wall representations. Two ordered projection axes select the common route plane. Oblique/end-on elbows fail rather than becoming chords, circles or invisible lines. General ellipse/hidden-line projection and multilevel drafting remain pending.

The reader checks source object/port GUIDs when a namespace is supplied, names/classes, provenance, space/system membership, port count/positions/directions/outward tangents, actual world bounds and native wall geometry. Straight walls retain hollow-profile, volume and bore checks. Elbows retain exact circular Axis, source-parametric indexed wall, closed oriented mesh, independent wall-volume and through-bore checks. Actual circular length is independently recovered from the saved three-point arc. Drawing geometry comes from checked saved geometry, not solely from plausible metadata.

Actual bounds are an independent gate: translating a straight body along its own axis can preserve diameter, volume and radial checks while connected ports remain in place. A retained failed control demonstrated this gap before adding the bounds gate. The corrected reader rejects the 20 mm shifted body before emitting a diagram; the normal model still passes. Earlier regression results are not relabelled as proof of the added check.

`segments.dxf` contains editable true `ARC`/`LINE` axes on `BSA_PIPE_AXIS`, two OD outline curves per piece on `BSA_PIPE_OUTLINE`, separate leaders and labels. Labels show bore, OD and true length; elbows add radius and angle. Outer curves are planar generic OD silhouettes, not a wall section, insulation envelope or manufacturer product. Every piece-linked entity carries its saved IFC GUID in `BSA_IFC` XDATA. DXF reopening reconciles geometry/rendering attributes, complete handles/identities, units and axis coverage. `segments.csv`, `drawing.json` and `preview.svg` retain dimensions, source hashes, native wall checks and scope. Annotation layout needs actual review for each route.

## Native and printed checks

`ifc_native` accepts finite positive-radius WCS XY arcs alongside lines/text. It rejects invalid/nonplanar arcs and conservatively checks full arc/annotation extents against the window before writes. AutoCAD uses isolated generated copies with exact document-path guards. A separate reopen/export reconciles arc centre/radius/angles/extrusion, other geometry and IFC XDATA. No GUI document is attached or closed.

Physical-scale proof still needs one nonzero source-linked reference `LINE`. The example supplies the incoming 1.5 m axis, A4 landscape, 1:25 scale and 0.2 mm tolerance. A route containing only arcs needs a separately sourced straight reference; an arc chord must not silently replace true length. The actual example measured 59.986333 mm against 60 mm expected. One reference does not establish complete printing or engineering acceptance.

The actual PDF was rendered and inspected. Three axes, six OD outline curves, legible separated callouts and a plane/scope legend were visible without clipping. The first trial's outgoing leader overlapped its axis; the final leader was moved outside the wall. The final native model contains 20 entities, including 18 GUID-linked entities. A separate hash-bound review records only the inspected sheet and does not rewrite the automatic visual-pending field into engineering approval.

Evidence is retained under `docs/evidence/ifc-route-drawing`. Controls cover saved body/axis/unit/coverage contradictions, shifted wall with unchanged ports, changed DXF radius/angle/GUID, wrong projection, clipped labels, invalid arc extrusion and failed-producer blocking. Actual AutoCAD reopen/physical-scale testing requires `BSA_TEST_AUTOCAD=1`.

The retained complete regression passed 231 cases with no skips before the final bounds refinement. After that refinement, all eight route cases passed with actual AutoCAD enabled, and the full four-task delivery workflow was rerun successfully. Separate six-requirement `review.json`/`assessment.json` records pin the source plan, producer Boolean evidence and inspected PDF attachment. `review_checks_pass` records this limited synthetic contract; `design_accepted` remains false. The archive includes actual native artifacts, source snapshots and the intentionally shifted failed-control IFC.

Pending: product/joint/support/insulation detail, formal sheet standards and dimension placement, automatic collision-free annotation for arbitrary routes, oblique/multilevel projections, BIM-viewer review and complete installation/engineering acceptance. This is a checked generic route drawing, not a finished installation design. No new upstream code or dependency was added; existing pinned IfcOpenShell, ezdxf, AutoCAD and PDF adapters retain attribution.
