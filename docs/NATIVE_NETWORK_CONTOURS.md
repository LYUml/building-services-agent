# Native DWG delivery of closed network contours

ifc_native now accepts scoped closed LWPOLYLINE outlines beside its existing
LINE/ARC/TEXT diagrams. Contours require finite coordinates, at least three
vertices, simple positive area, zero bulges/width/elevation, WCS XY orientation
and one explicit IFC identity. Shapely2.2.0 validates polygon topology only when
contours are present; existing non-contour diagrams acquire no Shapely runtime
requirement. Existing NumPy/ezdxf, source snapshots, isolated AutoCAD save/reopen,
GUID identity and fixed-scale plot checks remain. No new solver or dependency.

The actual first native reopening exposed NumPy scalar coordinates in the shared
snapshot. Its numeric comparator accepts Python floats but treated those values
as exact objects, rejecting ordinary binary roundoff. This adapter now normalizes
NumPy scalars on both snapshots before the unchanged equivalent comparator.
Existing1e-8 absolute/1e-12 relative bounds are retained; identity/entity/attribute
checks are not waived. The shared overlay module and historical receipts were
not rewritten. Mutation tests retain rejected open, curved, thick, elevated,
self-intersecting and identity-lost contours.

## Real project execution

All286 source contour rings, covering102 native product GUIDs, survive native
save/reopen and independent re-export. Host review annotations are revised on a
separate source-linked DXF copy; its contours remain unchanged. The final drawing
has291 entities,287 identity-linked (286 contours plus the calibration line),
with metre units. Fixed A4 plot1:150 expects a6.6667mm model-reference line and
measures6.6463mm, passing the declared0.3mm check. This is plotted model scale,
not independent confirmation of surveyed building dimensions.

The actual final PDF is rendered and visually inspected: title/notes are legible,
no clipping/overlap, and all three trunk rows, branches and bends are visible.
Assumptions and pressure/product/installation review remain on the sheet. A
separate visual-review receipt binds native record, DWG, PDF, PNG and method
hashes; producer records keep their original pre-review pending status.
Seven native adapter/workflow regression tests pass with no skips, including
actual AutoCAD legacy-diagram reopening/plotting, plus the separate real network
execution. Source models and original diagrams remain unchanged. Native writes
are guarded against the active isolated document path; user GUI documents are
not attached, closed or restarted.

This proves scoped native geometry-study delivery only. Hidden-line semantics,
architectural/installation context, insulation/support/product joints, dimensions,
complete pressure and full engineering/regulatory acceptance remain unresolved.
Private drawings, PDFs and source archives stay in the selected coursework
workspace; public snapshots include code and safe aggregate evidence only.
