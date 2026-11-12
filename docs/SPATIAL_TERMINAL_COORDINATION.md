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
