# Native energy workflow usability

On 2026-11-17, the installed OpenStudio 3.11.0 and official EnergyPlus
25.2.0 executable ran successfully again. The earlier import-policy failure
did not reproduce; no security policy, system association or user application
was changed. Its failure diagnostics remain supported.

## Actual execution

The existing annual example, saved-IFC annual example and fixed-size PTAC
example completed using the existing adapters. Each baseline/variant contains
8760 hourly records for the declared 2025 calendar. These are synthetic
capability models with Chicago TMY3 weather, not Hong Kong weather or BSE3227.
Source models, weather, native outputs and execution logs remain in ignored
local runs; the compact public receipt is
[native-energy-usability.json](evidence/native-energy-usability.json).

The PTAC baseline/variant results are:

| Quantity | Baseline kWh | Variant kWh | Energy type |
|---|---:|---:|---|
| Supplied cooling | 3885.664 | 3129.856 | Thermal |
| Supplied heating | 4989.067 | 5736.821 | Thermal |
| Lighting | 3321.936 | 1660.968 | Electricity |
| Explicit PTAC components | 6390.277 | 6900.089 | Electricity |

The lighting reduction increases heating and PTAC electricity in this example.
Thermal quantities must not be added to electricity. Synthetic fixed equipment
ratings and unity modifier curves do not establish manufacturer performance,
plant COP, whole-building energy savings or design acceptance. Unmet-zone
series were zero and the component accounting checks passed for this example.

The exact executable SHA256 is
`51715987663666eaff1c8d3bd6ac2d7fe0486d8bc93673eea87c6912a79103f0`.
Native completion remains `verified_with_known_unwritten_sql_flags`: raw SQL
FALSE/FALSE flags were preserved and the existing exact-build exception was
checked alongside successful exit/end reports, complete data and no severe
errors. See [completion constraints](ENERGY_COMPLETION.md). Each PTAC case
retained five default life-cycle-cost warnings; no economic analysis is claimed.

## MCP result channel repaired

Actual native execution exposed a protocol failure: OpenStudio C++ messages
bypassed Python stdout redirection and contaminated the worker JSON response.
The calculation itself had completed. The parent now allocates a fresh private
temporary response file, while both worker diagnostic streams go to MCP stderr.
Only the strict UTF-8 JSON envelope is interpreted as the response. The parent
checks the envelope and process exit code and cleans up the temporary directory.
No tool/document can select that response path. The fixed operation whitelist,
workspace guards and explicit host executable paths remain in force.

All 46 files from the first successful calculation were preserved while its
diagnosis was recovered without recomputation. A separate new MCP connection
then completed annual execution, diagnosis and pending delivery review through
the repaired channel. The one original source requirement remained present.
Successful execution explicitly returned `design_accepted: false`.

Actual test groups: 44 energy/binding/material/window/PTAC tests passed with
the native executable explicitly enabled and no skips; 14 MCP regression tests
had 13 passes and one explicit missing-PDF-fixture skip; four drawing/MCP
regressions passed; five final response-channel/native-annual tests passed.
These are test counts, not simulation counts, and the groups overlap.

## Entry and remaining scope

Use the existing [annual CLI commands](ANNUAL_ENERGY.md) with a fresh output
directory, or the [project-scoped MCP setup](CODEX_LOCAL_SETUP.md) with an
explicit `--energyplus` host path. The local project configuration now includes
that path; other host controls were preserved. New connections were verified.
The existing desktop chat was not restarted and hot reload is not claimed.

This milestone restores bounded native energy use through CLI and MCP. It does
not establish that every optional engine or arbitrary project is ready. Full
agent work remains active; BSE3227 is unchanged awaiting user feedback.
