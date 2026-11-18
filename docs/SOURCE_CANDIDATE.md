# Source distribution

The source-layout prerelease uses [one-click installation](INSTALL.md).
Download its source ZIP, SHA256SUMS and commit/hash receipt from
[GitHub Releases](https://github.com/LYUml/building-services-agent/releases).
Native engines and optional domain solvers are separately installed.

Build committed source without publishing:

```powershell
python scripts/build_candidate.py --out runs/source-candidate
python scripts/package_prerelease.py --out runs/prerelease-assets
```

Both builders use Git archive and reject runtime/private output directories.
Both include a deterministic commit/version manifest. The prerelease builder
uses a versioned filename and produces SHA256SUMS. Neither builder publishes.
Uncommitted files, environments, credentials, coursework and historical runs
are absent. Existing local historical runs remain preserved.

The runtime needs adapters, contracts, regulation packs and scripts in their
source layout. A wheel containing only Python modules is insufficient.
The source ZIPs have no Git object database. Their setup
restores its pinned Git objects for immutable reference retrieval, without
checking out or overwriting working source files. This requires Git and internet.

Earlier candidate evidence remains in the versioned
[source receipt](evidence/current-candidate-source.json) and
[architecture regression audit](evidence/architecture-full-regression.json).
Their commit identifiers identify their own historical snapshots, not the
latest release. Installation, tool execution and engineering acceptance remain
separate checks; publication does not establish user acceptance.
