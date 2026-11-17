# Release candidate hardening

The user reopened the goal on 2026-11-17: prepare a modular, lighter, debugged
candidate for user acceptance before any formal release. The earlier
[usability checkpoint](USABILITY_ACCEPTANCE.md) proved bounded workflows, not
release maturity. No release/tag is authorized by this hardening work alone.
BSE3227 and read-only history remain outside these implementation changes.

## First measured improvement: worker diagnostics

MCP previously used `capture_output=True` for each engineering worker, then
decoded its complete stdout/stderr. Large native logs therefore allocated full
byte buffers and decoded text in the protocol parent. The worker result already
used a separate private JSON file; diagnostic buffering was unnecessary.

Process execution, diagnostic decoding and response validation now live in
`bsa.worker_transport`, separate from MCP tool definitions. The existing fixed
operation whitelist, serialized execution, source/workspace guards, private
result file, strict JSON envelope and return-code checks remain. Diagnostics
use temporary disk storage, merge stdout/stderr and forward to server stderr
in 64 KiB reads. Incremental UTF-8 decoding preserves characters crossing read
boundaries and retains replacement behavior for invalid log bytes. JSON results
remain strict UTF-8. Full logs are forwarded; they are not truncated or discarded
by the production transport. Temporary files clean up on success/failure.

Three fresh-process Windows trials per case measured median peak working set:

| Probe | Before MiB | After MiB |
|---|---:|---:|
| Quiet MCP worker call | 60.17 | 60.36 |
| Worker emitting 32 MiB diagnostic stdout | 156.31 | 60.18 |

The noisy case's parent-process peak falls about 61.5%. This is a controlled
transport stress case using the actual fixed reference operation, not a building
simulation or a claim about total host/solver memory. The child and SDK client
have their own memory. Disk buffering adds temporary I/O. Import/startup times
were also recorded; no broad startup speedup is claimed.

Run the standard-library Windows profiler from the intended environment:

```powershell
python scripts/profile_worker_transport.py --out runs/FRESH_PROFILE --trials 3
```

Thirteen targeted transport/startup/dependency tests pass. Actual SDK project,
coupled-pump and native annual analysis regression runs five tests: four pass,
one explicit missing-PDF-fixture skip remains. These are not a complete release
matrix. See [measured evidence](evidence/worker-transport-memory.json).

## Remaining candidate gates

- Core CI now has explicit minimal and SDK integration profiles, and the PDF
  test generates its own recorded fixture.48minimal-profile and5actual SDK/native
  tests pass locally without skips. Remote results and legacy domain jobs remain
  unverified/unreconciled; see [CI profile evidence](CI_PROFILES.md).

- Freeze supported platform/runtime/profile contracts and map promised project
  operations to actual MCP calls; identify explicit host/manual preparation.
- Make installation and candidate artifacts reproducible; measure distribution
  and installed-profile sizes without bundling generated environments, runtime
  caches or private project records. Preserve supported features and notices.
- Repair/align CI with that support matrix and retain actual failures/skips.
- Verify a real-project input revision propagates consistently through the
  calculation, drawing, equipment table and report, preserving the baseline.
- Continue measured module/import/memory optimization and failure recovery,
  with checks appropriate to each change; no speculative solver rewrite.
- Supply the candidate, measured comparison, clear entry and known limits for
  user acceptance. Do not publish or infer acceptance automatically.

The disk baseline is 63.64 MB of tracked repository files, 1.079 GB in the full
development site-packages and 180.40 MB in the clean drawing/MCP site-packages.
These profiles intentionally differ. Counts exclude native engine directories,
Git history and ignored runs; they are not release artifact sizes. No dependency
or history was deleted to manufacture a reduction. Dependency/distribution
slimming remains work to do, not an achieved result.
