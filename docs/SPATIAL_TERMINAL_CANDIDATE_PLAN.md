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
