# Pressure evidence ledger through MCP

The fixed-host interface reuses source_pressure_ledger and its source/native
replay, existing isolated mcp_worker, artifact_access bounded byte limit and
the pinned official MCP SDK1.30.0. No new pressure solver, coefficient source,
provider runtime or dependency is introduced.

- bsa_run_pressure_evidence_ledger(source,out)
- bsa_inspect_pressure_evidence_ledger(out)
- bsa_list_pressure_evidence_gaps(out,record_sha256,offset=0,limit=20)
- bsa_read_outlet_pressure_evidence(out,record_sha256,outlet_port_guid)

Source is an existing source-native fitting analysis. Paths are relative to the
fixed host BSA_PROJECT_ROOT (or existing repository runs fallback). Clients
cannot select runtimes or change the root. Production output must be fresh and
separate from the source; original sources remain unchanged. Unknown arguments,
workspace escapes and invalid strict integer pagination are rejected.

Run and independent inspection each replay source/native ancestry and may take
several minutes. Configure adequate client read timeout; observation loss does
not establish process termination. Inspection binds both the manifest and
ledger bytes across replay. Summaries include exact ledger hash, artifact path
and outlet identities. Use that inspected hash for subsequent bounded reads.

Gap pages preserve source-research order by affected-outlet coverage; limit is
1..20. An exact outlet read returns signed partial contributions, null numerical
gaps and the unresolved physical/station/friction/joint/terminal/equipment/
boundary scope. Neither operation reruns engineering verification: they read
only the exact inspected saved bytes and say so. Hash checks are correspondence
controls, not authenticated inspection credentials. Changed records, over-limit
payloads and nonexistent/ambiguous outlet identities reject.

Tool success remains review_required with pressure_budget_complete=false,
critical_path=null, fan_duty_Pa=null and design_accepted=false. Coverage ranking
is not hydraulic criticality, partial sums are not lower bounds or fan duty and
parallel outlets are never summed. No new loss value or physical method is
selected. Arbitrary brief design and full whole-agent acceptance remain open.

Seven access/protocol/source-ledger and existing source-to-engineering/worker
regressions pass without skips; a durable receipt records their execution.
Private source/runtime/read records remain in the selected project workspace;
public evidence contains safe aggregate results only.

Actual stdio-client execution completes fresh ledger generation and independent
inspection, with matching summaries and record identity. All 45 numerical gaps
return across three pages; all 20 exact outlet reads match saved contributions,
nulls and global scope. All 33 requirements remain. Inventory is 38 tools;
critical path/fan duty/full engineering acceptance remain undetermined. Private
client records and source data stay in the selected coursework workspace.

Current ledger arithmetic requires relative-only subtotal correspondence and
unique/fully represented straight definitions. Older produced ledgers retain
old method identities and are historical; generate a fresh directory for
current native/source inspection. Saved-byte reads remain explicitly distinct
from fresh verification. See SOURCE_PRESSURE_LEDGER.md.

The current producer/inspector also reconstructs cached boundary paths directly
from port topology before subtotal checks. Graph continuity is separate from
physical joint/installation acceptance. Prior method-bound manifests remain
historical; see SOURCE_PRESSURE_LEDGER.md for reconstruction scope.
