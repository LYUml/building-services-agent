# Source-bound delivery review

Audits now include `review_agenda`: source-bound effective passes are listed by
requirement ID, while every remaining requirement is grouped once by its original
task. Groups retain full quote, acceptance target, source locator, review evidence,
execution status, input blockers, dependency blockers and the existing diagnosis
next action. The HTML displays the remaining task/requirement list. This closes
the gap between separately recorded scoped reviews and the agent's next work list.

The agenda is unavailable (`null`) after a global review/source integrity error,
instead of presenting a partial list as complete. Failed recorded reviews and
failed fact checks remain work items. A recorded pass for an unexecuted automated
task remains pending. A scoped manual pass does not change workflow task status,
unblock its dependent tasks, authorize execution or establish design acceptance.
An empty agenda only means the defined review records passed their scoped checks.

Twenty-seven delivery/status tests pass, including grouping multiple obligations
on one task, stale review rejection and manual-review dependency preservation.
An actual private project audit retains four scoped arithmetic passes and all
29 remaining requirements; work-load/work-minimum leave this review queue while
their original execution statuses and downstream blockers remain unchanged.
See evidence/remaining-review-agenda.json. Existing previous audits are preserved.

The HTML audit now shows effective pass/fail/pending counts and one readable
section per original requirement. Execution,recorded review and effective review
stay separately visible. Expand the source/evidence section for exact quotes,
locators,reviewer assertions,blockers,artifact hashes,attachments and Boolean
facts. Long text wraps without a wide source-quote table;untrusted observations
and source strings remain HTML-escaped. The audit JSON and acceptance semantics
are unchanged. See COURSEWORK_SCOPE.md for source-backed preliminary reviews
that preserve other obligations from the same paragraph.

Audit JSON and HTML retain each requirement's passage ID, validated source locator, exact quote and acceptance target. For multi-document plans, locators include the source document and its hash alongside PDF page/line or Word XML information. Identical quotes from two files remain separate requirements. Locators are reconstructed from current source extraction before use; changing a recorded locator invalidates the audit. The HTML column reports the effective review result after dependency/failure gates, which may differ from a reviewer's asserted status.

Audits also run source-bound dependency diagnosis. A recorded passing task with nonpassing required parents is rejected. Each reviewed requirement exposes `blocked_by`; a blocked manual task stays effectively pending even if its reviewer records pass. An upstream manual review does not rewrite workflow execution or authorize downstream tasks. Independent manual tasks can still receive evidence-backed reviews without being mislabelled executed engine tasks.

`bsa.delivery` records requirement-by-requirement review evidence separately from an immutable workflow run. Successful tool execution alone does not fill the review or establish engineering acceptance. The host agent can record actual numerical/visual observations; no user permission or external publishing action is implied by a review record.

```powershell
# This example intentionally leaves manual visual and missing-fault gates pending (CLI exit 2):
python -m bsa.workflow execute examples/delivery-plan.json --out runs/delivery
python -m bsa.delivery template examples/delivery-plan.json runs/delivery --out runs/delivery-review.json
# Inspect source requirements and actual artifacts, then edit the separate review record:
python -m bsa.delivery audit examples/delivery-plan.json runs/delivery --review runs/delivery-review.json --out runs/delivery-audit
```

Template creation requires a currently valid source-linked plan and unchanged run inputs/artifacts. Every source requirement appears exactly once with `pending` status. The template pins the exact plan and workflow-report bytes and a canonical hash of every full source requirement (including task, quote and acceptance text). Review/audit outputs must be outside the run and cannot contain or overwrite their inputs. Original workflow files and their recorded task statuses remain unchanged.

The audit revalidates the plan against the brief, requires the exact input/hash and task sets, checks each run requirement against its source text/task, and reconciles its artifact inventory. It verifies source/task-artifact bytes again after review. A changed requirement, missing/duplicate review row, edited source/report matrix, stale review, changed/missing artifact or escaped evidence path fails the audit. A pending or failed source task cannot become accepted simply because a reviewer typed `pass`: failed tasks stay failed, and pending automated tasks stay pending. A `manual` task may have a recorded review pass once actual cited evidence has been examined; its original execution status stays pending in workflow.json.

