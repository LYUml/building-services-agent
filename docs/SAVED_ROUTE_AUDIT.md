# Audit saved route annotations

The route drawing producer now audits the actual reopened DXF after planning and serialization. Its `annotation_layout.independent_saved_audit` result is calculated without calling the annotation planner or trusting that planner's Boolean flags. This closes a demonstrated injected-fault gap: matching planned and saved line segments alone could approve a wrong planner result.

The retained before-control deliberately replaced the planner with a result marked successful whose TURN leader passed through the BRANCH silhouette at X/Z (4.5, 2.74). The old serialization-only checks accepted it. The independent audit rejects the same injected result and no successful layout report is emitted. This was fault injection, not a claim that the normal current planner produced that bad result.

## Standalone use

```powershell
.venv/Scripts/python -m bsa.route_drawing_qa runs/elbow-riser-delivery-v2/model/bim/model.ifc --model examples/elbow-riser/project.json --settings examples/elbow-riser/drawing-settings.json --dxf runs/elbow-riser-delivery-v2/native/native-reopen/source-export.dxf --layout runs/elbow-riser-delivery-v2/drawing/annotation-layout.json --out runs/saved-native-annotation-audit
```

The command reopens and source-checks the IFC with the existing route extractor, then reads the actual DXF. It does not write CAD or invoke AutoCAD. It can check a native reopen/export DXF as well as the original generated DXF. All five input hashes are retained and must remain unchanged. Unsupported or failed checks raise an error; they do not emit a successful audit.

The source rows define full piece coverage, OD geometry and GUIDs. The auditor recomputes anchors and outward escapes, checks every tail against expanded source OD rectangles, checks other bodies against the initial outward stub, detects self-crossings and adjacent backtracking overlaps, and independently measures inter-leader segment distances. Physical overlap along a long segment is measured in model metres rather than being discarded by a fixed parametric-interval cutoff. Coordinates unable to support the 1e-8 m audit tolerance are rejected as unverified.

The DXF must contain exactly the expected GUID-linked leader segments and one matching linked label per piece. Label content comes from the checked bore/OD/length/radius values; positions, height, rotation, alignment, width, obliquing and extrusion are checked. Reversing a LINE's endpoints without changing its geometry is accepted. Missing/extra paths, unknown identity, changed text or placement, lost source anchors and nonfinite coordinates are rejected. Graphic margins remain half the model text height and are unrelated to service or maintenance clearances.

The producer retains its separate serialization/identity checks, then runs this audit before writing the successful layout report. A planner bug that produces an invalid saved path therefore fails the drawing task and cannot be cleared by copying a `true` status. Existing workflow dependency gates leave native output pending after a drawing failure.

## Evidence and limits

The saved audit also rejects hidden linked entities and off, frozen or nonplotting annotation layers. Layer locking is permitted. Raw entity group 67 is checked before ezdxf can normalize inconsistent paper-space markers from ownership; the check accepts ASCII and binary DXF and ignores unrelated paper-space legends. The initial paper-space mutation test failed because the writer repaired the intended fault before serialization. Corrected controls inject and verify the actual raw tag, rather than claiming that an in-memory mutation survived saving.

These are explicit visibility flags, not proof of visible pixels: transparency, colour/plot styles, font glyphs and viewport clipping still require rendering and review. Visibility controls and scoped regression evidence are retained in `docs/evidence/annotation-visibility`.

`docs/evidence/saved-route-audit` retains actual native-export audit evidence, before/after injected-fault records and related regression logs. Tests also cover crossings outside all pipe rectangles, self-crossing tails, label/content/coverage edits, false planner flags, endpoint reversal and numeric clipping boundaries. The standalone test reopens the actual saved IFC and AutoCAD export while the planner is patched to raise if called.

The final related regression passed 33 cases without skips with local AutoCAD enabled: ten saved-audit cases, eight route drawing cases, five annotation routing cases, four independent-riser cases and six workflow cases. This is a scoped related regression, not a new full-repository run. No printed layout was changed by the added audit; native physical-reference tests still execute and actual image inspection remains its own requirement.

The geometric OD reconstruction is shared with the source contract; the search planner and its status claims are not used. This is not a second independent IFC geometry kernel. The scope is linked leader/label geometry and source association. It does not audit arbitrary DXF layers, unlinked legends, font glyph extents or all rendering properties; it does not replace pipe-body/native identity reconciliation, PDF scale/visual review, BIM-viewer review, product applicability or complete engineering acceptance. `design_accepted` remains false.
