# Change impact and verified numerical reuse

[Knowledge input ownership](KNOWLEDGE_OWNERSHIP.md) now records exact task
source sets in verified workflows/checkpoints and localizes supported knowledge
changes. Legacy/unknown tasks keep conservative fallback; cache eligibility
and manual engineering review are unchanged.

The new real recorded-lighting source-power adapter also executes this path;
see [lighting audit](LIGHTING_SOURCE_AUDIT.md) for188entities,4owned inputs,
actual typed10W change/report propagation and bounded project-knowledge proof.
Lighting has no result-cache eligibility or new photometric/geometry acceptance.
Earlier counts and domains below describe their historical checkpoints.

The CLI and MCP adapters reuse existing workflow receipts, module contracts/provider verification,
common-data/report adapters and `doctor` dependency inspection. There is no new
solver, dependency or cache service. Existing HVAC refresh and native drawing
revision controllers remain authoritative for their supported operations.

```powershell
bsa changes checkpoint runs/baseline-workflow --out runs/fresh-checkpoint
bsa changes analyze runs/fresh-checkpoint
bsa changes analyze runs/fresh-checkpoint --plan PATH_TO_CURRENT_PLAN
bsa changes reuse runs/fresh-checkpoint --task analysis --out runs/fresh-reuse
bsa changes verify-reuse runs/fresh-reuse
```

A checkpoint requires a currently verified original workflow. It saves the exact
plan/workflow and independent numerical-result snapshots, bound back to the
unchanged original workflow record and artifact hashes. The current plan may
change, but its directory must remain the same explicit project. Original
sources, workflow artifacts and review records are never rewritten. Declared
project/scenario context must be pinned, and numerical modules must match it.

Analysis compares recorded source/method/runtime pins, task recipes, plan/brief/
requirements metadata, artifacts and explicit dependency links. It reports new
declared inputs and malformed current plans. Unknown task ownership falls back
to whole-workflow pins; recipe changes conservatively invalidate unknown adapters.
Unsupported adapters remain available through their original execution paths.
An unchanged artifact is not automatically an executable cache entry.

Only independently verified, completed, passing `bsa.classified-air-allocation`
and `bsa.single-phase-circuits` modules currently have an executed reuse path.
Inherited modules, host provider overrides and other capabilities require their
original execution. A changed upstream task invalidates declared consumers.
Changed context/requirements or an invalid current plan prevents reuse. Pending
manual review never becomes design acceptance.

The checkpoint also records the existing doctor's selected direct dependency
versions, Python binary and requirements-file hash. Air allocation includes the
spatial profile; electrical uses the numerical contract profile. Drift in this
profile or the change detector blocks reuse. This does not authenticate every
in-place edit to transitive installed packages. Existing provider verification
and recorded runtime/method pins remain required; no broader environment or
publication authentication is asserted.

Reuse checks eligibility, invokes the original module verifier, copies regular
files into a fresh `module` folder, invokes the verifier again, checks source
stability, and records provenance outside the module inventory. Verification
compares every copied byte against the original eligible module and reruns the
impact assessment. Rewriting outer artifact hashes cannot bless changed result
content. Links/junctions are not traversed. The existing common-data exporter can
consume the copied result and generate a fresh report. Original verifiers may
reconstruct arithmetic; avoiding the production entry is not avoiding all maths.

## First CLI slice evidence (historical)

Twelve controls cover independent branch reuse after another source changes,
downstream invalidation, real calculation/report propagation, context isolation,
method/detector/profile drift, artifact inventory changes, malformed plans,
coherently rehashed archive/result tampering and root CLI. The explicit electrical
control is synthetic: a25%load increase produces25%more design current while the
independent branch is reused through its original verifier.

The existing actual80terminal HVAC inputs also execute in an isolated agent
verification study. A copied baseline result passes its original verifier and
preserves the entire payload. A separate immutable scenario changes one declared
assumed heat-capacity value from1006to1010J/(kg K): all80maximum/minimum flows
scale by1006/1010, while total thermal cooling stays unchanged. The ledger
invalidates analysis, common data/report and review for that changed scenario.
Both scenario workflows and the baseline reuse remain independently verifiable;
all3original source files are unchanged. This is a controlled propagation test,
not a recommended design optimization, course adoption or ADPI acceptance.

The measured local copy-plus-verification operation takes approximately0.26s in
that study. This excludes fresh common-report generation and is not a speedup
comparison against a full workflow. Byte counts/times are observations, not a
performance guarantee or RAM benchmark. The actual copied module has2files/
168262bytes. A cold import of only the new CLI adapter takes0.0115s and peaks
at779567Python-traced allocated bytes; it loads no Shapely/Fluids/IFC/Manifold/
SQLite engine. This is not whole-process RAM or core-execution measurement.
Private originals and detailed numeric
results remain in ignored runs. See evidence/changes-first-slice.json.

The durable compatibility group has117cases:116pass,1existing offline-OCR sample
skip, no failures/errors; all_tests_pass=false. Its receipt is independently
verified. The minimal numerical profile passes12change controls. CI now includes
these controls on Windows/Ubuntu; configuration is not completed execution proof.

The following selective replay now integrates this slice with MCP/workflow.
Typed parameter-value diffs, knowledge-specific ownership, broader tested reuse
paths and a different real-project calculation/CAD-or-report acceptance remain open. There is no generic native-DWG
cache acceptance: reopening and visual plot review remain necessary. No release
or user acceptance is inferred; the complete ordered goal remains active.

## Selective replay through MCP and the original workflow

Start a new MCP connection with this source to discover42tools (the previous
candidate/catalogue of40remains historical). The two additive tools are:

- `bsa_checkpoint_workflow(plan, out, checkpoint)` audits the selected original
  plan/run before creating a fresh checkpoint.
