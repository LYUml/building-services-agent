# Committed reference library for MCP clients

The twelfth MCP tool, `bsa_reference_catalogue`, lets a client discover reusable
contracts, documentation, examples and regulation JSON without reading the
tool-repository filesystem. Read a returned `bsa://reference/{revision}/{id}`
resource to obtain exact UTF-8 content, immutable Git commit/blob identity,
original path, byte count and SHA256. `bsa://reference-guide` exposes this guide.

The catalogue accepts `kind` (`all`, `docs`, `schema`, `example`, `regulation`),
case-insensitive path `query`, nonnegative `offset` and `limit` (1–50, default20).
Responses include the exact current HEAD commit, total matching entries and the
next offset. Resource URIs use that immutable full commit, so a later HEAD change
does not silently change previously selected content. The reference ID comes
from the listed path; arbitrary paths, branch names or command options reject.

The adapter reuses the installed Git CLI's `ls-tree`/`cat-file` interface rather
than parsing Git storage, querying a remote service or adding a vector database.
It reads committed ordinary file blobs only. Eligible paths are root README/
third-party notices, top-level `docs/*.md`, contract JSON, example JSON/Markdown
and regulation JSON. Programs, environment files, binaries, symlinks, evidence
subtrees and untracked/modified worktree content are not served. Each resource
must fit within 512 KiB and decode as UTF-8; larger entries remain visible with
`readable=false`. No API can choose a different repository or executable. Repository-discovery
environment overrides are removed for these read-only child calls; the host
environment itself is unchanged.

This library is separate from the host-selected project workspace. It never
modifies the tool repository or project, and does not download anything. Actual
project originals/data still belong in the selected project. New uncommitted
reference edits are intentionally unavailable until committed. A committed
reference may document a historical, failed or unverified capability; listing is
not execution readiness, semantic completeness or engineering acceptance.

A typical host AI can now:

1. Read actual project source passages and the existing workflow/skill guides.
2. Search the reference catalogue for applicable adapter documentation, input
   schemas and declared synthetic example inputs.
3. Read the exact returned resource, retain its commit/path/hash citation and
   inspect its scope and limitations.
4. Derive new project inputs from actual supplied/measured/manufacturer facts,
   explicit assumptions and design targets. Never relabel example values as
   measured project facts or silently adopt another project's climate/code basis.
5. Save fresh JSON inputs and an explicit full-source interpretation, then
   execute and independently verify the existing engineering workflow. Missing
   facts, incompatible contracts and failed/native/manual checks remain pending.

Resources deliberately report `classification` as reusable reference rather than
project fact, and `design_accepted=false`. Existing schemas/engines perform the
actual input validation; the reference service does not certify their coverage.
The host still performs source interpretation, adapter selection and engineering
judgment. References are not an automatic arbitrary-brief planner.

The actual stdio test retrieves five source JSON examples through this interface,
checks their UTF-8 byte hashes, saves them into the independent project and runs
the original authored five-passage electrical/air/water/IFC handoff. Four domain
tasks pass, manual review remains pending, and all requirements survive.
The client no longer reads those input JSONs from the local tool filesystem.
Mini-repository tests verify committed-versus-worktree separation, excluded
paths, pagination, pinned old revisions, unknown identifiers and size bounds.
Six targeted tests pass. See [evidence](evidence/reference-library.json).

Git and the existing SDK are invoked unmodified; no third-party source or binary
is copied, no dependency is added, and upstream attribution remains. Specific
desktop client integration, arbitrary design interpretation, real project input
completion and full CAD/BIM/performance/Hong Kong acceptance remain unfinished.
