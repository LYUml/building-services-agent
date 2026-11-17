# Common engineering data: first executed slice

## Current project-context/workflow milestone

The new data view now runs through existing workflow and MCP routes. An explicit
persisted UUID4 project context replaces ambiguous project naming for this new
path. Existing legacy plans still execute; the old `workflow-allocation`
placeholder cannot be exported as a common project identity. A new explicit
module request is required instead of relabelling historical results.

```powershell
bsa engineering-data context --name "My project" --scenario baseline --out runs/MY_PROJECT/context.json
```

Create a context once for a new project, not once per execution. Keep its
project_id when preparing a fresh scenario file/request for the same project;
use a new UUID for another building/project. Do not edit old context files to
make historical receipts pass. Context is a declared project identity, not proof
that physical assets have been surveyed or manufacturer identities authenticated.

A source-bound plan may declare `project_context: "context.json"` and append:

```json
{"id":"common","kind":"engineering_data","depends_on":"analysis"}
```

Its earlier analysis must be a supported module_analysis task using the
classified-air-allocation or single-phase-circuits provider. Request project_id
and scenario_id must exactly match context before any task executes. The new
classified-air module-analysis route reuses the same validated allocation
provider; a completed allocation does not establish room-load or ADPI acceptance.
Older direct allocation workflows are not silently rewritten.

Execution and saved-result inspection both reconstruct the data and bind the
exact declared producer request, producer result location, context/method pins
and original requirements. A valid export from another task cannot substitute
for the declared one, even after coherent outer hash rewrites. Disabled/failed
producers block export while independent branches can continue. Manual review
and original pending numerical/engineering facts remain separate.

The existing40tool server requires no new operation/tool: execute_workflow,
diagnose_workflow, artifact_index, read_artifact and delivery_template execute
the new chain through the real SDK. Five actual calls on the historical HVAC
data preserve81entities/244quantities and all original source files. This is a
new integration plan around existing data, not a replacement coursework plan.

Current local evidence:64durably recorded regression cases pass, zero skips,
unchanged source and independently verified receipt;27minimal-profile cases
pass without Fluids/IFC/Manifold;11new context/workflow controls cover project
isolation, request/result substitution, omitted pins and failures. See
[workflow/context evidence](evidence/engineering-data-workflow-context.json).
Remote results for this later source revision remain to be observed; older
7841fae Windows/Ubuntu results below apply to the earlier first slice only.

General editable source-parameter ownership, broader entity/model mappings,
knowledge, change impact and different-real-project acceptance remain open.

## Earlier first-slice scope and evidence

This is the first additive slice of the2026-11-18 modular/data goal. Existing
module request/result contracts and domain engines remain authoritative. It is
not yet a complete editable cross-discipline project model.

## Boundaries and reuse

`engineering_data.model` owns common identity/relationship validation;
`quantities` owns an explicit bounded exchange-unit table; `module_bridge`
independently verifies existing module producers and maps their data; `report`
is a consumer of the same model. CLI is thin and lazily imports the bridge.
No solver is copied, no new dependency is introduced. Validation reuses pinned
jsonschema4.26.0, source reading/workspace guards and existing provider replays.
The unit table is not a general unit-expression parser or physical method.

The initial mappings cover classified air allocation and conditional single-phase
circuits. They preserve original provider acceptance, pending/numerical checks,
geometry limitations and a hash-bound workspace-relative producer reference.
Original provider artifacts remain available; selected common fields are not
advertised as a lossless replacement for every domain field.

IDs derive from explicit project ID, entity kind and original source ID, not
row order, scenario name or output location. They remain stable across quantity
changes when original identity stays stable. IDs currently assume source IDs
are unique within one project/entity kind; there is no automatic cross-model
merge or fuzzy entity matching. Conflicts need explicit source interpretation.
An exported supply relationship is not native installation/port acceptance.

Every quantity retains original value/unit, semantic dimension, explicit SI
value/unit, classification and JSON pointer into the original producer.
Thermal W, electrical real W and apparent VA remain distinct. Ambiguous kW,
nonfinite values, inconsistent conversions, duplicate IDs and dangling links
reject. Classification `declared` preserves an upstream declaration, not a
verified measured fact. This slice exports derived values; it does not authorize
editing calculated values as if they were source design inputs.

## Run and inspect

Install the existing `modules,spatial` extras for these two mappings, using a
dedicated environment. Air geometry needs Shapely; no Fluids/IFC/Manifold is
needed by this common-data profile. Other provider verification keeps its own
runtime requirements. The existing full-HVAC example fixture additionally
needs network for terminal lookup and duct sizing; do not confuse that fixture
with the smaller allocation data boundary.

```powershell
bsa engineering-data export PROJECT_MODULE_RESULT --out FRESH_COMMON_DIRECTORY
bsa engineering-data verify FRESH_COMMON_DIRECTORY
```

The standalone `python -m bsa.engineering_data` uses the same functions.
Input must be a supported, completed, independently verified module result.
Unavailable providers cannot become empty successful models. Completed numerical
failures stay fail in source flags. Output is restricted to tool runs or the
explicit host project, with three files: model.json, summary.html, receipt.json.

Verification checks exact file/method hashes and reconstructs the common model
from independently replayed producer evidence. It then reconstructs the report.
Rewriting all exported hashes cannot clear changed quantities, missing pending
items or a forged report. Original input/result bytes are not modified.

## Executed evidence

- 10 new controls pass, including the installed CLI, unit semantics, stable IDs,
  failure retention, workspace guards and coherent-hash forgery rejection.
- 31 current data/provider/CLI compatibility tests pass in the development profile.
- A new modules/spatial environment passes pip check and16data/electrical controls
  without Fluids, IfcOpenShell or Manifold. Its initial nine errors exposed a
  full-HVAC test-fixture dependency; the minimal new fixture is now independent,
  and original full-HVAC compatibility cases remain in the broader CI profile.
- The existing isolated actual HVAC layout maps80terminal rows to81entities and
 244quantities. Every terminal row and the load equal the prior native project
  result; three original source files remain unchanged. No course adoption.
- The actual common HTML first viewport was rendered in an isolated headless
  browser and viewed. Entire244row visual review is not claimed.
- Three fresh Windows imports of the common core show median0.0246s and
 28,463,104byte peak working set using the existing profiler harness. Import-only
  scope; no whole-host memory or improvement over a different workload claimed.

See evidence/engineering-data-first-slice.json and engineering-data-import.json.
The new Windows/Ubuntu CI profile passes at7841fae. Actual logs show16minimal
controls followed by8retained full-HVAC compatibility cases per platform.
See evidence/engineering-data-ci.json. Whole-suite and later goal phases remain
separate.

## Next steps, in the authorized order

1. Continue explicit source design-input bindings/identity ownership after the
   executed workflow/MCP boundary above. General spatial/system/port contracts remain to
   be integrated; no universal data editing or provider replacement is claimed.
2. Build source/version/page/applicability-aware knowledge retrieval, reusing
   existing source readers, reference library and rule packs.
3. Add change impact, invalidation and safe reuse using existing workflow gates
   and input/method hashes. No cache/resume claim from this export alone.
4. Validate with a different real project type and real output propagation;
   synthetic electrical controls are not that second real-project acceptance.

The previous release candidate remains a historical checkpoint. This new goal
is active, not complete. No formal release or user acceptance is asserted.
