# Source interpretation handoff

The host agent reads and interprets the actual brief;this CLI handles the source
coverage handoff to the existing workflow engine. It reuses document extraction,
plan validation and reviewed work decomposition. It does not use a keyword
classifier or a second engineering engine.

```powershell
.venv/Scripts/python -m bsa.work_plan_review template runs/project/plan.json --out runs/project/work-review.json
.venv/Scripts/python -m bsa.work_plan_review apply runs/project/plan.json runs/project/work-review.json --out runs/project/interpreted-plan.json
.venv/Scripts/python -m bsa.cli workflow runs/project/interpreted-plan.json --out runs/project/workflow
```

Start with a source-linked scaffold from workflow_draft. Inspect original pages,
resolve extraction-review issues and justify context classifications before this
handoff. A blocking extraction issue still rejects;the template cannot acknowledge
source review on the agent's behalf. Supplementary documents retain their IDs.

The template contains source_sha256,passages,tasks and source_passages. The latter
retains full extracted quotes and locators for agent reading;the authoritative
source is re-extracted when applying the review. Each passages entry pins its
text_sha256 and starts with an empty tasks list. The agent must map every technical
passage to one or more task IDs and author every task with exactly these fields:

| Field | Meaning |
|---|---|
| id | Unique work-package identifier |
| description | Actual work required by the complete source passages |
| blocker | Concrete unresolved input,design decision or integration gap |
| acceptance | Specific evidence needed to verify the complete obligation |
| requires_pass | IDs of earlier work packages that must pass first |

No tasks are inferred automatically. Include all obligations in compound source
paragraphs;retain units,targets,assumptions and source applicability explicitly.
The reviewed transform accepts only the original generic interpretation scaffold.
It cannot overwrite unrelated engineering gaps. Full source quotes survive even
when several passages share a work package. Source/text hashes verify identity
and coverage,not semantic completeness.

The CLI requires new output files beside the plan within the repository. Apply
validates the candidate before exclusively creating the new plan and leaves the
original untouched. Referenced planning records enter workflow integrity checks.
The old Python apply(plan,review) replacement API remains for existing benchmark
callers;new workflows should pass output or use the CLI.

Template and apply return JSON with exit2 because interpretation or engineering
execution remains pending. An error returns diagnostic text without success JSON.
The transformed tasks remain manual with explicit gaps until the agent creates
actual source-backed producer/consumer tasks. Running a manual plan is useful for
dependency diagnosis,but does not produce a completed design.

Fourteen tests pass across CLI/handoff,existing work-review and draft coverage.
The actual pinned five-document MIT bundle produced34 technical passages and14
reviewed pending packages with every original quote retained and workflow
integrity passing. Existing source-review notes and decomposition were reused;
this is not a fresh semantic interpretation or a completed independent assignment.
Attribution remains in benchmarks/mit-4401-2018/NOTICE.md. See
[executed evidence](evidence/document-intake/work-plan-cli.json).
