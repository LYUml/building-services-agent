# Change impact and verified numerical reuse

The CLI reuses existing workflow receipts, module contracts/provider verification,
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

## Executed evidence and boundaries

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

This first slice is CLI-only. Typed parameter-value diffs, knowledge-specific
ownership, integrated MCP/workflow selective replay and a different real-project
calculation/CAD-or-report acceptance remain open. There is no generic native-DWG
cache acceptance: reopening and visual plot review remain necessary. No release
or user acceptance is inferred; the complete ordered goal remains active.
