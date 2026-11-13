# Bounded fitting-request reads through MCP

After bsa_inspect_native_fitting_analysis, take the returned fitting-data.json
artifact SHA256. Pass that exact identity to:

- bsa_list_native_fitting_requests(out,record_sha256,offset=0,limit=20,status=null)
- bsa_read_native_fitting_request(out,record_sha256,product_guid,inlet_port_guid,outlet_port_guid)

The list returns stable directed-path identities, fitting type, recorded status
and affected-outlet count. Follow next_offset until null. Optional status filters
retain the original recorded states; totals apply to the filtered set. Page size
is1..20. A detail read requires the full body/inlet/outlet tuple, so two exits of
the same fitting are not confused. Missing or ambiguous matches reject. Details
retain native quantities, inherited flow/classification, source assumptions,
missing evidence, recorded source-table result and separate transition straight
study when present. Publisher grids and original documents are not returned.

These are reads of saved bytes, not a repeat native/source/engineering check.
The returned verification field says so explicitly. Source or method freshness
must be established by inspect; a supplied hash alone does not authenticate
provenance or clear physical applicability. No read changes an acceptance state.
A wrong or stale record hash rejects, including whitespace changes. A single
bounded byte snapshot is hashed and decoded, avoiding a hash/read mismatch.

Reuse: existing artifact_access.LIMIT (2MiB), host workspace rules, SHA256 and
fixed-operation isolated MCP workers. No solver, dependency or alternate model
is added. Original whole-workflow artifact access remains for workflow outputs;
these newer source-native records have their own producer/inspector ancestry.
They are not silently assigned an unrelated workflow receipt. Oversized records
reject rather than partially parsing or dropping requirements.

The private real-project trial first independently inspects the complete source
and native record, then pages all76 fitting paths and reads examples from all
three current status groups plus a transition with its separate end-straight
study. Saved identities, unresolved states and unchanged pressure acceptance are
preserved. Actual results are summarized in evidence/mcp-fitting-requests.json;
source records and detailed coursework responses remain private.

Actual execution reads76 unique body/inlet/outlet identities across four pages,
plus four details spanning three status groups and a transition with its
end-straight study. A final-code client repeats all76 identities and transition
details, and rejects boolean, string, zero and over-limit page sizes. Source
inspection precedes the original trial; final reads enforce its unchanged record
identity without claiming another native replay. Three targeted tests pass with
a current verified receipt, including exact-direction, stale-byte, workspace,
oversized-record and real stdio controls. No coefficient is changed or added.

Four existing MCP source-handoff/recovery/package regression tests also pass.
Both final runner receipts independently verify against current code with no
skips. Earlier receipts retain their source-drift status after strict pagination
annotations were added; they were not rehashed to claim current verification.
