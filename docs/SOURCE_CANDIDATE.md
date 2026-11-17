# Reproducible source candidate

Current implementation snapshot `7632371` was built twice identically by the
successful Ubuntu core job in run 44081506722. Its retained artifact 14328150516
was downloaded and its outer digest, inner receipt/hash, ZIP CRC, entry count,
size and excluded-path inventory independently verified. Source ZIP: 28,259,139
bytes, 3,687 entries; SHA-256
`b9789071458eb244b02802d8edf21724039f8a5ac3cbbbc8daf87f5a70de3a1b`.
See [current source receipt](evidence/current-candidate-source.json).
Full regression and receipt review are complete; see CANDIDATE_REVIEW.md
for candidate entry and explicit limitations. User acceptance is pending.

The current runtime resolves adapters, contracts, regulation packs and scripts
relative to the source checkout. Preserve that source layout in a candidate.
The wheel audit found only Python package files and metadata; it is not yet a
complete standalone installation and must not be presented as one.

Build a committed snapshot without publishing:

```powershell
python scripts/build_candidate.py --out runs/source-candidate
```

The builder uses the existing Git archive implementation. It never copies the
working tree, native engines, generated environments, ignored project runs or
Git history. It rejects excluded runtime paths, checks required source entries
and ZIP CRCs, and writes the commit, hash, size and Git version in a receipt.
Uncommitted changes are intentionally absent. This is a local candidate build,
not a GitHub release. Extract to a dedicated directory and follow START_USING.md
there, installing the extras needed for the chosen domain. Native engines and
MCP host setup remain explicit.

The committed-reference library additionally requires an actual Git checkout
at the tool source root. For that complete capability, clone the configured
origin and check out the receipt's exact commit, then install there. A ZIP has
no Git object database and cannot serve immutable Git references. The library
must reject it, including copies nested under another repository, rather than
silently reading the parent's unrelated revision. Other archive capabilities
remain subject to their executed evidence.

Executed baseline at commit `4e5e02803346af93592441e974040096ae1fdebe`:

- Two separate source builds are byte-identical: SHA-256
  `2d975fa5d15b7f7dfc491ec968d19fd49f1d88bfc8da02c3160e3b912745183a`.
- ZIP: 28,252,074 bytes; unpacked tracked content: 63,766,973 bytes;
  3,669 entries. This measures source compression, not solver memory reduction.
- Extracted source installed into a fresh Windows virtual environment with
  only the default profile. Doctor and pip check passed.
- That environment executed the office-electrical example through its own
  installed bsa entry point; calculated checks passed and engineering acceptance
  remained false. This is an example execution, not real-project acceptance or
  proof of optional MCP/native engine operation from this snapshot.

The builder itself was added after this baseline commit. The next committed
snapshot must include it and receive its own receipt. Historical receipts stay
associated with their actual source revision.

The Ubuntu core CI job now builds the same committed candidate twice and compares
their hashes. After its checks pass, the source ZIP and receipt are retained for
seven days as `building-services-agent-source-candidate` in that Actions run.
This is a review artifact, not a release. Inspect the receipt's commit and job
result; the presence of an artifact alone proves no native engineering result.
Remote execution is now observed at the current checkpoint above.
