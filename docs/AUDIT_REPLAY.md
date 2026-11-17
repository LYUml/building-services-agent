# Operation-scoped source replay

Repeated lighting verification inside one MCP operation previously copied and
parsed the same recorded PDF for every downstream check. This added source
reader work to calculation, export, workflow inspection and artifact access.
The original production extraction and the first independent verifier extraction
still execute. Only later identical source replays inside that same operation
can reuse the verifier's parsed JSON.

The existing fixed worker dispatcher creates one scope and clears it on exit,
including failures. No new tool or worker operation is exposed:42tools and
41operations remain. Direct CLI callers without a scope retain the original
replay behavior. Set host environment `BSA_DISABLE_AUDIT_MEMO=1` to disable this
optimization. Source documents cannot select this option or seed the memo.

The thin helper uses standard-library ContextVar and JSON; no third-party cache
engine is added. It retains at most4entries and128KiB of encoded keys/values per
scope. Oversized values continue through the original path without retention;
exceptions are not retained. JSON copies prevent a consumer from mutating the
memoized observation. This bound describes retained serialized content, not
Python object overhead, temporary parsing allocations or whole-process RSS.

## Checks retained

* Original module/request/source/artifact verification still runs on every call.
* The lighting source adapter rebinds normalized facts to the source JSON.
* Current source PDF path/hash, selected physical pages, room header, provider
  methods and external reader/interpreter pins form the replay key.
* Reader configuration, clean pinned Git state, method hashes and original PDF
  hash are checked before and after every lookup, including memo hits.
* Production extraction never populates this memo. The first verifier performs
  an independent source read, even within a calculation operation.
* Retained parsed facts, recalculated audit, HTML and common payload are compared
  on every verification. Only the nondeterministic excerpt-copy identifier hash
  is excluded from parsed-fact equality, as before. Module artifact hashes still
  bind the actual retained excerpt and logs.

This is parsed-source replay within a host operation. It adds no lighting
result-cache eligibility, no reuse across MCP calls/processes, no acceptance
transfer and no general bypass of verification.

## Actual recorded-project measurement

Two fresh worker/process samples per mode alternate off/on/on/off on the same
existing186fixture lighting source. Both modes use the same current code and
selected project; only the host switch changes. Private proofs are in
`runs/audit-scope-real`, with aggregate evidence in
`docs/evidence/audit-scope.json`.

| Existing MCP operation | Disabled median | Enabled median | Reduction |
| --- | ---: | ---: | ---: |
| Execute complete source-bound workflow | 48.279s | 19.442s | 59.73% |
| Diagnose saved workflow | 12.754s | 5.458s | 57.20% |

All four executions preserve byte-identical calculation JSON and common HTML,
identical188entities, owned input catalogue and source flags. Original sources
remain unchanged; all3requirements remain pending review. A delivery template is
also exercised. This comprises9actual SDK calls plus4catalogue checks. No native
geometry or new photometric calculation is claimed.

These are desktop wall-time observations on one recorded-source workflow, with
two samples per mode; some sampling overlaps regression activity. They are not
general solver benchmarks or RSS measurements. Fresh provider imports still load
none of pypdf/IFC/NumPy/SciPy/Fluids/MCP: three samples take0.150–0.163s and peak
about6.04MB Python-traced allocations. No memory reduction is asserted.

New controls cover missing/disabled scopes, exception isolation, nested scope
restoration, defensive copies, entry/size limits, worker lifecycle, independent
first replay, method/runtime drift, changed source files and coherently rehashed
bad calculation artifacts. The selected187-case architecture regression passes
with zero skips and an independently verified durable receipt; compatibility
group also passes48cases with zero skips and independently verified receipt
(`runs/audit-scope-compatibility`); total235selected cases, not full discovery. Full-goal knowledge-specific dependency
ownership and final user review remain open.
