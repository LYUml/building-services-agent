# Source-linked common requirements inventory


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


`bsa.source-requirements` implements `requirements.source-inventory`,returning
`bsa.requirements-inventory/1`. It reuses existing validate_plan,plan_documents,
source extraction and the pinned jsonschema4.26.0 module boundary. No new parser,
semantic model,engineering engine or external dependency is introduced. Its own
licence is NOASSERTION;upstream licences remain unchanged.

```powershell
.venv/Scripts/python -m bsa.modules examples/modular/requirements-request.json --provider bsa.source-requirements --out runs/requirements-example
```

The request contains exactly one hashed source-linked plan. Payload preserves
all indexed source passages and locators,requirement/context dispositions,
declared requirements/acceptance,task descriptions and unresolved inputs. Each
source document has its own original hash. Secondary documents are explicitly
labelled supplement_or_reference rather than guessing their document-wide role;
per-passage dispositions remain exact. The coordinate-frame envelope is carried
without a geometry claim or inferred coordinates.

Verification rereads the plan,all source/dependency hashes and exact extraction,
then compares the complete payload. Schema-valid edits to acceptance,reference
text or missing-input lists reject during replay. Contract checks also reject
lost coverage,duplicate IDs or unresolved source/task references. Host disable
returns unavailable with no payload. Invalid source validation fails without a
successful inventory. Existing extraction-review gates remain authoritative.

project_start automatically creates requirements-request.json and
requirements/result.json when source validation permits its interpretation
handoff. Unreviewed graphical/extraction issues block this module;original
sources and initial scaffolds remain preserved. The intake manifest inventories
the new artifacts. A validated inventory is still not semantic interpretation:
interpretation_status is not_assessed,engineering_execution is not_executed,
geometry_bound and design_accepted are false. Empty unresolved-input lists in a
legacy plan do not prove complete input discovery or engineering readiness.

Actual electrical,water and real BSE3227 plans verify through this boundary.
BSE3227 retains90passages,33requirements and9unresolved inputs;no private source
content is published. A fresh public-source project_start also produces and
verifies its common result. See evidence/requirements-module.json.

This is the requirements inventory boundary,not an autonomous brief-to-design
solver. Semantic design-input binding and completeness checks remain unfinished;
exact existing-plan workflow consumption is now supported above. Existing engineering
plans and domain validation remain the execution authority.