## Review entries

Each entry contains the requirement ID/fingerprint, `pass`, `fail` or `pending`, reviewer text, UTC review timestamp, observations, cited evidence, optional supplemental attachments and optional Boolean fact checks. Nonpending records require a nonempty reviewer, valid UTC timestamp, observations and at least one original recorded artifact. Reviewer names/timestamps are assertions, not authenticated identities or proof that someone inspected a file. The tool does not certify credentials, authorize external actions or automatically establish semantic completeness.

`evidence` entries use `artifact` (relative run path) and `sha256`, matching both workflow-recorded and current file bytes. A supplemental attachment, such as an actual rendered PNG created after execution, uses `path`, `sha256`, `source_artifact` and `source_sha256`. Its source must also be cited original evidence. Attachments remain within the run, are checked before/after review, and do not alter the original workflow manifest. The hashes establish file/source association, not that pixels were rendered correctly; inspect the actual image and describe the limited scope.

Optional Boolean facts read an explicit nonempty JSON pointer from a cited original artifact. Objects, zero-based arrays and `~0`/`~1` escaping are supported. A fact requires `artifact`, `pointer`, Boolean `expected` and explanatory `basis`, for example:

```json
{
  "artifact": "electrical/calculations.json",
  "pointer": "/calculated_checks_pass",
  "expected": true,
  "basis": "Source asks for the adapter's conditional current/ampacity/drop checks"
}
```

A false fact overrides a recorded pass. This reads an adapter-reported assertion; it is not an independent formula, quantity, regulation or visual check. Record separate numerical derivations or observed image/model evidence where the requirement needs them. Missing data remains pending rather than receiving an invented threshold or a fabricated check.

## Result and limits

The output is `audit.json` and a readable `report.html`. Each row preserves the source quote/acceptance, execution status, recorded and effective review statuses, evidence, facts, observations and issues. Overall status is `failed`, `needs_review` or `review_complete`. CLI exit 0 means all defined review-record checks passed; exit 2 means failed or unresolved review. `review_checks_pass` is specifically source/byte, review-record and defined Boolean-fact consistency. It does not prove the review covered every engineering implication. `design_accepted` always stays false in this tool; complete design acceptance requires the actual domain and visual evidence, not a blanket software flag.

The runnable synthetic example has three requirements: conditional three-light electrical outputs, actual SVG preview review and fault/protection evidence. The retained demonstration checks source formulas and inspects a real rendered image, recording two scoped passes. Fault disconnection/breaking-capacity data is absent, so that requirement remains pending and overall review stays incomplete. No native DWG, PDF scale or full electrical design acceptance is claimed by the SVG review. See docs/evidence/delivery for actual records. The test suite also exercises a complete **synthetic record** without changing `design_accepted`; that is a consistency fixture, not a certified engineering design.


## Retained engineering requests

The audit JSON and HTML now retain workflow_status.engineering_actions and
per-requirement engineering_review_requests. The HTML displays the task, source
requirement IDs, requested next evidence and original module artifact/hash.
Source strings are escaped as text. Existing reviewer assertions, effective
scoped review states and execution results stay distinct from engineering
acceptance, which is not_established; design_accepted remains false.

A zero request count does not establish complete engineering coverage. Disabled
or unexecuted components create no successful-payload requests. Original failed
coordination tasks and pending reviews remain. No reviewer entries are generated
as pass, no model is modified and no engine is selected by the HTML page.
Existing commands and separate output-directory guards are unchanged.

See evidence/friction-review-delivery.json for actual synthetic native and
module-disabled audit evidence. This is an internal diagnostic report, not a
coursework engineering deliverable or proof of complete design acceptance.

Validation: 23 related tests pass, including source-field escaping and scoped
review/engineering-state separation. Actual three-scenario audits retain all
13 requirements. The native study retains eight requests and a failed
coordination requirement; disabled cases retain zero component requests.
The visible request overview was inspected at 600px; full detail/engineering
acceptance remains pending.
