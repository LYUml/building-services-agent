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
diameter/angular dimensions, symbol catalogues and MCP/workflow registration are
not yet implemented. The author does not infer engineering topology or dimensions.

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
