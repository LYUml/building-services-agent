# Inherited spatial terminal IFC envelopes

Reuse decision: use the same pinned IfcOpenShell0.8.5 official authoring APIs,
mesh-envelope pattern and native geometry validation already used by bsa.bim.
Reuse box_geometry.box_mesh instead of writing a solid checker. No new engine or
dependency. Existing IfcOpenShell LGPL attribution/license remains in the repository.
The old box-room project builder cannot preserve concave saved rooms,so this thin
adapter adds devices to the original saved IFC instead of recreating its rooms.

`python -m bsa.spatial_terminal_ifc PERFORMANCE --basis BASIS --out NEW` (one line)
requires verified terminal-performance.json ancestry from spatial.ifc-room-recognition.
The exact original IFC source is inherited from the verified recognition request;
no replacement IFC,area,flow or centre is accepted. BASIS covers every terminal
exactly with size_m and bottom_above_floor_m records. Each record has value,unit m,
nonblank source and classification. Sizes are three positive dimensions;bottom is
relative to the inherited room floor. Full envelope footprints must fit the exact
source polygon and their tops must fit the inherited room height. Unknown values
are not supplied automatically. Bounding-envelope dimensions are not product shape.

Output Terminal Envelope Study.ifc preserves every original entity's serialized
forward attributes and original IDs. New IfcAirTerminal objects use stable
source/terminal GUIDs,NOTDEFINED subtype,original IfcSpace containment and exact
maximum/minimum L/s properties. Source-classified geometry basis and selected
product metadata are stored separately. No port,system or physical connection is
invented. Existing unrelated source devices are retained;they are not coordinated
or endorsed by this addition. Terminal GUID collisions reject.

Saved reopening runs full IFC schema/EXPRESS validation,world-native closed-box
mesh bounds/volume checks,complete terminal coverage,source-space containment,
stable identity and source/flow property replay. verify(NEW) repeats those checks
and source/method/output pins. Original IFC files are never rewritten.

Actual native/MOOSAS cases each add six0.6x0.6x0.1m bounding envelopes with explicit
synthetic2.7m bottom elevation. These are design choices/assumptions,not measured
ceilings or manufacturer thickness. Both preserve all original IFC entities,
pass schema/EXPRESS and native geometry checks,and preserve equal keyed
terminal GUID/volume records. See evidence/spatial-terminal-ifc.json.
Visual BIM review,manufacturer fidelity,ports/system connectivity,physical clashes,
installation,ADPI,full regulation/design acceptance and workflow task integration
remain unfinished. Do not call this a complete MEP model.

Validation:28 related tests pass with actual MOOSAS enabled,including saved-body
tampering after rewritten output hash,incomplete basis,unknown source/elevation
rejection and inherited spatial/native source controls.

## Automatic workflow

Task kind spatial_terminal_ifc requires an earlier spatial_terminal_performance,
explicit plan-local basis and optional requires_pass. No replacement source IFC,
flow or geometry is accepted. Missing/nonpassing prerequisite produces no model.
Execution passes after producer and saved-native replay;installation/complete
engineering acceptance is still pending. workflow.verify replays the model and
delivery.context binds exact declared source/basis and passing states.

The public builder accepts --ifc-basis only with explicit performance settings.
--clash-policy requires that IFC basis and adds spatial_terminal_coordination.
It retains all source requirements and adds explicit model/check obligations.
Each generated task depends on the preceding producer and final manual review
requires both. No new geometry/clash solver or dependency is introduced.
See evidence/spatial-bim-workflow.json and SPATIAL_TERMINAL_COORDINATION.md.