- `bsa_inspect_changes(checkpoint, plan)` returns impact and numerical eligibility.

Call the existing `bsa_execute_workflow` with its optional `reuse_checkpoint`
argument for a fresh run. CLI equivalent: `python -m bsa.workflow execute PLAN
--out FRESH_RUN --reuse-checkpoint CHECKPOINT`. No AutoCAD or user application
restart is required by these operations. A long-running old MCP session will
need a fresh connection to discover changed tool definitions.

All original tasks and requirements remain in the plan. Changed numerical tasks
execute normally; eligible independent tasks copy into the canonical task folder.
The normal downstream calculations/common-data/reports then consume that result.
Native/inherited/unsupported tasks keep original execution. Provider disable,
non-default provider and explicit runtime choices are respected. Empty CLI
runtime defaults do not accidentally disable reuse. No previous manual review
or engineering acceptance is transferred.

Standalone reuse bundle1 remains supported. Workflow reuse uses bundle2: the
receipt lives at `_reuse/TASK/receipt.json`, while `module_result` binds the exact
canonical TASK/result.json. This avoids a duplicate module copy. The normal
workflow input pins now include checkpoint archives and reuse/audit methods;
delivery audit reconstructs the same complete input set. Saved assessment,
canonical output binding, source/current-plan correspondence, byte identity and
regular-file/junction guards are independently verified. `_reuse` is reserved
only for runs explicitly requesting this feature; ordinary older plans retain
their previous task namespace behavior.

Six workflow controls and a real SDK control pass, including changed-branch
single production invocation, downstream report/delivery, disabled providers,
explicit/empty runtimes, missing provenance/pins, foreign output substitution
and actual link/junction replacement. Three existing startup/allowlist controls
also pass with42tools. The durable expanded group has134cases:133pass,1existing
offline-OCR fixture skip, no failures/errors; receipt independently verified.
The minimal profile passes18core/workflow cases without optional solver engines.

The existing actual80terminal source also runs through9successful MCP tool
calls and one catalogue call. Only the modified branch is recalculated; an
explicit unchanged control of the same project is reused byte-for-byte. The
common model matches the new calculation, all80maximum/minimum flows propagate,
and167source inputs retain the changed value as assumed. All4requirements stay
pending review; all3original sources remain unchanged. This control is not a
second physical system or different real project.

Observed tool elapsed times were3.42s for the baseline execution and4.44s for
selective execution with verification in this small case. There is no measured
speedup claim: added audit work currently costs more than the avoided production
entry, and original verifiers still reconstruct arithmetic. Subsequent profiling
must remove duplicate audit work without weakening correspondence checks.
See evidence/selective-replay.json; private numeric/source artifacts remain ignored.

The complete ordered goal is still active. Typed parameter diffs, knowledge
ownership, performance refinement and a different real-project acceptance remain.
No formal release, native CAD acceptance, course adoption or user acceptance is
inferred from these checks.

## Typed source parameter differences

Checkpoint2 additionally copies the exact primary project and request JSON for
the supported air/electrical providers. The snapshots are tied to original module
input hashes and request identity, not merely their editable outer receipt.
Checkpoint1 remains readable; missing parameter history is reported as
`not_recorded`, never synthesized from already changed sources.

The input catalogue's existing ownership/unit mapper is shared rather than
reimplemented. Full verified input-bundle exports retain their previous schema
and values. Comparing new inputs does not invoke a production calculation:
`current_producer_executed=false` describes this comparison operation; actual
execution status remains in fresh workflow tasks. Source assertions remain
unauthenticated. Wrong units or another project identity do not produce numeric
deltas. Unmapped numeric changes retain raw pointers without invented units.

The typed catalogue covers numeric parameters and their annotations. Non-numeric
fields such as circuit phase remain protected by file-level invalidation; zero
parameter changes does not mean the whole JSON is unchanged.

Each task's parameter_changes distinguishes added/removed identities, values,
units/classifications, source-note and source-location changes. Array reordering
preserves owner IDs and reports location changes instead of invented value
changes. Deltas use matching semantic SI dimensions, preserving thermal versus
electrical power. Before values refer to an immutable before_snapshot as well as
the historical source location; after values bind the current source/request.

`bsa_inspect_changes` now accepts parameter_offset and parameter_limit; CLI
`changes analyze` has corresponding flags. Defaults are0/50, maximum limit100.
Total counts and has_more are explicit for mapped and unmapped lists. Long source
notes over2000characters are omitted explicitly with length/hash, not clipped
into misleading partial citations; full notes remain in source snapshots. A
parameter page over1MB reports page_too_large instead of silently dropping rows.

Eight additional controls cover SI deltas, pagination, identity/reordering,
add/remove, long notes, coherently rehashed snapshot forgery, legacy checkpoint
and project/unit isolation. The expanded durable group includes the full core CI
selectors:214cases,213pass,1existing offlineOCR skip, no failures/errors; receipt
independently verified. Minimal26core/workflow/parameter cases pass. The actual
SDK audit confirms42tools/41worker operations, exact routes, unknown-field
rejection and excluded executable overrides.

Actual80terminal MCP comparison identifies only load.specific_heat changing
1006to1010J/(kg K), delta4 in the same unit, both labelled assumed. The unchanged
control reports zero parameter changes; calculation/common-report propagation,
167inputs and4pending requirements remain intact. Its checkpoint has9files/
84559bytes on this host. This is verification of the same existing project;
different-real-project acceptance remains open. See evidence/parameter-diff.json.

A previously missed hard-coded40-tool assertion caused both core CI jobs at
f08e5ad to fail after the catalogue grew to42. The expectation is corrected while
all workspace protections remain. Local complete-core checks and actual SDK
contract audit pass; only new head-specific CI can establish remote recovery.
