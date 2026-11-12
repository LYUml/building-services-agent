# Retained straight-friction engineering review queue

The existing workflow_status diagnosis now projects source-backed requests from
an already verified bsa.straight-friction-components/1 payload. It reuses the
common module verifier and retained report; no pressure solver, engineering
threshold, code interpretation or new dependency is introduced.

The new top-level engineering_actions list is separate from execution-failure
actions. A numerically passing component task can still need engineering review.
Each entry preserves the task requirement IDs, exact module evidence/hash and
requests. Existing execution statuses and dependency roots are unchanged.

Requests retain per-terminal native GUIDs, length, bore and L/D for unverified
flow-development applicability; pending cases additionally retain flow regime,
Reynolds and condition. No L/D acceptance cutoff is invented. Air-property review
retains original density/viscosity/roughness source classifications. Whole-system
pressure review requires physical network/joint/loss evidence before fan duty.
These are review requests, not a diagnosis of a defective installation, an
automatic geometry repair or approval to use a different numerical method.

Unavailable, failed and unexecuted modules have no successful friction payload
and therefore create no component-derived requests. Native-model and source
replay must still pass before the diagnosis is published. Editing evidence or
source files does not become an accepted review by rerunning this projection.

Run the existing command:
`python -m bsa.workflow_status PLAN RUN`.
Engineering gaps remain even when execution_pass is true; design_accepted stays
false. Existing clearance failures and original source requirements are retained.
See evidence/friction-review-queue.json for executed synthetic diagnosis evidence.

Validation: 11 related tests pass. The actual native diagnosis retains eight
requests and the existing coordination failure. Both disabled scenarios retain
zero component-derived engineering requests. These are synthetic controls.
