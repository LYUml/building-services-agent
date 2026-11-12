# Source-bound terminal envelope coordination

Reuse decision: directly compose existing clash.inspect and solid_clash.overlaps.
IfcOpenShell0.8.5 triangle intersection/clearance and Manifold3D3.5.4 Mesh64
Boolean supplement remain authoritative. Pin both methods plus contact_clearance
and their existing configuration method. No new geometry engine or dependency;
existing upstream licenses/attribution remain in place.

`python -m bsa.spatial_terminal_coordination TERMINAL_IFC_REPORT --policy POLICY
--out NEW` (one line) requires verified terminal-ifc.json. The exact saved IFC is
inherited from that producer;replacement models and terminal inventories are
not accepted. POLICY is the existing sourced clash policy schema. Outputs stay
in the repository or explicit selected project workspace. verify(NEW) rechecks
original IFC authoring ancestry,pins,full native clash calculation and summaries.

The entire existing all-represented-physical-elements scope runs. Raw findings,
coverage issues,unverified solids and accepted source-policy contact exceptions
remain intact. A summary partitions findings into terminal-terminal,
terminal-existing and existing-existing,using verified added GUIDs. It does not
waive existing findings or accept the design. Whole-model failure remains fail
even if no new terminal is involved. Geometry-coverage failure also prevents a
calculated pass. IfcSpace room volumes are not physical clash objects;original
room containment/footprint checks remain in the authoring producer.

Actual native/MOOSAS source chains each inspect eight represented physical
elements,six added terminals and28potential pairs. Geometry coverage,intersection
and clearance pass under an explicit synthetic50mm clearance/0.1mm intersection
policy with no allowed contacts. This is not an official HK rule,maintenance
clearance or installed-product check. A deliberate overlapping-terminal control
fails;rewriting/removing its findings is rejected by native replay. A separate
control confirms original-only collisions still fail the whole model.
See evidence/spatial-terminal-coordination.json.

Manufacturer/insulation geometry fidelity,actual ceiling/obstacle completeness,
policy applicability,ports/network connectivity,BIM viewer review and complete
engineering acceptance remain pending. Workflow-task integration is unfinished.

Validation:17 related tests pass,including existing hollow-bore,containment,
connected-contact and finite-elbow native regressions,as well as new overlap,
original-only failure and tampering controls.

## Automatic workflow

spatial_terminal_coordination inherits an earlier spatial_terminal_ifc and exact
plan-local policy. workflow.verify/delivery.context replay complete native data,
validate producer/policy identity and require task status to equal full-model
calculated status. Failures remain fail;they do not become a completed pass.
Existing requires_pass gates prevent intended dependent work after failure.

Actual native/MOOSAS workflows execute recognition,selected HK lighting check,
classified air balance,terminal allocation,source catalogue query,editable DXF,
IFC envelopes and whole-model coordination. Both retain10requirements and pending
manual review. Disabled geometry creates neither terminal model nor coordination,
while independent electrical still executes. A real overlapping-envelope workflow
control retains coordination fail. No IFC viewer/installation/network acceptance
is inferred from these synthetic runs. See evidence/spatial-bim-workflow.json.

Workflow regression:23 related tests pass with actual MOOSAS enabled,including
clear/disabled/real-overlap complete workflows and source/native tamper controls.

Exact inlet-model workflow/consumer integration is now executed;see
SPATIAL_TERMINAL_MODEL.md and evidence/spatial-inlet-workflow.json. Earlier
pending-integration notes describe prior milestones,not complete design acceptance.
