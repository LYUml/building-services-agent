# Connection schedule coordinated with the recentered layout

The delivered Connection_Layout scenario now includes its own matching VAV
connection DWG/PDF/CSV. The earlier Agent_Study schedule remains preserved.
This closes a specific cross-deliverable mismatch after moving ten VAV groups;
it does not merge the separate earlier IFC/pressure network scenario.

The composition verifies the existing vav_recenter revision, then reuses
air_terminal_drawing.run on its actual saved/reopened native export, compensated
duct project, revised binding and unchanged allocation. Existing vav_schedule
rows_from/author and duct_sheet_native provide table/calculation/native engines.
No new geometry kernel, sizing solver or dependency is added. Existing pinned
ezdxf1.4.5, fluids1.3.1 and U-C4N/Autocad-MCP attribution remain applicable.
This composition is project-executed, not a newly registered generic MCP tool.

Actual output:20groups/80terminals, with ten groups' planar connection lengths
updated and all memberships/maximum/minimum flows unchanged. Total maximum
flow12000.372763L/s and minimum4800.149105L/s reconcile. Total planar flex is
197.894042m; the longest connection is2.872869m. These are straight XY lower
bounds, not installed lengths or verification of the5m installed-flex criterion.

AutoCAD2027 actually saves and reopens the185-entity table DWG. The actual A4
PDF is rendered and visually inspected: readable rows/notes/reference, no observed
clipping or overlap. Its100mm reference measures100.033667mm. An independent
raw-native inspection converts explicit millimetre drawing units to metres and
reconciles all80flex lines,20flow sums,140native table cells and140CSVcells.
All original source/method pins and the parent recenter revision recheck.

Course files are under03_Design_Drawings/Connection_Layout and
05_Calculations/Connection_Layout. Existing earlier drawings/tables are unchanged.
Actual hardware, port geometry, elevation/slack/bends, installed flex length,
physical coordination, ADPI and complete fan duty remain unresolved. The separate
network study remains30conditional fitting paths/33numerical gaps and must not
be represented as this layout's completed pressure analysis.

Private executed evidence is under
`07_Agent_Work/runs/recentered-vav-connection-schedule`.


The later [recentered network delivery](RECENTERED_NETWORK.md) now integrates
these source revisions into the matching rigid network and native drawing.
Earlier snapshots above remain historical; full pressure/installation acceptance
continues to be unresolved.
