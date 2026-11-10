# Whole source-tree centreline studies

`bsa.duct_system_paths` reuses saved-native drawing correspondence and the
selected duct schedule to enumerate every source inlet-to-leaf path. It replays
the existing equivalent-round/Colebrook friction method with pinned fluids1.3.1.
It does not author another network or infer actual installed fitting dimensions.

```powershell
.venv/Scripts/python -m bsa.duct_system_paths runs/source-plan.json runs/source-workflow native-task-id --out runs/system-path-study
```

The plan must belong to the saved workflow,with passing native-sheet→sheet→
schedule ancestry. Existing delivery.context verifies requirement contents,
execution/artifact correspondence and input hashes. Existing duct_junction_review
reopens the saved native-export DXF and binds exact LINE handles,units,endpoints,
nominal dimensions and source design flows. Source documents,all recorded
artifacts/runtime inputs and method files are protected against changes. A changed
source during calculation blocks the final report;partial source-review evidence
is retained separately in the new output directory. Originals are not modified.

Every unique source section must agree with its two directed node incidents.
Native-derived source centreline length is checked against those incidents;
selected friction gradients must match a fresh method replay. One-parent tree
topology,node/boundary flow conservation and exact leaf/section coverage are
required. Parallel paths remain separate;shared upstream sections may appear in
several paths but are never silently summed into a fan duty. Each path retains
ordered section/node identities and unresolved internal connection requirements.

The numerical quantity is **nominal untrimmed source-centreline friction**.
Fitting reaches have not been deducted and fitting-body friction conventions are
not established. Physical straight length/friction fields and complete path
pressure remain null. Do not combine this baseline with the trimmed local-chain
study or treat it as a conservative pressure bound. Fitting,equipment,flexible
duct,terminal,boundary,balancing,installation and local-code scope remain open.
There is no inferred fan critical path or hardware selection. The inherited air
conditions,flows and nominal sizes retain their preliminary design/assumption
interpretation;source CAD lengths are not site measurements.

Outputs are junction-review.json,system-paths.json and a readable index.html.
The exact original interpreted-plan requirement records and acceptance states
are retained,without claiming that the interpreted plan omitted no brief content.
CLI exit2 and pending status reflect incomplete pressure/design acceptance.
The host agent can call this postprocessor after an existing saved native
workflow;it is not registered as a task that consumes an unfinished workflow.
For single-invocation preparation,add --system-paths-native-task with the declared
native sheet ID to bsa.hvac_package. It runs this study after completing its new
workflow,and retains pending scope,errors,artifact hashes and an index link.

Actual private execution covers47 source sections,48 nodes and20 paths to the
original VAV leaf nodes,with all34 original requirement records retained. The
downstream80 diffuser/flexible-connection paths are not inferred from these20
leaves. Full pressure and original acceptance remain pending. Five targeted
methods cover the new source-path/mutation controls and existing saved-drawing
connection regressions. Independent two-outlet controls check shared-path
accounting,known source lengths,nominal scalar sums and rejection of stale
gradients/incidents/topology/leaf flows. Mocked mutation controls are source-boundary
tests,not native AutoCAD evidence. Public aggregate evidence is in
evidence/duct-system-paths.json;private source/workflow/report data stay local.
