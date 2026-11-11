# Source-linked common requirements inventory

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
solver. Common design-input binding,semantic completeness checks and direct
common-requirements workflow consumers remain unfinished. Existing engineering
plans and domain validation remain the execution authority.
