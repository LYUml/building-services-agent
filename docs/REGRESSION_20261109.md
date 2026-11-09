# Current native-runtime regression

Full command: `.venv/Scripts/python -m unittest discover -s tests`, observed terminal result: 487 tests in 1076.047 seconds; 1 failure, 13 errors, 38 skips. The suite did not pass. The original local log is `runs/regression-20261109.log`.

All 13 errors report Application Control blocking `_openstudioairflow` import, across native HVAC rules, humidity, geometry, materials and window tests. The single HVAC workflow assertion expected a scoped rule pass but received pending because its energy producer did not pass. A separate persisted reproduction (`runs/regression-energy-probe-v1`) shows EnergyPlus `--version` exits 3236495362 before simulation. Windows CodeIntegrity events 3077/3033 explicitly identify its `energyplusapi.dll` as blocked. These are two distinct dependency failures; an installed executable or package is insufficient availability evidence.

`scripts/probe_energy_runtime.py` runs the version command and OpenStudio import in isolated child processes with 30-second limits. It records raw output, executable hash and return codes, without changing policy or starting a simulation. The actual report is `docs/evidence/moosas-review/energy-runtime-probe.json`; both startup probes fail on this host. Preserve these failures instead of skipping tests to obtain a green result. Historical energy runs remain evidence of their original execution only.

The independent workflow reproduction retains energy=fail, hk=pending and review=pending. No downstream rule or delivery acceptance was manufactured. Revalidation requires successful native startup followed by the affected native tests and actual model runs; startup alone cannot clear engineering or regulatory gates.
