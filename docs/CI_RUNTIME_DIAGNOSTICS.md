# Runtime diagnostics and full regression recovery

Observed remote commit: `68d59697ac27eb892768566e3fe5c0cca5c7f3e6`.
Core run 44057101878 passed all four jobs: Windows core, Ubuntu core,
pure pump-network and coupled MCP integration. Domain run 44057101944 passed
energy, lighting and network; water, IFC and electrical failed.

The electrical job ran broad discovery in a minimal dev environment, producing
414 errors including missing optional packages. Its 19 electrical tests passed.
Electrical checks now explicitly select those tests; full discovery remains in
a separate job installing all declared Python extras. This does not increase
the default user installation. The durable runner accepts fixed `--all`
discovery, rejects mixed selectors and stops before test bodies on load errors.
The full job retains its execution log and integrity receipts as an artifact.

IFC coordination fixtures previously wrote outside the selected workspace.
Two fixtures now use owned runs; no production workspace guard was relaxed.
Four local coordination checks pass. Remote correction remains unverified.

Water failed inside the Linux worker with insufficient retained detail.
The cause remains unresolved. EPANET failure results now include an 8 KiB
diagnostic tail and total byte count, using a shared 64 KiB chunk reader.
Application-control classification still scans the entire log, including
markers crossing chunk boundaries. Failure never becomes a hydraulic result.
The CI water job runs a native smoke case before tests to expose the real trace.
Windows native EPANET smoke remains successful; this proves no Linux result.

Local checks for this change:

- Core command: 71 pass, zero skips, in the existing core-plus-network environment.
  This is not a new clean minimal installation claim.
- Durable-runner suite: 11 pass, including discovery preflight and zero-body failure.
- Runtime diagnostics, policy recovery and coordination group: 9 pass.
- Durable diagnostic execution: 3 pass with successful receipt verification.
- Full-profile collection: 1,841 collected instances, no load errors, zero test
  bodies executed. This is collection evidence, not a full-suite pass.

No release, course design change or user acceptance is asserted. Next remote
results must resolve water diagnostics and establish the full-profile baseline.
