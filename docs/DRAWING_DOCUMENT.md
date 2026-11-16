# General AutoCAD 2D drawing document

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
