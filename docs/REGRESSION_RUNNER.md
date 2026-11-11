# Retained unittest regression runs

```powershell
.venv/Scripts/python -X utf8 scripts/run_regression.py --out runs/regression-current
```

The default uses the existing stdlib unittest discovery over tests/test*.py.
It does not filter known native failures,enable optional tests,change numerical
criteria,repair packages or alter host policy. Output must be a new directory
under this repository's ignored runs folder. Optional --pattern selects a
narrower filename pattern;such a run is not a full-suite result.

start.json retains revision,tracked changes and SHA256 of tracked files plus
untracked Python/application/test and JSON-contract source. progress.json is an
atomic snapshot of test starts/completions and result counts. unittest.log
captures discovery/test stdout,stderr and verbose results. result.json retains
individual failure/error/skip records,elapsed time,log hash and source changes.
Atomic JSON replacement retries a temporary Windows sharing/access error for a
bounded interval;it does not change permissions or hide persistent IO failures.

passed counts actual unittest addSuccess events. Failure/error events may include
multiple subtests within one invocation;they are not subtracted from invocation
count to invent a pass total. Expected failures and unexpected successes remain
separate. Empty discovery,failed tests or persistent before/after source changes
cannot produce regression_pass=true. A complete result still does not establish
engineering acceptance or prove that skipped capabilities work.

Source hashes detect persistent before/after changes,not every transient change,
runtime dependency byte or executed code path. Freeze development during a full
run and inspect failure traces before assigning a cause. A progress file alone
does not prove that a process remains live;poll the actual execution handle.
If a run terminates without result.json,it has not completed this audit protocol.

Executed runner controls:11 existing module tests pass;an empty pattern is
non-green;a temporary3-test counter probe produces1pass,1skip and2failed-subtest
events without a negative or inflated pass count. Transient/persistent replacement
controls verify bounded retry and preservation of the previous JSON when
replacement cannot complete. These validate reporting only,not a new full
regression. The earlier complete audit remains documented in
REGRESSION_20261111.md until a fresh complete run finishes.
