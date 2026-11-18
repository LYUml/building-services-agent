# Supplied-curve recovery example

This public analytic case demonstrates the existing failed-design iteration
path. It is explicitly synthetic: a 10 mm diameter, 2 m long laminar line with
dynamic viscosity 1 Pa.s, density 1000 kg/m3, zero elevation/local losses and a
100 Pa required outlet total pressure. These are not ordinary water properties
or manufacturer data. No equipment, installation or regulatory acceptance is
implied. All quantities and sources are explicit in the input JSONs.

Use the drawing/MCP environment with the existing pinned network extra:

```powershell
python -m pip install -e ".[network,mcp]"
# Use a fresh destination under the selected workspace; do not overwrite a run.
Copy-Item -LiteralPath examples/pump-recovery -Destination runs/my-pump-recovery -Recurse
bsa workflow runs/my-pump-recovery/plan.json --out runs/my-pump-recovery/baseline
# Exit2 above is expected: pump checks fail and manual review remains pending.
python scripts/run_recovery_mcp_demo.py --project-root runs/my-pump-recovery --plan plan.json --original-run baseline --policy policy.json --out recovery --receipt mcp-receipt.json
bsa delivery verify-recovery runs/my-pump-recovery/recovery
```

If using another project workspace, select its explicit `BSA_PROJECT_ROOT` and
copy the example there. The SDK demo sets that selected root on its new server
connection. It does not configure/restart the desktop application or use native
CAD. Only the supplied catalogue is eligible; no product search occurs.

The catalogue objective is the exact supported contract
`lowest declared preference among passing candidates`. Other objectives reject
with that expected value rather than silently choosing another ranking method.

## Expected and observed results

| Quantity | Failed baseline | Selected analytic curve |
|---|---:|---:|
| Operating flow, mL/s | 1.2 | 2.0 |
| Original required minimum flow, mL/s | 1.5 | 1.5 |
| Flow margin relative to minimum | -20% | +33.33% |
| Pump total-pressure rise, kPa | 9.87848 | 16.39747 |
| Estimated electrical input, W | 0.0237084 | 0.0655899 |

This satisfies the declared numerical duty by increasing flow and input power;
it is not an energy-saving or real pump-selection claim. Independent laminar
resistance is `128 * viscosity * length / (pi * diameter^4)`. At the selected
2e-6 m3/s, pressure rise is `100 + resistance * flow` Pa. Hydraulic power is
`flow * pressure` W; electrical input divides this by the explicitly synthetic
wire-to-water efficiency of 0.5. The test checks these independently.

The controller writes a fresh sibling plan and full replay. Original brief,
plan, network, weak curve and failed run remain unchanged. Inspect the receipt's
`final_plan` and `final_run`: task `pump` passes while `review` remains pending.
Independent verification returns `integrity_pass: true`, one step,
`execution_pass: false`, `design_accepted: false`. A valid but insufficient
catalogue instead stops with `no_feasible_candidate` and retains the failed
baseline. Emptying the candidate list is invalid input, not that control.

Actual installed CLI plus fresh MCP execution and 14 pump/recovery tests pass;
a separate fan catalogue rejection regression also passes. The longer mixed
native replay suite was intentionally stopped and is not counted as passing.
See [public receipt](../../docs/evidence/public-pump-recovery.json).
