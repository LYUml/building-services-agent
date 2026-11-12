# Source-bound terminal IFC visual diagnostic

Reuse decision: extend existing ifc_preview.extract/run,using pinned
IfcOpenShell0.8.5,Matplotlib3.11.2 and NumPy2.5.4. No new renderer,viewer or native
geometry engine. Existing upstream licenses/attribution remain unchanged.
The generic preview adds optional context_guids and element_labels. Opaque blue
foreground and transparent grey context use the same native saved meshes.
Context ports remain in context_ports_not_drawn;only foreground ports draw arrows.
Labels must be short,nonempty and belong to selected GUIDs. Existing positional
arguments and the original no-context path remain supported.

`python -m bsa.spatial_terminal_preview TERMINAL_IFC_REPORT --out NEW` (one line)
requires verified terminal-ifc.json ancestry. All added terminals are foreground;
represented original IfcSpaces/IfcElements are background. Unrepresented objects
remain in omitted metadata,not silently represented by fabricated meshes. Short
Txx labels map to full source terminal/space GUIDs in terminal-preview.json.
Output overview/preview.png contains isometric,XY,XZ,YZ projections. No IFC file
is changed. Existing twelve-port and triangle budgets remain explicit limits.

verify(NEW) replays original model verification,selected roles/IDs,mesh inventory,
world bounds,origin,foreground/background port records,omitted objects,runtime
and all source/method/image/report hashes. It does not prove correct pixels or
visual acceptance;actual image inspection remains necessary.

Actual native/MOOSAS source chains each show six terminal envelopes,five original
represented context objects and two retained background ports. Foreground has
zero ports. The final rendered PNG bytes match across both chains. The final
image was inspected:all six envelopes can be distinguished in isometric/XY views;
some labels overlap in side projections. Original first-trial background arrows
were identified as potentially misleading and hidden without deleting metadata.
The final legend explicitly separates solid foreground,transparent context and
hidden original ports. See evidence/spatial-terminal-preview.json.

This is a selected saved-geometry diagnostic,not independent BIM-viewer
acceptance,hidden-line drawing,manufacturer geometry,connected MEP installation
or complete engineering design. Per-room zoom/label collision handling,IFC viewer
review and automatic workflow-task integration remain unfinished. Producer
visual_review/design_accepted stay pending/false.

Validation:two focused tests pass on final rendering code,including original
millimetre/rotation/port geometry,complete context/foreground binding and image
mutation rejection. A four-test IFC/preview regression also passed before the
final legend-only change.

Exact inlet-model workflow/consumer integration is now executed;see
SPATIAL_TERMINAL_MODEL.md and evidence/spatial-inlet-workflow.json. Earlier
pending-integration notes describe prior milestones,not complete design acceptance.
