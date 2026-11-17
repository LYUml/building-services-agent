# Core CI profiles

The new `.github/workflows/core.yml` checks explicit dependency profiles rather
than inferring that a full development environment is the minimum installation.
This is part of release-candidate hardening, not a completed release matrix.
The existing `check.yml` domain jobs are retained unchanged and may still expose
their existing coverage/dependency issues. No failing domain was disabled.

| Job | Environment | Checks |
|---|---|---|
| core | Windows and Ubuntu, Python3.12; drawing/MCP/setup extras | Setup, explicit profile doctor, pip check and48core tests |
| mcp-integration | Ubuntu, Python3.12; same extras plus IFC/network; host Poppler | Actual SDK source/handoff, PDF rendering, recovery and rejection tests |

The new workflow pins the existing checkout v4 and setup-python v5 actions to
their official source commit IDs, resolved before writing the workflow. It
requests only repository read permissions. There is no publishing/release step.
Poppler is an explicit distribution-managed native prerequisite in the Ubuntu
integration job, not a Python dependency or an AutoCAD substitute.

## Self-contained PDF transport test

The old MCP rendering case required three host environment variables pointing
to an already executed workflow under ignored local runs, so a clean checkout
skipped it. It now copies checked-in public inputs into a temporary project.
A controlled test producer runs the real conditional electrical adapter and
adds a simple rectangular-vector PDF **before** normal workflow inventory.
It does not modify recorded hashes after execution. The PDF is explicitly a
rendering fixture, not a native CAD drawing or an engineering report.

The actual SDK indexes this fresh recorded artifact, renders it with Poppler,
checks returned image bytes/hash against disk, verifies nonblank pixels and
page aspect ratio, and retains engineering/visual pending flags. It also rejects
path escape, a non-PDF artifact, stale workflow identity, invalid page and reused
output. No saved local workflow or proprietary AutoCAD installation is needed
for this rendering/protocol test. A missing host renderer remains an explicit
prerequisite; the integration CI installs/checks it before running the test.

## Executed versus pending evidence

A new Windows dependency environment installed only the core extras against
the current checkout. Its isolated setup, doctor and pip check pass; the exact
new CI core test command runs48tests with zero skips. This is a clean dependency
environment, not a second physical machine. The separate actual SDK/native annual
group runs5tests with zero skips, including the formerly skipped PDF case.
No CFD, AutoCAD or whole-repository regression is inferred from these counts.
See [local evidence](evidence/self-contained-core-ci.json).

Remote Windows/Linux Actions results are not inferred from these local passes.
The available classic commit-status response was empty; that does not establish
the state of GitHub Actions check runs. Until actual workflow results are
inspected, the remote matrix remains unverified. The legacy all-test electrical
job and remaining domain coverage still need explicit dependency/coverage review
before candidate acceptance. There is no claim that the repository CI is green.
