# Knowledge input ownership and change impact

Knowledge index/query tasks now record their actual source dependency set when
the workflow executes. The implementation reuses `knowledge.workflow.inputs`,
the same validator already used for source/context/method pins and saved-query
verification. There is no second parser, hand-maintained source list or new
MCP operation.

New knowledge workflows add `knowledge_input_ownership` to workflow.json:
schema `bsa.knowledge-input-ownership/1`, a task-to-path-list map, and the existing
SQLite/Python runtime fingerprint. Every path must be an exact original
workflow input; its hash remains in the original inputs map. Saved verification
reconstructs every task set and compares the runtime. Dropped, substituted or
invented ownership cannot be blessed by rewriting outer artifact hashes.

The existing checkpoint archives and hash-binds the entire original workflow.
Change analysis reads the old verified ownership without asking changed source
files to replay. It never silently edits an old checkpoint or invents ownership
for older workflows. Checkpoint1/2 remain supported; absent ownership retains
the earlier conservative whole-workflow dependency rule. No new checkpoint
format or duplicate source archives are needed.

## Scope and retained gates

* Document ownership includes the manifest, exact selected source files, context
  and implementation methods. Page selection and declared publication metadata
  remain part of the manifest, rather than becoming untracked search options.
* Immutable Git references remain pinned through the manifest's commit/blob
  identity and the reference reader; they are not promoted to normative sources.
* Saved-index queries also own the original receipt, request and SQLite file.
* Project-input sources include their verified common bundle, original numerical
  producer, original inputs/methods and retained producer artifacts. Ownership is
  not limited to the small inputs.json file.
* Knowledge-package method changes affect their consumers. Shared framework and
  contract paths retain their previous global gates. Project context, brief,
  requirements, recipe, detector and original artifact checks remain active.
* Knowledge runtime drift invalidates knowledge tasks and their consumers.
  Unrelated numerical modules retain their original dependency/runtime checks.

The impact response labels each task with `input_ownership`:
`verified_knowledge_closure`, `verified_module_inputs`, or
`conservative_workflow_inputs`. An unchanged knowledge artifact is not an
executable result cache. The numerical reuse whitelist remains air allocation
and single-phase circuits only. A malformed current plan still conservatively
invalidates execution/reuse, even if some branches appear unrelated.

Generic common-report consumers and manual review still use conservative input
ownership. This milestone improves knowledge dependency precision; it does not
claim precise dependencies for every existing workflow task or automatic review.

## Executed real case

The real study composes selected course, EMSD code snapshot, manufacturer
snapshot and recorded lighting-input sources, plus an independent actual
lighting calculation/common report. The snapshots retain their source roles,
declared editions, selected pages and unresolved applicability. This tests
versioned retrieval and dependence, not current statutory applicability.

Only the course manifest's physical page selection changes from4/5 to4:

| Task group | Impact |
| --- | --- |
| Course index and ADPI lookup | Invalidated; new hits cite page4 only |
| Code index and lookup | Unchanged |
| Manufacturer index and lookup | Unchanged |
| Nested lighting-input index and lookup | Unchanged |
| Independent actual lighting calculation | Unchanged; original execution still required |
| Generic common report and manual review | Conservatively invalidated |

The saved source closure covers8knowledge tasks, with17input paths per document
task and52per nested-input task on this host. Its compact JSON encoding is21,298
bytes, excluding the existing global hash map; this is serialized size, not RSS.
All original selected sources stay unchanged. Actual calculation JSON and common
HTML stay byte-identical across executions; all11study requirements remain
pending review. Nine actual SDK calls use the unchanged42tool catalogue.

Private proof/review files are under `runs/knowledge-ownership-real` and the
selected study workspace. Public aggregate evidence is
`docs/evidence/knowledge-ownership.json`; it contains no source documents or
personal records. The real case covers document/project-input kinds; separate
synthetic controls exercise immutable Git references and saved-index ownership.

Ten new controls cover local source changes, numerical-source independence,
knowledge runtime, recipe/global requirement gates, shared/domain methods,
coherently rehashed substitutions, nested producer evidence, fixed Git sources,
saved indices and legacy fallback. The197-case selected architecture regression
passes with zero skips and independently verified durable receipt. Existing
module/MCP compatibility group also passes48cases with zero skips and verified
receipt; total245selected cases, not whole-repository discovery. No new photometry,
native geometry, engineering acceptance, release or user acceptance is asserted.
