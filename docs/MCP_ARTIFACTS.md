# MCP workflow artifact inspection

Use bsa_artifact_index(plan,out) on an executed workflow directory. It reuses
bsa.delivery.context and workflow verification to check current source bindings,
requirement/task correspondence and recorded input/runtime/artifact hashes.
The response includes workflow_sha256, recorded artifact paths, SHA256, sizes,
task statuses, requirement count and original unresolved inputs.

Pass that workflow_sha256 and an exact recorded path to bsa_read_artifact.
Every read repeats the source-bound audit; changed evidence or an index from a
different workflow is rejected. Unrecorded diagnosis files and traversal paths
are not available. Resolved files must remain inside the run and both plan/run
must remain within the host-selected project. Reads are bounded to 2 MiB; larger
files remain listed and require a future streaming/export adapter. UTF-8 content
is returned literally; non-UTF-8 bytes use base64 with the original SHA256.

These tools inspect saved bytes, not geometry quality or professional approval.
Pending reviews and source gaps remain pending. Native DWG/RVT reopening and
visual plot review require their existing separate acceptance workflows.
No arbitrary filesystem browser, solver, remote service or dependency is added.

Actual stdio protocol tests passed: three tests, zero skips (60.794 seconds).
JSON and IFC bytes matched saved files; unrecorded/traversal/wrong-index and
tampered-artifact controls rejected. Existing pump recovery also passed.
Evidence: evidence/mcp-artifacts.json. Base64 and oversized-file branches were
not exercised by this protocol trial.
