# Source-bound delivery review

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
