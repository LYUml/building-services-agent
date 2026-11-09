# Upstream three-phase power-flow evaluation

The existing electrical adapter calculates conditional single-phase circuit loads and tabulated voltage drop; it does not solve a three-phase network. Before adding an engine, evaluated upstream [pandapower 3.5.6](https://pypi.org/project/pandapower/3.5.6/) and its [sequence-frame three-phase solver](https://pandapower.readthedocs.io/en/v3.5.6/powerflow/ac_3ph.html). The original probe calls upstream network/line/asymmetric-load APIs rather than rebuilding a load-flow solver. BSD-3-Clause LICENSE and AUTHORS are retained in `docs/evidence/pandapower`.

## Executed scope

The upstream annotated tag `v3.5.6` resolved to source commit `fe517927858f8ffb8ef28db5a15f1a175f57dbbd` during review. Installed-wheel hashes are the runtime artifact pins; tag resolution does not establish a reproducible wheel build from that commit.

On 2026-11-09 an isolated Windows CPython 3.12 environment installed and executed pandapower 3.5.6 with NumPy 2.4.6, SciPy 1.18.1 and pandas 2.3.3. `pip check` passed. The exact selected package artifacts and SHA256 hashes are pinned in [the platform-specific lock](evidence/pandapower/requirements-win-py312.lock.txt). The existing engineering environment was not changed. This lock covers selected Windows wheels, not other operating systems or a full transitive license audit.

```powershell
.venv/Scripts/python -m venv tools/pandapower-runtime
tools/pandapower-runtime/Scripts/python -m pip install --require-hashes -r docs/evidence/pandapower/requirements-win-py312.lock.txt
tools/pandapower-runtime/Scripts/python scripts/probe_pandapower.py --out runs/new-three-phase-trial.json
tools/pandapower-runtime/Scripts/python -m unittest discover -s tests -p test_pandapower_trial.py -v
```

The probe's inputs are explicitly synthetic: 400 V line-line, 50 Hz, one 50 m sequence-impedance line, wye constant-active-power loads, zero reactive load and zero shunt capacitance. Source sequence/short-circuit inputs and line resistance/reactance are declared in the script, not inferred from Hong Kong practice. The 100 A comparison is a synthetic trial target, not verified cable ampacity or a regulation limit.

Three actual upstream solutions were retained in [the numerical evidence](evidence/pandapower/three-phase-trial.json):

| Case, per-phase electrical kW | Observed result | Verification |
|---|---|---|
| 5 / 5 / 5 | Receiving voltage about 230.72338 V line-neutral | Balanced constant-power analytic voltage error below 1e-5 V |
| 10 / 5 / 2 | Different phase voltages/currents | Independent phase-domain sequence-impedance voltage equations, current/load reconciliation, total power balance and resistive loss checks |
| 30 / 5 / 2 | About 131.11 A on phase A | Numerical checks pass while the declared 100 A trial target fails; convergence is not design acceptance |

The independent voltage check uses the line's phase-domain matrix reconstructed from positive/zero-sequence impedances and load currents from complex power/voltage. It checks phase angles as well as magnitudes. The balanced check solves the two-bus constant-power quadratic independently. Tolerances are numerical trial criteria, not installation or code allowances. Fault-injected line current, receiving voltage angle and source active power each cause the appropriate verification checks to fail. Two trial tests passed in the isolated environment. Without pandapower installed, the main test environment skips them rather than claiming runtime execution.

## Remaining integration and acceptance

Reactive absorption and total source reactive-power balance are also reconciled for these zero-load-Q cases. A deliberately altered source reactive result is detected. This checks the trial's reactive bookkeeping, not general nonzero-Q load support.

This is an executed upstream selection trial, not a production workflow adapter or a three-phase design. It has no arbitrary source-backed project schema, multi-bus/transformer/meshed-network verification, reactive-power validation, cable/neutral/harmonics/protection selection, motor starting, native electrical topology, saved CAD/BIM binding or Hong Kong regulatory acceptance. Do not feed three-phase loads into the original single-phase adapter or select this probe as an assignment deliverable. Next integration must preserve explicit sequence/source/PQ data and independently audit all supplied buses/branches; the two-bus checks alone cannot establish general network correctness.
