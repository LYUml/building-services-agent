# Planar terminal layout revision

The adapter reuses pinned ezdxf1.4.5 and existing air_terminal_drawing.inspect,
air_tree_flow.aggregate and duct_sheet.snapshot. It updates an explicitly bound
DXF copy;it does not issue live AutoCAD commands or change an open document.

```powershell
.venv/Scripts/python -m bsa.terminal_layout_revision runs/project/source.dxf runs/project/old-allocation.json runs/project/new-allocation.json runs/project/ducts.json runs/project/binding.json runs/project/revision-settings.json --out runs/project/revised-source
```

Settings contains exactly layers,labels and basis. The four distinct layers name
supply,VAV,terminal and flex scopes under the existing terminal inspection
contract. Labels maps every source terminal ID to handle and expected_text;the
text must be exactly that ID and the handle must identify unique modelspace TEXT.
No nearest-text or regex-based identity guesses are made by the adapter.

The drawing hash must match the original sheet binding. Original rigid section
lines,VAV circles,rectangular panel symbols and straight centre-to-centre flex
lines must match the original allocation/tree. Old/new terminal identities,
classified load and turndown are unchanged;both allocations conserve that total
airflow. New flows may redistribute between terminals and original VAV groups.
The new allocation should come from fresh source-backed layout calculation;
this tool does not authenticate its physical assumptions or reconstruct load
calculations. Rerun the actual allocation and schedule in the downstream workflow.

For each position change,only three explicit entities may change:panel XY
vertices,its ID label position and the flex endpoint at that terminal. Opposite
flex endpoints and original VAV/rigid geometry remain fixed. Panel size,style and
label offset remain unchanged. Source entity snapshots prove all unbound
modelspace tags are preserved. The saved DXF is reopened and checked against
expected tags and fresh terminal/group/route correspondence. Reversed flex
directions are supported. No new entities or replacement equipment are created.

Outputs are Supply Air Distribution.dxf and revision.json in a new directory.
Record the new drawing hash in a separate sheet binding,retain the original
schedule cell text/handles,and execute fresh allocation,lookup,sizing,sheet and
native stages. A DXF pass leaves native_reopen_pass=false and plot review pending.
AutoCAD independent reopening and actual plot inspection remain mandatory.

Changed straight plan distances are not installed flex lengths. This tool does
not verify physical VAV ports,ceilings,clearances,fire boundaries,noise,ADPI or
full engineering acceptance. Updated flows can change selected duct sizes even
though the source centrelines remain unchanged. Every original requirement and
unrelated unresolved input must survive the new candidate plan.

Fifteen tests pass across revision,original terminal correspondence and layout
studies. A serialization control exposed ezdxf default elevation/extrusion tags
introduced by polyline translation;explicit XY vertex updates preserve the
source attributes and exact saved-entity check. Native evidence is separate from
these tests. See evidence/terminal-layout-revision.json for actual execution.

Actual source-backed execution revises24 terminal positions and exactly72 bound
entities,preserving all unbound source entities. A new eight-stage package has no
stage errors. Fresh saved native review matches80 terminals,20 four-outlet VAV
groups and47 rigid sections. Maximum straight plan flex distance is2.975724m;
physical installed length remains unknown. Changed load distribution selects new
dimensions for9 sections. Independent review checks all47 sections and16779
candidates. Every original34 requirement and unrelated unresolved input survives.

The23-page report retains388 checked numerical rows and14 ADPI paragraphs. All
pages were inspected in contact sheets,with changed basis/lookup/schedule/source
pages individually inspected;unchanged pages match bound reviewed renders. The
actual native full plot and right-hand connection details were inspected. Three
scoped numerical reviews pass and31 requirements remain pending. A separate
selection record chooses this as the continuing design scenario while retaining
the original baseline. This supersedes only the earlier unselected status for
continued design;full design/ADPI,installation and fire acceptance remain pending.
