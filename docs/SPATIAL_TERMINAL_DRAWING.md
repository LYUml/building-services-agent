# Source-bound terminal airflow schematic

Reuse decision: use installed pinned ezdxf1.4.5 (MIT,existing upstream attribution
and license) with existing verified spatial allocation/balance/provider replay.
No new CAD engine. Preview uses existing ezdxf Matplotlib backend3.11.2;it does
not count as native AutoCAD verification.

`python -m bsa.spatial_terminal_drawing ALLOCATION --settings SETTINGS --out NEW`
(one line) requires the exact verified terminal-allocation.json and explicit
settings containing annotation_height_m (.001 to1m) and nonblank source. This
height controls annotation only. Sources and output must stay in the repository
or explicit selected project workspace. Existing output and source overlap reject.

Output Terminal Airflow Schematic.dxf uses metres,source world-XY room outlines,
POINT centre symbols and separate terminal-ID/maximum-minimum flow labels in L/s.
No panel dimension or terminal mounting elevation is invented. Room floor levels
are annotated separately;the diagram is a projection,not a physical ceiling plan.
Short labels bind back to complete source room and terminal IDs in drawing.json.
Floors with overlapping XY extents are not automatically separated. Text placement
is a fixed schematic offset,not a collision-avoidance or sheet-layout engine.

Saved DXF inspection replays complete entity inventory,closed room boundaries,
centre coordinates,flow text,units and source ID bindings. Unexpected entities,
changed source/output bytes and altered coordinates/text reject. The report is
source/method pinned and design_accepted/native_reopen_pass remain false.
Preview inspection does not clear the report's pending native plot review.

Actual synthetic native/MOOSAS cases each generate three rooms,six terminals and
24entities. Both saved drawings match their own inherited source geometry/flows.
Boundary vertex sequence differs between providers,so entity-record equality is
false;do not claim byte-identical CAD. Both PNG previews were inspected after
shortening identifiers,separating ID/flow lines and increasing annotation height.
The first tiny/long/yellow labels were rejected during visual iteration.
See evidence/spatial-terminal-drawing.json. Native DWG save/reopen,actual AutoCAD
plot review,duct routing,ADPI,installation and complete engineering acceptance
remain unfinished. This is a source-bound editable schematic,not a full HVAC plan.

Validation:28 related tests pass with actual MOOSAS execution enabled,including
saved-DXF coordinate tampering after a rewritten output hash,source replay and
complete candidate workflow regressions.

## Automatic workflow integration

Use kind spatial_terminal_drawing,depends_on an earlier spatial_air_allocation,
and explicit plan-local settings. Geometry or flow overrides are forbidden.
The public examples/moosas-transform/build_workflow.py accepts --drawing-settings
with --air-balance --terminal-allocation. It adds an explicit sourced brief
requirement and manual-review dependency. The drawing uses allocation,not product
footprints;optionally require product performance with requires_pass if the
specific project demands that gate. Range failures do not invent geometry.

Execution inherits the exact saved parent allocation. Upstream pending/failure
creates no drawing. workflow.verify replays saved DXF evidence;delivery.context
also enforces declared parent/settings and passing dependency status. Saved DXF
correspondence can pass the scoped task while native reopening,plot review and
engineering acceptance stay pending in its report and final manual review.

Three actual six-terminal workflow scenarios execute: native and MOOSAS produce
the source-bound drawing;disabled geometry produces none while independent
electrical still passes. Eight requirements remain fully represented and manual
review stays pending. See evidence/spatial-drawing-workflow.json. No actual
coursework data or files were modified for this integration.

Integration regression:30 related tests pass with actual MOOSAS execution enabled,
including drawing task gating,forbidden overrides and wrong-parent rejection.
