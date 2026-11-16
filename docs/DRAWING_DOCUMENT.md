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
