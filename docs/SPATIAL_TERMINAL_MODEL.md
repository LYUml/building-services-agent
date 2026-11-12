# Exact terminal model consumer binding

Reuse decision: compose existing envelope/inlet producer verifiers and existing
clash/preview engines. No new engine or upstream dependency. A shared
spatial_terminal_model.resolve accepts only terminal-ifc.json or
terminal-inlets.json,verifies their native ancestry,and selects their exact saved
Terminal Envelope Study.ifc or Terminal Inlet Study.ifc. It returns original
terminal identities and complete producer/artifact/method pins. Arbitrary IFC
paths are not a substitute for those verified producer reports.

Coordination and preview now use this resolver. Their terminal_ifc field retains
its historical name but identifies either exact supported producer report.
Existing envelope-only use remains supported;new inlet use reads the actual
augmented model,not its older source envelope. Original findings,full-model
coverage,source-classified port geometry and all unaccepted scope remain intact.

Workflow kind spatial_terminal_inlets inherits an earlier spatial_terminal_ifc
and explicit plan-local basis. Coordination accepts an earlier envelope or inlet
task and verifies the exact declared report filename/path. delivery.context also
verifies inlet task ancestry/status. No original requirement is cleared merely
because logical inlets exist. The public builder accepts --inlet-basis with
--ifc-basis,and binds subsequent coordination to the inlet task when supplied.
No additional runtime path or executable may be supplied by a task document.

Three actual synthetic workflows execute: native and MOOSAS retain11requirements,
create6logical inlets and pass full-model coordination against the inlet file.
Disabled geometry creates no downstream IFC/inlet/coordination;independent
electrical still runs. Manual review stays pending. Two actual previews read6
foreground ports and retain2background ports separately;final PNG bytes match.
The images were inspected:long port legends initially overlapped the footer.
Port owner GUIDs now bind legends to short terminal labels,and bottom margin
adapts to legend rows. Footer overlap is fixed in these samples;side-projection
label overlap remains. Arrows show illustrative outward axes,not SINK airflow
or physical ducts. See evidence/spatial-inlet-workflow.json.

Regression deliberately substitutes a valid envelope-only coordination report
into an inlet-bound workflow. The explicit declared-producer check rejects it,
even though the old report is coherent on its own. This prevents inspecting one
model while delivering another. Logical ports still have no body opening,
physical fitting,duct connection or network continuity. Full installation,
performance,HK applicability,visual BIM and engineering acceptance remain pending.

Validation:8 distinct related tests pass,covering source substitution,gates,
legacy envelope coordination/preview and inlet geometry/identity controls.
Two preview tests were repeated successfully after the final footer/owner-label
change,including source port ownership and image mutation detection.

The resolver additionally supports verified terminal-stubs.json. See
SPATIAL_TERMINAL_STUBS.md for exact new-model consumer and workflow semantics.
Original two-producer notes describe earlier milestones;full acceptance remains
unproven. Producer-declared IFC hashes are checked before returning artifacts.
