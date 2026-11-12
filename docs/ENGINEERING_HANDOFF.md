# Source interpretation to engineering execution

The host AI reads the actual brief and supplies an explicit review. This adapter
binds that interpretation to existing workflow engines without a keyword router,
another LLM service, or a new engineering solver. It fills the gap between the
manual source scaffold and concrete executable tasks. It does not independently
prove the semantic completeness or engineering correctness of the host review.

Start with `bsa.project_start` or `bsa.workflow_draft`, inspect all source pages
and extraction issues, then author a sibling review JSON with exactly:

| Field | Required content |
|---|---|
| schema | `bsa.engineering-handoff/1` |
| source_plan_sha256 | Exact original plan hash |
| tasks | Concrete tasks using existing validated workflow adapter kinds |
| requirement_bindings | Every original requirement ID mapped to `tasks` (nonempty task-ID list) and `acceptance` (explicit evidence criterion) |
| interpretation_notes | Every generic interpretation-gap ID mapped to an explicit host explanation |
| extra_unresolved_inputs | Additional ordinary source-linked missing/conflicting input records; use an empty list only when justified |

Only an all-manual original interpretation plan is accepted. Original engineering
tasks cannot be replaced. All source passages, quotes, dispositions and original
acceptance text survive; bound requirements retain `original_requirement_id` and
`original_acceptance`. One obligation can bind to several adapters without losing
its full quote. Every adapter needs an original requirement. Old dependency gates
are inherited, including when obligations split; collapsing dependent obligations
into one task rejects. The existing workflow validator checks adapter contracts,
source paths, units, prerequisites and declared input citations.

Generic "not interpreted" gaps may be replaced by explicit interpretation notes.
Every other original gap retains its ID, description, kind and source citations,
with affected task IDs remapped. Additional actual gaps remain blocking. A review
note cannot clear a missing survey, product rating or engineering fact. Keeping
all actual facts/gaps is the host's responsibility; the adapter does not discover
undeclared omissions or verify that the selected input JSON means what the source
requires. Preserve thermal/electrical power, assumptions and regulatory editions.

```
python -m bsa.engineering_handoff ORIGINAL_PLAN HOST_REVIEW --target NEW_SIBLING_PLAN --out NEW_RUN
```

This creates a validated new plan, pins its concrete engineering inputs, rebuilds
the common requirements inventory, executes the original-source-linked graph and
diagnoses the result. Runtime options belong to the trusted Python API's
`execute_options`; documents cannot select shell commands. Disabled requirements
providers stop all engineering execution. Changes to bound parameters are retained
as source changes rather than silently accepted. Original plans and source files
are preserved. CLI exit 2 retains pending engineering acceptance; inspect the JSON.

`bsa.engineering_handoff.verify(NEW_RUN)` independently reconstructs the bound
plan from the original source/review, verifies input/method/artifact snapshots,
exact requirement and gap counts, fresh inventory binding, workflow integrity,
diagnosis and status. Passing means evidence correspondence, not design approval.

Reuse: project_start/workflow_draft document intake, existing workflow validation,
requirements source-inventory module, executor and workflow_status diagnosis.
The public trial uses existing electrical/ezdxf, fluids catalogue sizing and
network analysis, and IfcOpenShell native IFC authoring. No new dependency,
engine or third-party code is added; existing licenses/attribution are retained.

Run the authored public interpretation with:

```
python scripts/run_engineering_handoff_demo.py --out runs/NEW_PROJECT
python scripts/run_engineering_handoff_demo.py --out runs/NEW_CONTROL --missing-water
```

This script contains an explicit host interpretation of its five source
paragraphs and rejects changed source text. It is a repeatable integration case,
not an interpreter for arbitrary documents. Source JSONs remain explicitly
synthetic. The positive case executes electrical checks/overlay, air catalogue
sizing, water pressure analysis and standalone IFC envelope authoring. The control
keeps water and final review pending while independent tasks execute. The envelope
model is not reconciled with the separate calculations. There is no new native
DWG/plot acceptance, complete installation or Hong Kong compliance claim.

[Executed evidence](evidence/engineering-handoff.json) retains both real runs,
source transfers, saved model/artifact checks and four rejected receipt/input
controls. Thirty-eight related tests pass, including actual adapter execution,
ordinary-gap/dependency preservation, missing mappings, disabled inventory and
source/artifact drift. The upstream IfcOpenShell ResourceWarning remains noted.
