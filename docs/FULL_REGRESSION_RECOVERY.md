# Full-regression portability recovery

Current follow-up at implementation 7632371: the fixed-source external-runtime
recovery group passes all eight cases with zero skips, independently verified
receipts and unchanged source snapshots. This includes complete fan/pump recovery,
forgery rejection and no-feasible-candidate controls. All six domain jobs and five
core/profile jobs at that commit have now passed. Whole-repository regression
completed successfully:1840tests, zero failures/errors,258skip outcomes.
Final downloaded receipt/hash/source-byte checks pass; all_tests_pass=false
remains explicit and user acceptance is pending. See
[final full result and all skips](evidence/current-candidate-full-regression.json).
See [recovery evidence](evidence/external-runtime-recovery.json).

The all-extras run at 4e5e028 completed 1,827 tests in 3,726.788 seconds:
12 failures, eight errors and 258 skips. Its actual passed inventory is 1,551;
unittest subtest/class-level outcomes do not form a simple disjoint sum.
The downloaded artifact matches GitHub's ZIP hash and all receipt file hashes;
source_unchanged is true. This is a failed suite, despite six passing domain jobs.
See [exact result and skip reasons](evidence/full-regression-failure.json).

Diagnosis identified platform/deployment assumptions hidden by the development
environment being inside the repository:

- Water providers selected Windows epanet22.dll on every platform. The adapter
  now follows installed WNTR 1.5.0's platform layout without importing native
  libraries into the orchestration process. Path, binary hash, engine version,
  raw-data replay and numerical acceptance checks remain enforced.
- Source/method inventories mixed project files with the exact Fluids method
  files and selected EPANET binary. Those runtime files are outside the source
  checkout on Linux and in many normal installations. Registered providers now
  name their exact external runtime files; they cannot authorize arbitrary files.
  The inherited air-route chain shares a small method-evidence validator for
  pinned Fluids 1.3.1 core.py, friction.py and numerics/__init__.py. The helper
  itself is source-pinned; no package-directory wildcard is allowed.
  Project requests, declared sources and output locations still use the strict
  workspace checks. Source route data are checked separately from method files.
- A missing-Graphviz test supplied a Windows AutoCAD path even on Linux, causing
  an early missing-file error. Its host-path sentinel is now an existing inert
  test file and the test still requires no CAD execution/output. Native DWG
  acceptance is not inferred from that guard fixture.

No geometry, hydraulic equations, units, thresholds, native products or regulatory
clauses were changed. Existing WNTR/Fluids engines and upstream attribution remain.
Water/network CI now exercises registered providers and inherited consumers, with
the required modules/spatial profile instead of relying only on direct solvers.

Local security controls confirm exact platform mapping, hash-bound permitted
methods, rejection of a neighbouring unlisted package file, rejection of unrelated
external files and rejection of promoting a runtime binary into a project source.
Three controls pass. A source copy with its runtime physically outside the copied
checkout is used for native regression. Exploratory runs exposed inherited rule
and route consumers; their partial outcomes are not labelled acceptance. The final
fixed-source targeted regression and corrected Linux CI remain to be inspected.

Follow-up: corrected Linux water job 134019552918 passed its 11 direct EPANET,
seven binding and 29 registered-provider/rule/boundary checks. A 37-case local
external-runtime regression completed with unchanged sources: 33 passed, two
failed, two errored, zero skipped. The remaining friction error identified the
inherited interpolation method file, now included in the exact three-file list.
The mixed path also exposed a variable-shadowing mistake in the new source-data
loop; the loop variable is corrected. A direct replay of the already saved
route now passes source geometry/property/frame preservation, seven local bodies,
six connections and IFC schema checks. No upstream model was regenerated for that
diagnostic replay. The focused eight-case current regression remains pending;
these stage checks are not a whole-suite pass.

The next focused replay reached calculated airflow metadata, then stopped in the
catalogue recovery receipt verifier: that consumer still required inherited method
files to be repository-local. It now uses the same exact Fluids method whitelist,
while explicitly checking plan/original-run/catalogue/target workspace paths and
all hashes. New recovery receipts pin the shared evidence helper, including the
pure pump route. Nine catalogue/import-isolation controls pass locally. Complete
mixed recovery and corrected full CI are still pending; source identity and
artifact checks have not been bypassed to reinterpret old receipts.

The 258 skips are retained explicitly. They request host engines, official source
caches, isolated adapters or explicit native fixtures. Dedicated engine jobs and
local native evidence have their own scopes; they do not turn these skipped calls
into executed tests. The full goal stays active until corrected results and final
candidate evidence are reviewed. No release or user acceptance is asserted.
