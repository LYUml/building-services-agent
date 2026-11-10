# Native-runtime and workflow regression

The complete command `.venv/Scripts/python -X utf8 -m unittest discover -s tests -v`
finished with exit1: **988 test invocations in1441.319 seconds, 25 failures,
17 errors and103 skips**. The suite did not pass. The remaining843 invocations
passed; discovery can include inherited/imported tests, so this is not a count of
unique engineering capabilities. The original ignored log is
`runs/regression-audit.log`; its hash and individual issue names are recorded in
[machine-readable evidence](evidence/regression-20261111.json).

The run started at revision8fb7b16. Only documentation and a standalone diagnostic
script were added during execution; application/test source was changed after it
terminated. This report does not turn the subsequent targeted checks into a full
rerun.

Thirteen errors directly report Application Control blocking OpenStudio's
`_openstudioairflow`. One HVAC rule-workflow failure retains its failed upstream
energy producer and pending native checks. The other24 failures and4 errors are
in water/circulation and dependent saved-model/pump workflows. A fresh circulation
example and isolated WNTR1.5.0 probe independently reproduce Application Control
blocking `_network_isolation` before EPANET execution. Missing raw/pipes/native
producer artifacts and blocked dependent tasks are consistent with that failure;
not every temporary worker traceback was retained, so this does not prove the
absence of other defects in every individual test.

The103 skips leave real coverage gaps, including optional AutoCAD, isolated
numerical and energy runtimes. Historical native executions do not clear those
gaps for the current host. No tests were weakened, source thresholds relaxed,
security settings changed or blocked libraries replaced to obtain a pass.

After this audit, EPANET failure reporting was improved to preserve separate
`application_control_block`, `timeout` and generic worker/result-error categories,
with a worker-log evidence reference. No hydraulic results or design pass are
created from an engine startup failure. Twelve targeted checks pass for this
diagnosis, pure input/network calculations and inherited drainage workflow. An
actual source-example rerun reports the policy block and no pipe results. This
improves recovery decisions; it does not repair the blocked native runtime or
establish full project acceptance.

Use [water diagnostics](WATER_RUNTIME.md) and the existing energy probe to recheck
an approved environment. Successful imports alone still require real solver,
geometry, engineering and jurisdiction acceptance. Unaffected work can continue
through verified pure calculations, requirements, supported CAD/IFC authoring and
source-bound fixture-demand tools within their documented scope.
