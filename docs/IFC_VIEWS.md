# Orthographic IFC pipe drawing sets

The `ifc_views` adapter creates two or three distinct orthographic views from saved hollow IFC pipe/duct profiles. Every segment appears in every view as either a true projected axis or an explicit symbolic end-on cross. Every segment must also have a nonzero axis in at least one view. This fills the three-axis drawing gap while preserving the older single-view adapter's strict end-on rejection.

```powershell
.venv/Scripts/python -m pip install -e ".[bim,documents]"
.venv/Scripts/python -m bsa.ifc_views source.ifc --settings examples/water-loop-ifc/views-settings.json --out runs/views
.venv/Scripts/python -m bsa.ifc_views runs/views/views.json --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe' --out runs/native-views
# Full source-quoted model -> water analysis -> views -> native sheets:
.venv/Scripts/python -m bsa.workflow execute examples/water-loop-ifc/views-plan.json --out runs/water-views --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe'
.venv/Scripts/python -m bsa.workflow verify runs/water-views
```

## Explicit drawing contract

Version-1 settings declare provenance, annotation height and end-on marker half-size in metres, a complete unique short ASCII label map keyed by segment GUID, and two/three distinct ordered axis pairs. Each view has its own path-safe ID and sourced native-sheet contract: A4 landscape window, scale denominator, a non-end-on reference segment GUID and PDF tolerance. Full original IFC names remain in the common CSV schedule; labels are explicit callouts, not guessed identities.

Geometry comes from the existing saved-profile reader: direct circular hollow extrusions, placed ports matching profile ends, rigid placements and explicit length units. Every source pipe/duct must be supported and labelled. Equipment/other classes are listed as excluded. The DXF retains metre units and IFC GUID XDATA on each axis, marker, leader and segment label. True profile length and projected length remain distinct. `BSA_END_ON` crosses are symbolic: their size is a drawing setting, never the actual bore/outside diameter.

The example supplies XY, XZ and YZ at 1:50. Six pipes appear as four axis lines plus two end-on symbols in each view. Each pipe has an axis in two views. The 2 m vertical pipes become marked end-on symbols in plan and measurable axes in the elevations; their true lengths remain in labels/schedule. Text height 0.12 m prints at 2.4 mm. An axis-pair view is an orthographic projection, not a developed riser or an isometric drawing.

Each DXF is reopened and reconciled with its in-memory geometry/GUID inventory. A conservative ASCII text-width allowance checks the supplied window before saving; it is not a font or print-quality proof. The manifest reader also rechecks projection facts from recorded source world coordinates, axis/end-on geometry, label/leader positions, identities, source-derived lengths and combined coverage. Artifact/path changes fail before native writes. The manifest's recorded coordinates remain producer evidence; this is not authenticated source certification.

## Native delivery and review

`ifc_views_native` consumes a verified `views.json` manifest or an earlier `ifc_views` workflow producer. Missing AutoCAD or a failed producer leaves the native task pending. It runs the existing guarded isolated Core Console adapter on each view, saves and independently reopens each DWG, reconciles complete LINE/TEXT entity/geometry/layer/GUID identity, then plots the supplied fixed-scale window. Original IFC and input diagrams stay unchanged. It never attaches to the GUI session or closes user documents.

Each view needs its own reference axis. The example's three 5 m references should each print at 100 mm within 0.2 mm. Actual PDF vector positions/lengths are checked independently; a successful CAD command is insufficient. Three individual PDFs are merged with pinned pypdf; page count and decoded page-content streams are checked against the verified source sheets. Actual merged pages must then be rendered and visually inspected. Native records keep visual review pending; a separate source/artifact-bound delivery record stores observed findings and render hashes. [Retained evidence](evidence/ifc-views/README.md).

Outputs include per-view DXF/SVG/sheet settings, a common CSV, coverage/geometry manifest, three native DWGs/reopen exports/PDFs and a merged drawing-set.pdf. These are pipe centreline drawing sets. Overlapping projected geometry, hidden lines, finite fittings/equipment, insulation, drawing borders/title blocks, installation details, product/code applicability and full engineering acceptance remain pending.
