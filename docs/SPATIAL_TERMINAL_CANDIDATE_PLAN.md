# Candidate to complete workflow plan

Reuse decision: compose existing candidate.verify,workflow.validate_plan and
source-linked delivery.context. No new solver or upstream dependency. Existing
allocation,fluids1.3.1 and source provider licenses/attribution remain in place.

`python -m bsa.spatial_terminal_candidate_plan PLAN CANDIDATE --task TASK
--target NEW_PLAN` (one line) materializes a previously studied explicit terminal
candidate. NEW_PLAN must be a fresh JSON path in PLAN's directory. Only the
selected spatial performance task's product basis and its allocation parent's
terminal basis change. All original tasks,dependencies,requirements,brief and
unresolved-input register are retained. The original workflow ancestry must
validate against PLAN before materialization. Original files are untouched.

Only declared candidate product settings,source and catalogue are copied into
a new adjacent input directory. Original private directories are not bulk copied.
A .provenance.json records original/candidate pins and generated file hashes.
verify(NEW_PLAN) rechecks ancestry,exact plan changes,geometry and product
semantics,source hashes and complete copied output inventory. The new plan uses
the existing workflow.execute/verify and delivery.context interfaces. Execute
it into a new run;manual acceptance is not transferred from the original.
Partial failed materializations remain diagnostic;retry with fresh paths.

Actual native and MOOSAS runs of the same synthetic six-terminal candidate both
pass recognition,selected HK lighting arithmetic,air balance,terminal allocation,
terminal catalogue performance and independent electrical calculation. All seven
original requirements remain;manual review remains pending. Geometry/flows are
synthetic controls;room loads,ADPI,acoustics,routing,installation,full HK compliance
and complete engineering acceptance are not established. No native CAD is written.
See evidence/spatial-terminal-candidate-plan.json.

Validation:27 related tests pass with the real MOOSAS runtime enabled,including
full candidate-plan execution,exact preservation and provenance tampering checks.


## Explicit downstream geometry transfer

Optional `--geometry-policy POLICY.json` lets a studied candidate with new
terminal IDs continue through the existing downstream IFC-envelope, inlet and
short-stub tasks. Reuse the existing source-linked plan factory and authoring
engines; no new geometry kernel, fitting solver or dependency is introduced.

The policy has exactly source, classification=design_choice and
from_terminal_by_room (source room GUID -> original terminal ID). Every room
must be covered and each reference must belong to that same original room.
Omitting the policy retains the existing behavior and transfers no geometry.
An explicit policy with no supported downstream tasks rejects.

Only supported descendants of the selected performance task receive new basis
files. Numerical values, units and system declarations are copied from the
explicit original template, with sources preserved in a new reuse statement.
New assignments are classified design_choice; original records/classifications
are retained separately in geometry_bindings in the provenance manifest. No
original measured classification is promoted to a new-location measurement.
Unclassified originals, missing templates and cross-room references reject.

The factory reconstructs new-ID coverage from the verified candidate allocation,
pins policy and original basis bytes, preserves all unrelated task/basis fields,
requirements and unresolved inputs, and verifies generated records against the
original templates. A new full run remains mandatory; old manual acceptance is
not transferred. Reuse does not establish product fidelity, actual mounting,
neck/clear-bore truth, physical joints, coordination or engineering acceptance.

See evidence/automatic-candidate-bim-plan.json for executed five-terminal studies
and retained original requirement/coordination states. These are synthetic model
studies, not BSE3227 modifications or complete installation designs.

Shared systems retain one consistent declaration per original system identity;
per-terminal template origins live separately in the provenance bindings. An
actual initial trial added different terminal-origin text to one shared system
and failed inlet authoring. That failed run is retained; the corrected source
statement uses the shared system identity and both complete reruns pass inlet
and stub authoring without waiving coordination.

Validation:7related tests pass, including omitted-policy compatibility,
classification/source preservation, same-room references, unrelated branch
preservation and shared-system consistency. Actual native/MOOSAS reruns retain
all13requirements, five stub bodies and10friction cases. Both retain five
clearance failures, zero hard intersections and pending final review. No full
agent/design completion is claimed.
