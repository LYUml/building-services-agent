# Native concept facade section sheets

bsa.concept_section takes the exact source-bound native facade revision and creates a horizontal section for every supplied storey, one concept space per storey. It does not replace the original IFC or write to a live user CAD document. Original source/layout/thickness files are required and rechecked; unsupported represented elements reject rather than disappear. The brief's room program, MEP and performance requirements remain unmet.

Reuse decision: the existing IFC pipe-view tool extracts pipe projections, not facade material sections. The thin extension therefore calls pinned Trimesh 5.2.0 mesh_plane on reopened IfcOpenShell world meshes, then existing Shapely 2.2.0 polygonize/topology tools. It reuses ezdxf 1.4.5 and the existing ifc_native/cad_sheet AutoCAD reopening, exported-DXF reconciliation and fixed-scale PDF checks. No section/intersection or CAD engine was rebuilt. Trimesh MIT license is retained at third_party/licenses/trimesh; existing IfcOpenShell/Shapely/AutoCAD notices apply.

Restore parent dependencies:

```powershell
.venv/Scripts/python -m pip install -e ".[section]"
```

After generating a public source/facade workflow, run one variant (all its storeys):

```powershell
.venv/Scripts/python -m bsa.concept_section --ifc runs/public-climate-workflow-v1/workflow/facade-compact/facade.ifc --project runs/public-climate-workflow-v1/compact.json --layout runs/public-climate-workflow-v1/compact-layout.json --facade-basis runs/public-climate-workflow-v1/facade-basis.json --drawing-basis benchmarks/mit-4401-2018/section-decisions/compact.json --out runs/new-compact-sections --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
```

The corresponding slender/stacked decision records select 1:400 / 1:200; compact uses 1:250. Cut height 1.2 m above storey, annotation height and scale are explicit unapproved drawing decisions, not a surveyed section or code mandate. Final paper text heights are 2.4 / 2.5 / 3 mm. Source space-width dimension lines are separately GUID-linked numerical plot references; they do not claim an external wall or clear usable-room dimension. +Y direction is explicitly provisional local orientation, not surveyed site north.

Native mesh/plane intersections are polygonised with an explicit 1e-8 m coordinate rounding/simplification scale for numerical stitching. Open/dangling/invalid linework rejects; there is no physical gap waiver or geometry repair. Saved section areas are independently compared to source wall thickness minus the actual through-opening width at the cut, and window-envelope thickness. A below-window test produces a different continuous wall section and no window intersection, proving this is not a bounding-box projection. Actual source wall corner deficiencies remain visible and labelled unresolved.

Every wall/window section edge, reference, annotation and local-direction graphic is checked in the saved DXF against source-checked native section records. Independent reading verifies exact line/text/GUID coverage, metre units, raw model-space markers, plot-enabled visible layers, by-layer colour without hidden true-colour overrides, ordinary text orientation and source text sizes. Deleted edges, wrong GUIDs, hidden/nonplotting layers, changed notes, white overrides and mirrored text reject. Unsafe storey names cannot escape the output directory. The same audit runs on AutoCAD's reopened/exported DXF; generic native reconciliation additionally preserves model handles/geometry/XDATA.

AutoCAD Core Console operates only on generated copies, checks document identity before saves, writes DWG, reopens it for export and prints fixed-scale A4. The GUI and unsaved user documents are not attached, closed or restarted. Without --autocad, only checked DXF is produced and native_reopen_pass remains false; a DXF success is never DWG acceptance. Actual PDF rendering and visual review are separate gates, not inferred from export success.

Executed final selection: compact Level1/2 and stacked Level1..4 under runs/public-section-native-v1; revised slender Level1/2 under runs/public-section-native-v3. All eight native DWGs reopen, exported vectors/identity pass and PDF references pass. Expected references are 200 mm for compact and 175 mm for slender/stacked; maximum measured discrepancy is 0.0596667 mm, within the explicit 0.5 mm numerical paper-check tolerance. Reference measurements are not physical building tolerances.

All eight final pages were rendered with Poppler and viewed. Level/Z/cut/scale labels, local direction and scope notes are readable and no clipping was observed. Slender text was revised to 2.5 mm with larger line spacing/inset direction label after actual visual review found small text and then a collision in earlier drafts. Superseded outputs remain local; selected final page/hash paths are in evidence/document-intake/native-concept-sections.json and runs/public-section-review-v1/review.json. Models still lack completed room program, slabs/roof, corner joints and actual window products, so these are diagnostic concept sections, not complete architectural or installation drawings.

Nine targeted tests ran: eight passed and one existing optional native test was skipped by its environment gate. Actual eight-sheet native AutoCAD execution was separately completed, so the skip does not stand in for native evidence. An existing IfcOpenShell destructor cleanup warning appeared without test failure. AutoCAD PDF output also emitted duplicate PageMode metadata warnings; the actual pages rendered and scale checks passed, with no archival/PDF-A claim. The broader repository suite is not asserted green.

This module is currently standalone, not yet a registered inherited workflow drawing task. design_accepted stays false; full program/MEP, product/architectural completeness, site orientation, professional analysis, Hong Kong coverage and whole-assignment acceptance remain pending. The old completed electrical project was not used or modified.
