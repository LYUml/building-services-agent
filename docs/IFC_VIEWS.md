# Orthographic IFC pipe drawing sets

Optional annotation_mode:keyed-schedule replaces straight leaders with numbered
tags near the source projections and matching full parameter rows. Numbers are
deterministic from source GUID order;original callouts/names and true lengths
remain in the schedule. It supports the existing end-on glyphs without sending
zero-length axes through a finite-pipe leader router. The default legacy settings
remain structurally unchanged.

The small graphic adapter reuses route_annotations.expand and the existing
ezdxf/native pipeline. It searches20 bounded candidate positions per tag against
conservative projected pipe/symbol rectangles,parameter/title regions and other
tags. Those are graphic avoidance bounds,not physical/service clearances. Failure
to find a clear position raises rather than placing an overlapping tag. It is
not a general annotation optimizer or a proof of unambiguous physical installation.

The saved-DXF verifier checks exact tag-to-GUID/parameter identity,placement,
height,width/rotation and independently reads tag boxes against graphic regions.
Both helper method hashes are required in the manifest and selected workflow
inputs. Updated file hashes cannot clear a moved/reassigned/resized tag. Actual
PDF inspection still remains mandatory.

The public circulation settings now select this mode. Actual gated native
authoring/water/HK checks →2DWGs/reopens →2pages at1:30 execute. Both rendered pages
were inspected:the prior crossing leaders are absent,all four tags match their
parameter rows,and no clipping/overlap is visible. The scoped presentation review
passes;whole engineering/installation acceptance remains false. 14 targeted
invocations:13pass,1optional native test skipped;actual2view native execution is
separate from that skipped test. See evidence/keyed-view-tags.json.

The view adapter can also inherit a completed common model artifact from an
earlier module_authoring task. See examples/modular-drawing-plan.json and
MODULES.md. Actual native authoring →3views →3DWGs/reopens →3plotted pages is
verified within the existing centreline-only scope;hydraulic analysis and full
engineering review remain separate. No provider filename is assumed.

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
