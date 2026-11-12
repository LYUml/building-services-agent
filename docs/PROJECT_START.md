# Start from original requirement documents

User-selected coursework workspaces now separate project inputs/runs/deliverables
from reusable tool source. Supported entry points use explicit host BSA_PROJECT_ROOT;
actual BSE3227 execution now occurs in its own project directory. Other adapters
are not all migrated. See PROJECT_WORKSPACE.md.


A workflow can now require the exact common inventory using host option
`--requirements-result`. This checks the original plan path/hash,complete
requirement/task identities and unresolved inputs before executing any task:

```powershell
.venv/Scripts/python -m bsa.workflow execute runs/project/plan.json --requirements-result runs/project/requirements/result.json --out runs/project/workflow
```

The same option is available on `bsa.cli workflow`. The run records the inventory
reference and pins its module inputs/artifacts;verification and delivery replay
its source and compare the resulting requirement matrix. A same-byte different
plan cannot borrow it. A disabled/unexecuted inventory rejects before output.
Rewritten acceptance,removed blockers or a stripped pinned binding reject.
Existing tasks keep their original source inputs,gates and acceptance states.
After changing a plan or completing interpretation,export a fresh inventory for
that exact plan;do not rewrite old module results. This binding does not infer
engineering values or perform semantic requirement-to-design selection.

Actual public electrical and native-water workflows execute with bound
requirements and pass integrity/delivery correspondence. A fresh BSE3227 run
preserves33requirements and9unresolved inputs,four existing calculation/drafting
stages pass,and native/other unresolved stages remain pending without an explicit
AutoCAD host. No native drawing or full design acceptance is established in this
trial. See evidence/requirements-workflow-binding.json.


Common source-linked requirements inventory now executes through the trusted
module runner and automatically after validated project_start intake. Exact
passages,requirements,locators and unresolved inputs survive source replay on
electrical,water and real BSE3227 plans. Semantic completeness and design-input
binding remain unfinished. See REQUIREMENTS_MODULE.md.

The real interpreted bundle now also executes5existing engineering adapters
after explicit host binding of18unchanged source files. This regenerates actual
calculation/sizing/native drawing outputs while retaining the user-selected HK
check and10manual work packages. Native reopen/scale and source/delivery checks
pass;11tasks remain pending. This uses earlier source-backed design choices,
not automatic inference from an arbitrary brief. See
evidence/project-start-engineering-binding.json.

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

Use repeated `--reference C:/path/to/guide.pdf` for host-selected reference
material. These files are still copied,hashed,indexed and extraction-reviewed.
The original all-passage plan.json remains unchanged;role-plan.json records
reference passages as context with a pinned source-roles.json decision. Primary
and --supplement documents keep their interpretation obligations. intake.json
identifies the effective plan. This is an explicit host role choice,not automatic
semantic classification. Do not label a mandatory rubric as reference.
Graphical/reference extraction issues still withhold work-review.json until
source inspection is recorded. Changing reference bytes invalidates the plan.

Fourteen intake/draft/handoff tests pass,including supplementary/reference role
separation,source mutation and graphical-reference review preservation. The real
two-PDF reference-aware run keeps14primary requirements and76reference-context
passages,with all90passages preserved in the original draft. Source review stays
pending;prior review notes are not automatically transferred.

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
