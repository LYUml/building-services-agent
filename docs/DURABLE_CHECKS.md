# Durable host check receipts

Long native checks can finish after a terminal/session view disappears. Use the
standard-library unittest runner with durable local log, actual test counts and
process return code instead of inferring success from the last console message.
No new testing framework, engine, dependency or desktop configuration is added.

```powershell
python -m bsa.check_runner run tests.test_recovery_controller --out runs/NEW_CHECK
python -m bsa.check_runner verify runs/NEW_CHECK
```

Only explicit repository unittest selectors are accepted (module, class or method),
not arbitrary command strings. Output must be a fresh directory under this tool
repository's runs. This is host development/test execution, not a document-driven
MCP command API. Existing tests retain their own workspace/native/runtime rules.

The parent saves request.json with selected source hashes and interpreter identity,
started.json with actual child/host PIDs and start time, and execution.log directly
from the child stdout/stderr. The child writes tests.json from TestResult callbacks,
including actual executed/passing test IDs, failures/errors, skips and expected/
unexpected outcomes. The parent waits for the real process return code, compares
source snapshots and atomically writes receipt.json. Files are flushed before
atomic replacement. Existing outputs are never reused or overwritten.

A valid successful suite needs at least one actual passing test. An all-skipped or
zero-executed suite cannot turn green. suite_pass permits explicit skips/expected
failures alongside actual passes; all_tests_pass requires every executed test to
pass without those exclusions. Subtest failures and class-setup errors are counted
as unittest actually reports them, even when failure/error counts exceed testsRun.
A failed test can have an integrity-valid receipt while suite_pass remains false.

The verifier checks recorded file hashes, counts, process-result consistency,
current interpreter and selected current source bytes. Source changes invalidate
current verification; historical files are preserved rather than rehashed. A
missing terminal receipt means incomplete evidence even if a worker result exists.
started.json or a PID alone never proves that a process is currently live. Inspect
the actual process/session before deciding to wait, stop or restart work.

## Limits

These are local execution records, not authenticated provenance or a malicious-
forgery defence. Before/after snapshots do not detect transient edits reverted
before completion. Selected control files are src/tests Python, contracts and
regulations JSON and pyproject.toml. Native engines, all installed dependencies,
external project inputs and optional environment flags are not comprehensively
captured by this receipt: keep each domain's existing pinned evidence/audits.
The wrapper does not certify applicability, coverage, visuals or engineering
acceptance; design_accepted always remains false. It cannot repair or resume a
killed parent. Retain partial logs and independently establish terminal state.

Test logs and runtime receipts stay ignored under runs; never publish private
coursework, credentials, protected sources or environments from their contents.
Only scoped aggregate verification evidence belongs in public documentation.

Actual durable run: 34 tests passed with no top-level skips; process return code
0, unchanged selected source inventory and independent receipt verification.
Nested control runs exercise failures/skips/source drift without promoting them
to engineering acceptance. See evidence/durable-checks.json.
