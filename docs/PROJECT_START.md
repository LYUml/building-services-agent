# Start from original requirement documents

The actual reviewed bundle now also exercises source-role interpretation and
work decomposition:all14primary passages retain original quotes across26rows
and10work packages;76lecture passages remain indexed reference context. This
preserves the brief's required scope without turning every general reference
example into a coursework deliverable. Original drafts remain unchanged. Source
validation and dependency diagnosis pass,while all10engineering packages remain
pending. This is host-agent interpretation,not an implemented autonomous semantic
engine or a completed engineering execution. Evidence:
evidence/project-start-interpretation.json.

```powershell
.venv/Scripts/python -m bsa.project_start C:/path/to/brief.pdf --supplement C:/path/to/rubric.docx --out runs/new-project
```

This composes existing workflow_draft and work_plan_review tools. It copies
original briefs into numbered source folders,pins original/staged bytes and
retains full extracted passages. Originals can be outside this repository;
all new files must be in a new runs directory. Repeated --supplement arguments
preserve distinct document IDs. No source is executed or uploaded. Unsupported
formats,duplicate originals and existing output directories reject.

`intake.json` records source locations/hashes,generated artifact hashes,direct
orchestration method hashes,errors and the next state. The three recorded method
files are not a transitive dependency/runtime lock. Private documents/paths and
generated intake records remain ignored local files.

Successful text extraction creates plan.json with all-passage coverage and
explicit interpretation blockers. When there are no extraction-review issues,
work-review.json is also generated for host-agent interpretation. If PDF layout,
annotations,Word drawings or other extraction issues require inspection,the
source copies and draft remain but the interpretation template is withheld.
Inspect the originals and record specific document_review notes in the plan,
then use work_plan_review template/apply per WORK_PLAN_HANDOFF.md. Blank or
failed extraction preserves source files and diagnostics without a false plan.

CLI exit2 is expected:needs_source_review or needs_interpretation remains.
This starts a project;it does not interpret a raw brief into an engineering
design,select supported adapters automatically,resolve missing inputs or produce
accepted models/drawings. Original requirement coverage and source review remain
necessary before the agent creates executable engineering tasks.

Twelve intake/draft/handoff tests pass. A real private two-PDF bundle was staged
unchanged with90passages;source-review issues correctly prevent a ready handoff.

That real bundle was subsequently reviewed against actual reference-page renders
and hash-verified prior primary-page inspection. A new source-reviewed plan now
validates and generates the interpretation template,retaining all90passages and
their interpretation blockers. Embedded performance/friction/fitting graphics
are explicitly identified as untranscribed source evidence. Source review does
not imply those numbers or their engineering applicability are accepted. See
evidence/project-start-source-review.json.
