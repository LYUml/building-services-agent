# Full regression after modular integration

Default unittest discovery finished at revision
`b74f03038035094f5695180cb20aaffd48fe0302`: **1,136 invocations,
1,019 passes, 1 failure, 13 errors and 103 skips**, in 1,972.719 seconds.
The process exited 1; the suite did not pass. All tracked source and the runner's
additional source inventory remained unchanged throughout execution.
Counts are invocations, not unique engineering capabilities.

Command: `.venv/Scripts/python -X utf8 scripts/run_regression.py --out runs/regression-modular-full`.
The complete result and verbose log remain in that ignored directory.
[Public evidence](evidence/regression-modular-20261111.json) retains their hashes,
all issue names, skip reasons and separately executed runtime checks. This run
supersedes the earlier [regression snapshot](REGRESSION_20261111.md) for the tested
revision; it does not erase historical failures.

## Failures and runtime boundaries

All 13 error tracebacks explicitly report OpenStudio import failing at
`_openstudioutilitiestime` because an Application Control policy blocked the file.
They cover HVAC IDF rules, sizing humidity, thermal geometry, materials and
windows. The single HVAC workflow failure is an assertion that its rule task
should pass; the recorded task instead remains pending because the upstream
energy producer did not pass. That assertion alone does not retain the deleted
temporary producer's traceback. A separate fresh energy startup probe confirms
the current OpenStudio import block. EnergyPlus 25.2's `--version` does launch;
that is not a simulation or proof that the complete energy adapter can execute.
No security policy, binary or test acceptance criterion was changed.

Water availability differs from the previous snapshot. All 11 invocations in
test_epanet pass. A fresh WNTR 1.5.0 import probe passes, followed by an actual
`bsa.epanet` run of the public water-loop example. Its EPANET 2.2 runtime produces
native results and all 12 recorded checks pass, including mass balance, pipe
energy and pump curves. The report and library/source hashes are retained in
the evidence. This updates current scoped availability, not manufacturer,
installed-system, regulatory or complete design acceptance. The cause of the
change from the prior policy failure is not established.

## Coverage still missing

The default run enables no optional native flags. The 103 skips include actual
annual EnergyPlus, explicit AutoCAD/OCR, isolated three-phase numerical runtimes,
official-source-cache integrations and Radiance tests. Exact reasons and test IDs
remain in the evidence. A skipped test does not prove a runtime is unavailable;
historical native runs do not replace executing that check for this revision.

Two ignored exceptions from IfcOpenShell `file.__del__` report a `KeyError` in
the raw log. Their enclosing tests pass; they are not counted as unittest error
events. Impact is not established, and the warnings have not been suppressed.

Module contracts, authoring/spatial/thermal preparation, air budgets and fan
handoffs now have full-suite context, but this result does not establish actual
inherited annual simulation, general provider interchangeability, real-coursework
completion or complete multi-discipline engineering acceptance. Keep those
requirements pending and continue development with the retained runtime boundaries.
