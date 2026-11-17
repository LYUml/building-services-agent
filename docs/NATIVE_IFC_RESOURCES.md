# Reproducible native IFC resource probe

This Windows-only probe compares the original factory and guarded production
path on the existing **synthetic** three-piece route. It adds no engine,
dependency, geometry approximation or acceptance waiver. Win32 counters are
shared with `profile_worker_transport.py`; importing the snippet loads no engine.

Use a Git checkout with the existing pinned `[drawing,bim]` environment:

```powershell
.venv/Scripts/python.exe scripts/profile_native_ifc.py --out runs/FRESH_NATIVE_PROBE --trials 3
```

Choose a fresh output directory inside repository `runs`. The known IFC is copied
from `docs/evidence/circular-elbow/workflow.zip`; no coursework or AutoCAD opens.
Each path runs in three fresh Python processes. The control restores the original
factory only inside its child, without editing production files. Both paths use
the same source model/settings and original native checks. Every returned field
must match; numerical differences above1e-12 fail. Input/method hashes must remain
unchanged. Existing output is never overwritten.

`measurements.json` retains raw samples, medians and exact source/fixture hashes.
Child stdout/stderr logs remain after each completed process. `recorded_git_head`
is the base checkout identity, not proof that uncommitted benchmark files belong
to it; use exact file hashes when reviewing a study.

## Executed Windows study

Public probe, three samples per path, unchanged sources and matching results:

| Metric | Original factory | Guarded production path |
| --- | ---: | ---: |
| Median import/read/extract time | 23.134s | 6.039s |
| Median peak working set | 1862.53MiB | 546.26MiB |

Time decreased73.90%, peak70.67% in this study. Earlier exploratory results stay
separate. The original six import/transport probes passed the shared-counter
smoke with one sample each; this is not a new statistical optimization comparison.
Sanitized samples/script hashes are in evidence/architecture-candidate-check.json.

The timer includes child imports, source JSON reads and checked geometry
extraction; it excludes parent fixture copying and model authoring. Peak includes
child libraries and temporary allocations. These are **not** total-host,
AutoCAD, real-project, Linux or general-engine resource guarantees. Host conditions
can change measurements. No engineering, product or regulatory acceptance follows.
