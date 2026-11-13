# Native source-network analysis through MCP

For composed projection/layout/native delivery and inspection from an AI client,
see [MCP source-network delivery](MCP_SOURCE_NETWORK_DELIVERY.md).

Additional paginated fitting-request and directed-detail read tools are described
in [fitting request access](MCP_FITTING_REQUESTS.md); current inventory has32 tools.
The four analysis/inspection tools below keep their existing roles.

Four tools connect the existing source_network_analysis and source_fitting_data
adapters to the fixed local MCP host. No new engine or dependency is introduced.
They reuse official MCP SDK1.30.0, strict existing argument validation, isolated
fixed-operation workers and host BSA_PROJECT_ROOT. All tool paths are relative
to the host-selected project. Documents cannot select runtimes or a workspace.

- bsa_run_native_network_analysis(source,out): replay the existing source-bound
  native construction and calculate inherited graph flows and straight friction.
- bsa_inspect_native_network_analysis(out): independently replay the record's
  complete source/native ancestry and return compact artifact identity.
- bsa_run_native_fitting_analysis(analysis,basis,out): replay verified analysis,
  evaluate explicit source tables and separately record transition end straights.
- bsa_inspect_native_fitting_analysis(out): independently replay those source,
  native, table, method and pressure-path records.

Run tools require fresh output directories and preserve their input models and
records. Summary fields retain original requirement/outlet/fitting counts,
conditional table counts, transition study counts and the saved record path,
SHA256 and size. The full record remains in the selected project. Inspect calls
bind the summary to unchanged record bytes across independent verification.
Native numerical imports execute in workers rather than protocol threads.
Long ancestry replays need an adequate client read timeout; a timeout alone must
not trigger a duplicate producer. Inspect the actual worker/process outcome.

Tools do not replace source interpretation, supply missing coefficients, modify
models, select fan products or create new DWG acceptance. Status stays pending,
pressure_budget_complete and design_accepted stay false, and critical_path stays
null. The actual engine's source/construction assumptions and full requirement
set remain in saved records. Protocol success means executed access, not design
approval or general autonomous modelling.

The interface closes a concrete gap: these recent verified native analysis
adapters previously required direct module invocation, while the existing MCP
package interface covered an earlier interpreted HVAC chain. Existing package,
workflow, source-page and delivery tools remain separate. No legacy record is
rehashed to conceal method drift; new engine versions require fresh runs.

## Actual protocol evidence

The real BSE3227 project executes through a separate stdio client using the
fixed selected workspace. Fitting execution returns31/76 conditional paths,
31 separate transition end-straight studies and pending engineering acceptance;
its independent inspection agrees exactly, adding integrity_pass=true. Source
records/grids and full private responses remain excluded from public snapshots.
Protocol controls exercise schema exposure, rejected external paths, unknown
runtime overrides and missing records without creating a producer directory.
Existing package and source-handoff regression tests remain separate evidence.

All four tools execute against the real project, including fresh network
production and its independent inspection (33 requirements,20 outlet paths,
76 fitting paths). Both inspectors agree with their corresponding execution
summaries exactly, with integrity_pass=true. Five targeted protocol/native
checks and four existing-source/recovery/package regressions pass with verified
runner receipts and no final-suite skips. The earlier regression attempt retains
its failure caused by the old24-tool inventory assertion; that milestone had
28 tools and its fresh four-test regression passed. An optional unrelated PDF
trial was skipped in that earlier broad attempt and is not counted as passed.
No application UI setup, native model writing or whole-design acceptance is
claimed. See evidence/mcp-native-network.json for safe aggregate evidence.
