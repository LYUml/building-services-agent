# Diagnostic watchdog for long full-suite checks

The first all-extras full-regression jobs remained in their test phase for
approximately an hour without a terminal result. Their stdout is a retained
execution log, so job state alone cannot distinguish a slow suite from a
particular test that never returns. The existing jobs were not cancelled or
restarted on that observation.

The durable check runner now also records loading, per-test started/finished and
completed events in progress.jsonl. That file is hashed into new receipts and
retained in CI artifacts. Historical four-artifact receipts remain verifiable
within their original source/interpreter scope. Success still requires a real
tests.json, matching source snapshot, actual process return and observed counts.

The optional host argument `--test-timeout SECONDS` uses CPython's existing
faulthandler watchdog. CI selects 600 seconds, reset at each test start and also
covering initial loading. It emits the real Python stack and exits the worker
if the budget expires. It is not an engineering/solver threshold, test skip or
passing result. Missing final test counts yield worker_incomplete and a failed
check receipt. Default CLI behavior remains unchanged without this argument.
This cannot recover an interrupted test or certify all remaining tests ran.

The failure step prints bounded execution/progress tails; artifacts preserve the
full recorded files. The diagnostic job therefore can identify the last started
test even if a native call stalls. It does not retroactively change older live
jobs or prove why they are slow. Inspect the new actual result before diagnosing.

For a local run that must continue during development, use a separate checkout
at the recorded commit. Confirm that `bsa.__file__` resolves inside that checkout
before starting, especially when using Python from an existing editable install.
Run against synthetic fixtures in that checkout and keep the output under its
`runs` directory. Do not update the checkout while the run is active. This
keeps source-bound recovery tests from correctly rejecting concurrent method edits.

```powershell
python -m bsa.check_runner run tests.test_catalogue_iteration tests.test_revit_revision --test-timeout 60 --out runs/pinned-diagnostic
python -m bsa.check_runner verify runs/pinned-diagnostic
```

Both commands ran in a detached checkout of `5001f64`. The verifier reconciled
14 passing tests, their progress records and the selected source hashes.

Local evidence: 13 check-runner controls pass. A real controlled child sleeps
beyond a one-second watchdog: it exits unsuccessfully with a traceback, retains
loading/started events, and creates no completed test result. Invalid budgets
reject before creating outputs. A normal four-test electrical run under a
30-second watchdog passes with independently verified counts, progress hash and
unchanged sources. Production engines and engineering criteria are unchanged.
