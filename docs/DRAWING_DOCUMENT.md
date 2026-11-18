# General AutoCAD 2D drawing document

Installed shared entry: `bsa drawing run examples/drawing-document.json --out
runs/fresh-drawing --autocad HOST_EXE`, then `bsa drawing inspect
examples/drawing-document.json --out runs/fresh-drawing`. Install `.[drawing]`
first. The same existing dispatch handles all seven documented drawing schemas.
See [clean-install execution evidence](AGENT_USABILITY.md).

All seven schemas are now registered through project task `drawing_document`,
with recipe/model/upstream/runtime bindings, independent native readback and
source-bound delivery review, alongside their standalone/MCP entry. See
[workflow contract](GENERAL_DRAWING_WORKFLOW.md).

The first shared authoring entry is `bsa.drawing_document`. It accepts a declarative
document instead of a duct, electrical or IFC-specific task. It reuses pinned
ezdxf1.4.5 (MIT), existing guarded isolated AutoCAD execution, DWG export and
physical PDF-reference checks. No new drawing kernel or dependency is added.
Upstream dimension and block APIs were checked in the installed pinned source and
[official documentation](https://ezdxf.readthedocs.io/en/stable/tutorials/linear_dimension.html).
Existing U-C4N provider remains useful for source/schedule work; its current
adapter is bound to schedule cells, so it does not implement this document contract.

```powershell
python -m bsa.drawing_document examples/drawing-document.json --out runs/fresh-drawing --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
```

For coursework use explicit host BSA_PROJECT_ROOT and absolute project/output
paths. Documents cannot choose executables. Inputs are preserved and output must
be fresh. DXF-only runs never claim DWG verification. The example is a synthetic
capability fixture, not a completed building design.

Current entities: LINE, straight LWPOLYLINE, CIRCLE, ARC, single-line TEXT,
uniformly scaled/rotated named INSERT and native aligned DIMENSION. Dimensions
retain editable definition points, measurement and effective style; they are not
flattened strokes. Both mm and m are explicit. Entities carry stable IDs, sources
and fact classifications. Blocks are user-declared reusable non-nested symbols.
An A4/A1 model-space frame, title, number and scale reference are composed from
explicit sheet parameters; all coordinates and layout choices are supplied.

Native audits compare model entities, authored symbol contents, units, layer
visibility/styling and effective dimension style. Actual PDF review remains
separate: the first visual trial exposed EZDXF's default dimension multiplier100;
the author now explicitly sets dimlfac1/dimscale1 and the audit rejects changes.
The failed trial is retained. Automatic label placement, arbitrary existing-DWG
editing, paper-space viewports, rich title-block attributes, hatches, leaders,
diameter/angular dimensions, symbol catalogues and workflow registration remain
unfinished. The author does not infer engineering topology or dimensions.

Executed evidence: synthetic plan/system/detail sheet saved/reopened with18model
entities including3native dimensions and one symbol INSERT. Corrected printed
dimensions105/55/30 inspected. The same entry then authored actual BSE3227 saved-IFC
material cuts,132entities and2native dimensions (550/381.07mm), saved/reopened at
1:10; actual final PDF inspected after correcting a view-label collision.50mm
paper reference measures50.038mm in both cases. Four new tests cover invalid
inputs, document mutation, symbol/style/visibility/unit tampering and no-overwrite;
related sheet/overlay tests report10passes/1existing optional skip. Independent
actual AutoCAD execution is not that skipped test. Full engineering acceptance
remains false. See evidence/general-drawing-document.json.

## MCP access

The follow-up registers `bsa_draw_document(project,out)` and
`bsa_inspect_drawing_document(project,out)` in the existing fixed-worker server.
Paths are relative to the host-selected project; AutoCAD is selected only by host
`--autocad`, not by tool arguments or document contents. The writer requires that
host runtime. Inspection does not run AutoCAD: it reconstructs declared entities,
checks source/method/artifact hashes, native entity/symbol/style correspondence
and the actual PDF reference position. Rehashed forged DXF geometry is rejected.
Native/visual/design states remain separate, with design_accepted=false.

Seven targeted tests execute, including actual MCP stdio native drawing and
inspection, no-host runtime, extra runtime arguments, corrupt artifacts and
source/geometry tampering. A separate actual BSE3227 stdio run authors132entities
and2native dimensions; read-only inspection returns the same result. Its rendered
pixels exactly match the previously visually inspected material-section drawing.
This tests an independently started MCP process; it does not assert the desktop's
already-running connection has reloaded the new tools. Unified workflow task
registration and within-view label placement remain open. See
evidence/mcp-drawing-document.json.

## Automatic view packing

The same MCP author/inspect tools also accept `bsa.drawing-layout/1`; example:
`examples/drawing-layout.json`. Define named views containing ordinary drawing
entities, a content window and a paper-space gap in millimetres. The adapter uses
ezdxf bounding boxes including dimension graphics/text, then pinned rectpack0.2.2
MaxRects packing. Views translate only: no rotation, geometry scaling, changed
dimension distance or modified symbol definitions. Reserved title/frame/reference
regions are excluded. Upstream ceiling-rounded rectangle extents and floor-rounded
bin sizes avoid underestimating view sizes. An independent region check rejects
overlap/outside placements. Failure to place every view reports heuristic failure,
not proof that no arrangement exists. Inspection reconstructs the layout and
resolved document from the source before checking native outputs.

Install the optional `drawing-layout` extra. Upstream is Apache-2.0, fixed tag
0.2.2/commit123d57e0ef22adb5ae5f09b435c69f0589f521d1; the PyPI source archive hash
and all nine installed runtime file hashes are recorded in
`third_party/rectpack-0.2.2.json`. The exact-tag license is preserved. No rectangle
packing algorithm is reimplemented. The first no-build-isolation install attempt
failed because this environment lacks setuptools; ordinary isolated wheel build
succeeded from the already hash-verified source archive.

Three new tests pass for deterministic/nonoverlapping placement, retained model
dimensions and input immutability, reserved/too-small windows and altered resolved
documents. Existing five drawing and two MCP tests pass. Actual BSE3227 MCP
author/inspect executes on plan/side/notes views,132native entities/two dimensions;
the actual PDF is rendered and visually inspected without observed view overlap
or clipping. Printed550/381.07mm dimensions and1:10 scale stay unchanged. This is
inter-view approximate bounding-box layout; font substitution and intra-view text
collisions still require separate review. See evidence/automatic-drawing-layout.json.

## Existing DWG text revisions

The same MCP tools also accept `bsa.drawing-revision/1`: an existing recipe-relative
DWG and SHA256, explicit TEXT handles, expected text/layer/insertion point,
replacement text/insertion point and reviewed plot settings. Current scope is
ASCII unaligned unlocked model-space TEXT. Preconditions for all edits are checked
before changing anything. The source DWG is copied/exported by AutoCAD; existing
pinned ezdxf edits only the declared fields, then the existing guarded native
adapter saves/reopens a new DWG and plots it. Original bytes remain unchanged.
No new dependency, CAD engine or security-setting change is introduced.

Preservation covers every saved model/paper/block entity and layer/text/linetype/
dimension-style record using ordered DXF tags. Strings and integers are exact;
floating values use the existing native-adapter1e-7drawing-unit absolute bound,
not an installation tolerance. The actual4609model-entity BSE3227 trial compares
4885records, edits3notes and observes maximum2.91e-11drawing-unit numeric difference.
Paper layouts, architectural blocks and all remaining drawing entities reconcile.
The A1 plot and enlarged notes were actually inspected. The inherited10m reference
is100mm on the1:100 drawing and is checked by the existing plot adapter.
The revision states the ADPI load-band qualification; it does not resolve it or
replace the existing report/main drawing automatically.

Four focused revision tests plus two MCP protocol tests pass, including an actual
native existing-DWG edit retaining symbol blocks and three original DIMENSION
entities. Missing target/position, unintended dimension/paper changes and missing
artifact inventory are rejected. An initial inline-LISP prototype was not adopted:
its malformed/command-reader trials failed, loading its own LISP file was blocked,
and only the verified isolated helper processes were stopped. Those trials remain
private history. The accepted implementation uses the previously verified DXF
writer path; no trust settings were changed. Independent inspection replays source
preconditions and approved edits with exact artifact/method/source binding. It is
not authenticated provenance or complete arbitrary object/dictionary fidelity.

For an existing verified revision, `bsa drawing inspect <recipe.json> --out
<revision-directory> --independent-report <new-report.json>` also compares
the saved DWG with that revision's reopened DXF using the host-configured
ACadSharp worker. The MCP equivalent is `bsa_crosscheck_drawing_revision`
with `project`, `out` and `report`. The report must be outside the revision
directory. The comparison checks drawing units and supported modelspace
geometry and leaves the original receipt and plot review status intact.

Build the optional worker with the host .NET 10 SDK. On Windows, for example:

```powershell
$workerOutput = Join-Path runs "dwg-worker-$([guid]::NewGuid().ToString('N'))"
dotnet build adapters/acadsharp/Bsa.DwgReadback.csproj -p:RestoreLockedMode=true --artifacts-path (Join-Path $workerOutput 'artifacts') -o $workerOutput
if ($LASTEXITCODE -ne 0) { throw 'DWG worker build failed' }
$env:BSA_ACADSHARP_DOTNET = (Get-Command dotnet).Source
$env:BSA_ACADSHARP_WORKER = (Resolve-Path (Join-Path $workerOutput 'Bsa.DwgReadback.dll')).Path
```

Pass these variables in the environment that launches the CLI or MCP server.
Use a fresh build directory for each rebuild so an in-flight CLI, MCP or
regression run keeps its configured binaries. The summary and report include
SHA-256 values for the DWG, the comparison DXF when supplied, the worker and
the loaded ACadSharp library. The report
compares insertion units, modelspace identity, supported geometry, block
reference placement and text display properties. Block definitions, nested
geometry, plot styles and PDF glyph placement require other evidence. For
`POINT` entities, geometry comparison covers the saved XYZ location. For
`LINE`, it covers the endpoints, normal and thickness. Rebuild earlier workers
to include these fields in their inventory. Workers older than schema v3 are
rejected before a comparison report is written.
For `INSERT`, the comparison also checks attached attribute handles and tags,
and text values of single-line attributes. Embedded multiline attribute text,
attribute placement and block definition geometry remain outside this check.
The CLI and MCP summaries report `geometry_compared_count` and
`identity_only_counts_by_type`. The latter counts matched modelspace entities
whose type and layer were checked and whose geometry is outside the comparison.

MTEXT, block-attribute editing, arbitrary geometry revisions, external-reference
packaging, Unicode/font review and general within-view label placement remain open.
See evidence/existing-dwg-text-revision.json.

## Within-view text allocation

The same MCP tools accept `bsa.drawing-labels/1`; see
`examples/drawing-labels.json`. The document is embedded with explicit label IDs,
source target IDs, obstacle IDs, bounds, paper-distance limits and candidate budget.
Targets retain source line midpoints, circle centres, block insertions or polyline
bounds centres. The caller specifies the semantic association; the adapter never
guesses a label's engineering meaning from proximity.

Pinned MIT textalloc1.2.4 allocates actual ezdxf text-box sizes against selected
lines/boxes/anchors. Its lower-level entry avoids substituting Matplotlib font
measurements for CAD boxes. All requested labels must be placed; draw_all=false
and unplaced candidates fail explicitly. Dimensions, source geometry and all
unapproved label fields remain unchanged. The existing route_annotations.path
engine then routes orthogonal LINE segments around other labels and protected
source/native-dimension text. Independent existing clipping and CAD-box checks
reject residual collisions. These are ordinary editable LINE segments, not native
associative LEADER/MLEADER objects. Fixed text is always protected; geometric
obstacles must be explicitly selected. Curve/block boxes are conservative.

The optional drawing-labels extra pins textalloc plus existing NumPy/Matplotlib/
tqdm/packaging versions. The verified PyPI wheel SHA256, all four runtime source
hashes, dependency versions and MIT license are retained under third_party.
adjustText was surveyed but not installed/integrated: textalloc's direct box and
line inputs better match this CAD gap. No allocation algorithm was copied or
rewritten. Exact version/internal API checks are intentional.

Four actual BSE3227 source-linked stage labels execute through MCP, native save/
reopen and independent inspection:143entities,2unchanged native dimensions,
4labels/7leader segments and7protected text boxes. A tighter30mm maximum with500
candidates did not place every label and was rejected; a separate explicit60mm/
1500candidate input succeeds. These are graphic preferences, not duct design
changes. The first actual plot exposed a leader crossing381.07dimension text;
that failed output remains preserved. The revised plot and enlarged dimension
area were actually inspected after adding existing dimension-text extraction and
leader routing. No observed overlap/clipping remains in the examined sheet.
Fourteen focused/related tests pass without skips, including a true native MCP
label trial. Geometry/550and381.07printed dimensions stay unchanged. General
font substitution, Unicode, dense-layout optimality, richer leader objects,
arbitrary obstacles and engineering acceptance remain separate. See
evidence/drawing-label-allocation.json.

## Bounded existing-DWG geometry edits

The existing revision schema now accepts explicit `kind` values `line`, `circle`
and `arc`, alongside legacy text edits. Each edit declares a hexadecimal handle,
expected layer and all source geometry fields, plus all replacement geometry
fields. LINE uses start/end XY; CIRCLE uses center/radius; ARC also requires
normalized start_angle/end_angle. All preconditions are checked before mutation.
Targets must be unlocked model-space entities with supported planar geometry.
Source SHA, native reopening and whole-record preservation remain mandatory.

The actual BSE3227 trial changes three annotation leader segments, preserving
the source anchor and label endpoint. Independent geometry checks show the
approximate dimension-text clearance increases from 8 to 38 drawing mm, or
3 paper mm at 1:10. Both original dimensions remain 550 and 381.07 mm. The
actual whole PDF and enlarged dimension area were inspected. The source drawing
remains unchanged; the derivative is delivered separately as Leader Clearance
Detail. This is a drawing improvement, not a changed HVAC design.

Geometry edits do not recalculate loads, networks or guarantee associative
dimension updates. Polylines, MTEXT and arbitrary object edits remain open.
See evidence/existing-dwg-geometry-revision.json.

## Unified command line

`python -m bsa.drawing_access run PROJECT.json --out FRESH_OUTPUT --autocad "HOST_EXECUTABLE"`
authors any of the four supported schemas through the same engines used by MCP.
`python -m bsa.drawing_access inspect PROJECT.json --out EXISTING_OUTPUT` checks
saved evidence without starting AutoCAD. Set the host environment variable
BSA_PROJECT_ROOT to the explicit external project directory first. Neither a
recipe nor a result file chooses the host workspace or AutoCAD executable.
Unknown schemas fail explicitly. Native run requires an explicit executable;
inspection retains pending visual/design acceptance rather than granting it.
All four existing actual BSE native workflows were checked through this CLI;
see evidence/drawing-cli.json. No new geometry engine or dependency was added.

## Actual current network coverage

The shared CLI now authors the saved 110-body constant-height candidate as an
A4 1:200 coordination plan:301 model entities,294 editable polylines and full
110-product source identity/contour-count coverage after native DWG reopening.
The actual PDF was inspected; its50mm reference measures50.038mm. Existing
source_network_drawing.project and pinned IfcOpenShell/Shapely supply native
material silhouettes; the generic document engine remains discipline independent.
This drawing is separate from the course submission baseline.

This real trial exposed NumPy scalar coordinates in ezdxf polyline records being
compared exactly rather than through the existing numeric bound. Records now
normalize these coordinates to Python float, preserving that bound unchanged.
A regression accepts1e-10drawing-unit noise and rejects a0.01unit vertex change.
The first rejected native run remains private history. See
evidence/current-network-general-drawing.json.

The same110body candidate now also has an A1 1:5 branch-detail sheet through
the shared layout/CLI entry. Ten actual native side cuts cover20saved products;
615model entities include10editable dimensions. Independent saved IFC port
separations match all10reopened DWG dimensions within9.4e-13mm. The100mm
paper reference measures100.034mm. Actual whole PDF and enlarged detail were
inspected after correcting a title-line overlap in a preserved earlier trial.
Pinned trimesh plane intersection, existing IfcOpenShell native meshes, rectpack
and generic drawing authoring were reused without new dependencies. This is
a candidate construction study, not product/full-pressure/course acceptance.
See evidence/current-branch-general-drawing.json.

## Source-bound generic IFC sections

`bsa.drawing-ifc-sections/1` is accepted by the same CLI and two MCP tools.
Install the existing section and drawing-layout extras. The recipe has exact
fields schema, source, ifc, ifc_sha256, layout and views. IFC is recipe-relative,
host-workspace-contained and SHA256-bound. Only metre IFC source models are
supported; layout units may be m or mm. Source originals are never written.

`layout` contains the existing layout fields source, units, layers, blocks, sheet,
content_window and gap_mm. Each view requires id, guids, frame, layer, annotations
and port_dimensions. The4x4 frame is in source world metres: columns0/1 are the
drawing X/Y axes, column2 is the plane normal, and column3 is the origin. A finite
right-handed orthonormal frame is mandatory. Every selected represented product
must intersect the plane; empty views are rejected rather than silently omitted.
Annotations are existing explicit drawing entities in local plane coordinates.

Each port dimension requires id, ports(two GUIDs), layer, distance and text_height.
Both ports must belong to selected products and lie within1e-8m of the plane.
The author derives definition points from saved native port placements; distance
is the caller's dimension-line offset in output units. This avoids copying a
length into dimension text or inventing installed dimensions.

Pinned IfcOpenShell0.8.5 native meshes, trimesh5.2.0 mesh_plane and NumPy2.5.4
are reused with existing rectpack/layout/document/native adapters. No geometry
engine was reimplemented. Inspection regenerates all cuts and dimensions from
the current source, validates source/method/runtime binding and the nested native
artifacts. This can be more expensive than merely reading a manifest. It does
not perform hidden-line removal or accept engineering correctness.

Actual BSE3227 MCP execution and independent inspection cover10views/20products/
10editable dimensions, all checked against saved native port separations. The
actual A1 PDF and enlarged detail were inspected. Eleven related tests pass,
including mirrored/skew frames, missed sections, off-plane ports, changed source
SHA and resolved-output tampering. The existing desktop connection was not
reloaded. See evidence/generic-ifc-section-drawing.json.

Views may now explicitly set kind=projection; omitted kind retains section.
Projection transforms the saved world mesh into the declared orthonormal frame
and reuses source_network_drawing.project's pinned Shapely2.2.0 material union.
Exterior and interior rings become editable closed polylines with product IDs.
This is a tessellated silhouette, not a section or hidden-line drawing. Port
dimensions retain the same in-plane restriction, avoiding a foreshortened length
being presented as actual3D separation. Both modes can share one layout recipe.

The actual110body candidate plan now executes directly from its source IFC via
MCP and independent inspection. All110source identity/contour counts reconcile;
independent native mesh extent checks, after removing sheet translation, differ
by at most4.71e-9m. The actual A4 PDF was inspected. Twelve related tests pass,
including projection-normal translation invariance and unknown-kind rejection.
The old private projection script is no longer needed to execute this recipe.
See evidence/generic-ifc-plan-drawing.json.

## Actual system-schematic trial

The current110body candidate now also has a directed source topology schematic.
Existing evaluated Graphviz13.1.2(executable hash ff1ce5f13caf4ed7dddb7327b94781e751e4a7e693b4655287b6647d959c879a),
ezdxf Bezier utilities and the generic drawing entry are reused. Native IFC
links yield109directed interfaces; prescribed_flows reconciles all239ports
against the inherited current analysis. Saved native output retains110node
labels and109arrowheads. One inlet and20outlet boundaries exactly match the
pressure ledger. A component-key CSV binds short diagram IDs to native GUIDs,
source names, inherited flows and numerical-gap flags.

Five marked products account for11numerically unresolved fitting paths. Their
outlet coverage is20,12,6,1,1 respectively; coverage is not hydraulic criticality.
The actual A1 whole PDF and enlarged area were inspected after enlarging the
schematic paper layout for readability. Paper geometry has no route-length
meaning. Full pressure and engineering acceptance remain open. Topology-to-
document preparation still uses a project script; this evidence does not claim
a general schematic MCP adapter. See evidence/current-system-schematic.json.

## Generic declared system graphs

The same CLI/MCP now accepts `bsa.drawing-graph/1`; see the explicitly synthetic
`examples/drawing-graph.json`. The recipe requires source, source_files, nodes,
edges, layers, sheet, notes and layout. Source files use recipe-relative path
and SHA256 pairs, constrained to the host workspace. Nodes declare id, label,
layer, source and classification; edges declare id, from, to, layer, source and
classification. The adapter validates identity coverage and declared endpoints;
it does not infer engineering topology from file contents.

Layout explicitly supplies origin, factor, node_width_mm, node_height_mm,
text_height_mm, ranksep_mm, nodesep_mm and rankdir(LR/TB). Nodes are boxes with
ASCII single-line labels; labels that do not fit fail. Paper coordinate scale
is1:1 and has no installation-length meaning. Notes are ordinary declared text
entities. Sheet containment is checked against reserved margins.

Run with the existing evaluated host Graphviz executable as well as AutoCAD:
`python -m bsa.drawing_access run PROJECT.json --out FRESH_OUTPUT --autocad HOST_AUTOCAD --graphviz HOST_DOT`.
For MCP, Graphviz comes only from server startup --graphviz; neither recipes nor
tool arguments can choose executables. The existing desktop server was not
restarted/reconfigured. Pinned Graphviz13.1.2, existing ezdxf Bezier4P flattening
at0.01paper mm and native drawing adapters are reused; no layout algorithm or
new dependency was introduced.

Inspection checks source files, recipe/method/artifact binding and regenerates
editable entities from the saved Graphviz JSON. It checks every node/edge identity
and endpoint mapping. It does not rerun Graphviz or authenticate its provenance.
Source interpretation and actual visual/engineering acceptance remain separate.

Actual BSE MCP author/inspect execution covers110nodes/109edges. Reopened labels
and arrowheads match the recipe, and a separate host check reconciles all edges
against the saved native IFC connections. Actual whole PDF and enlarged detail
were inspected; all5numerical-gap marks remain. Eight targeted/related tests
pass, covering changed source, swapped endpoints, geometry tampering, label fit
and missing runtime. See evidence/generic-system-graph-drawing.json.

## Directed system graphs from saved IFC

`bsa.drawing-ifc-graph/1` extracts native port relations before calling the
existing declared-graph adapter. It uses the same CLI/MCP entry and host
AutoCAD/Graphviz configuration. The recipe has exact fields schema, source,
ifc, ifc_sha256, products, marked_products and graph. IFC paths are recipe-
relative, host-workspace-contained and SHA256-bound. IfcOpenShell0.8.5/IFC4
are required. Select an explicit unique GUID list or products=all_distribution.
Every selected distribution element must have uniquely owned SOURCE/SINK ports.
Bidirectional/unknown directions and multiple peers per selected port fail.
No direction is guessed from element names or coordinates.

The graph base supplies existing source/source_files/layers/sheet/notes/layout
fields plus node_layer, marked_layer and edge_layer. The IFC source is bound
automatically; additional source_files must not repeat it. Marked products are
explicit caller-declared highlights within the selected scope, not inferred
pressure or engineering failures. Nodes receive N-prefixed labels sorted by
GUID; those labels are stable only for the same model/selection. Native GUIDs
remain the persistent identity. Component Key.csv maps labels to GUIDs/names.

Relations with both endpoints selected become directed edges. Connections to
unselected products are retained as external_selected_connections, separately
from genuinely open_boundary_ports. Cropping a graph therefore does not turn
connected ports into unconnected model boundaries. Inspection reextracts this
source topology, validates the resolved graph and exact component-key bytes,
then replays the existing stored Graphviz/native drawing checks. No coordinate,
material/contact, fluid/electrical calculation or pressure validation is implied.

Actual BSE execution through an independently launched MCP process extracts
118products/255ports/117interfaces,1open inlet and20open outlets. A separate
raw IfcRelNests/IfcRelConnectsPorts reconciliation matches every ownership/link
and open boundary. Reopened118node labels/117arrowheads and118component-key
rows agree. Actual whole A1 PDF and enlarged area were inspected. Eleven related
tests pass, including ambiguous flow, changed source, explicit cropped scope
and component-key tampering. The4compound pressure gaps and ADPI basis decision
remain unchanged. Desktop server configuration was not reloaded. See
evidence/native-ifc-system-graph.json.

## Reusing repeated IFC geometry during drawing composition

The source-bound IFC drawing adapter now caches exact forward representation values plus complete forward representation-context values within one immutable composition. It reuses pinned IfcOpenShell local meshes, verifies the kernel transformation against the native product placement, and applies each original placement. Inverse opening geometry prevents sharing across products. Projection reuse additionally requires an exactly equal local viewing normal; the adapter proves the remaining transformation is an in-plane rotation and translation. Mesh deflection, source selection, units and source hashes are unchanged. No persistent cache or invented geometry is introduced. Build counts are recorded with source coverage.

The existing Shapely triangle-union projection and its cleanup displacement/area bounds remain. The original strict default rejects failed cleanup. The IFC composition explicitly requests retention of a valid original raw polygonal union when cleanup exceeds that bound, and records every affected view/GUID in raw_projection_products. It never adopts the failed cleaned polygon or silently increases the bound. Raw tessellation seams may remain and require actual plot review. The source/default caller behavior is unchanged.

Nineteen related tests pass, including repeated equivalent representations with distinct STEP/context identities, translated/rotated native world-projection correspondence, and strict rejection versus explicitly recorded raw retention. Actual full598product execution now saves/reopens in AutoCAD;19related tests and independent source reconstruction pass. No complete engineering acceptance follows. Historical native receipts remain tied to their original method hashes.


Drawing recipes may additionally declare mesh_quality with exactly source, classification=design_target, linear_deflection_m and angular_deflection_rad. Values must be positive finite numbers, and the angle must not exceed pi radians. Omission retains the original fine mesh settings. This is a drawing-only target; source IFC, native port dimensions and analysis mesh settings are unchanged. The actual full-plan trial selects0.0001m/.05rad, nominally0.0005mm model deflection on1:200 paper. One actual toroidal bend has64,512faces versus402,560at the inherited fine settings; curved-face-centroid surface error is0.0352mm and relative material-volume discrepancy0.0207percent. This sample is not whole-model or analysis-mesh acceptance.

The explicit reviewed projection path also excludes positive projected triangle areas no greater than a conservative32*machine-epsilon*max-coordinate-squared arithmetic envelope. Omitted count, total area and bound are recorded per view/GUID through projection_review_records. The formerly failing actual tangent excludes992roundoff faces totaling1.50e-17m2 and retains a valid polygon. Strict default callers do not use this filtering. Raw union uses upstream floating-precision GEOS union; cleanup still uses and verifies the original grid/bounds. These numerical checks do not replace actual native/visual review. Full-plan execution and source reconstruction now pass. Actual whole PDF and four enlarged raw-projection regions are reviewed; note overlap is fixed and minor tessellation seams remain. Native598GUID/12,904contour counts and per-product bounds agree. This is a CLI execution; the desktop MCP process was not reloaded. See evidence/current-full-network-drawing.json.
