# Native source-network XY drawing

source_network_drawing reuses source_network_analysis.verify and the saved model,
IfcOpenShell native world-coordinate tessellation, Shapely2.2.0 union_all and
pinned ezdxf. Existing rectangular_drawing requires its separate device schema
and supports only bounded profile types; it cannot consume the verified compound
network directly. This thin adapter closes that native-body coverage gap without
rebuilding a geometry engine. Existing Shapely/GEOS notices apply.

Each projected triangular material face enters a per-body Shapely union. A
separate1e-8m numerical precision grid removes tessellation seams. The cleaned
silhouette and raw filled projection must cover each other after a2e-8m
set offset (not a ring-vertex Hausdorff comparison)
and within2*raw_perimeter*grid+4*grid^2 area difference. These are computational
bounds relative to tessellation, not fabrication or survey tolerances.
Zero-area edge-on projections contribute no area.
Disconnected polygons and holes survive. Every saved distribution element must
match the analysed product GUID set. All contour rings become editable closed
DXF polylines with BSA_IFC identity. Product names are descriptive only; duplicated
names do not collapse bodies. The saved DXF is reopened and exact GUID coverage
checked. Source model, analysis and method bytes are retained unchanged.

The result is an XY silhouette study in metres. It is not an architectural plan,
installation layout, hidden-line drawing or evidence of surveyed source scale.
Native tessellation approximates curves; existing elevation, nominal clear-size
and wall-gauge assumptions survive. Joint/insulation/support/equipment envelopes,
room/ceiling context, labels/dimensions and full coordination/design acceptance
remain open. A source-linked 1m reference and explicit review sheet settings are
provided. A DXF result does not establish native DWG reopening or PDF plot review.

Use explicit host BSA_PROJECT_ROOT for coursework and a fresh output outside the
immutable source analysis:

```
python -m bsa.source_network_drawing SOURCE_ANALYSIS --out FRESH_DRAWING
```

Reuse reference: https://shapely.readthedocs.io/en/stable/reference/shapely.union_all.html
No new dependency, source drawing edit, external application restart or source
archive redistribution is introduced. The general native diagram adapter currently
accepts LINE/ARC/TEXT only; these closed polylines need a separately verified
native handoff before any DWG acceptance claim.

The first numerical cleanup trial correctly blocked export under its original
check, but diagnosis showed discrete ring Hausdorff distances include eliminated
internal seam vertices. Fifteen bodies failed that boundary metric while all
passed mutual filled-set offset coverage and the original area bound. The final
method uses those set checks without increasing the2e-8m displacement allowance.
A remote tiny component that would disappear under snapping rejects in tests;
ordinary disconnected components remain. Original zero-grid and failed trials
are preserved as internal provenance, not submitted revisions.

Actual source replay exports all102 products with286 contour rings. Independent
saved-DXF GUID, closure, shoelace area and native-bound checks pass for every
product; maximum axis-bound difference is1.52e-9m. All33 requirement IDs remain.
The complete preview is visually inspected for geometry coverage/clipping.
Three tests pass, covering non-box silhouettes, disconnected components, seam
cleanup, lost remote features and invalid meshes. The final source run and its
numerical checks are distinct from the preserved earlier attempts. Native DWG
reopening/plotting, professional annotations and installation acceptance remain
pending. The preview and DXF stay in the private selected project workspace.
