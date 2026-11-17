# Clean CI bootstrap and recovery dependency isolation

Actual Actions run44052897722 for ad3552b passed its Windows and Ubuntu core
jobs. The coupled MCP integration case failed with missing `manifold3d` during
recovery import. Separately, original domain run44052897631 failed early: the
IFC/Linux and lighting/Windows logs explicitly show missing repository `runs`
while creating temporary test directories. These were actual remote failures,
not inferred from package lists or reclassified as skips.

## Owned test workspace

All six original domain jobs now explicitly create their owned repository
`runs` directory before tests. No project selection or validation is relaxed.
An independent public-source copy initially had no `runs`; the exact workflow
bootstrap command initialized it, source identity was checked and26domain tests
completed:25pass, one existing opt-in native-lighting skip. Native flags were
deliberately unset in this local bootstrap trial; engine availability is not
inferred. Remaining legacy profile/test-discovery issues are not claimed fixed.

## Optional geometry stays with geometry tasks

Pump recovery reused finite preference ranking from the rectangular-fan module.
Its top-level native path imports and generic recovery's circular-fan imports
loaded IFC/Manifold even for a purely numerical water-pump task. Geometry and
fan modules now load only at their actual domain call boundaries. Existing
ranking, numerical evaluation, mechanical eligibility and independent source/
artifact verification are unchanged; real fan geometry is still checked.

The fully coupled water/electrical example explicitly includes IFC clash tasks,
so its integration profile legitimately requires the existing `clash` extra.
Adding that declared profile is separate from the pure pump import repair.
No geometric validation was removed to make the coupled case pass.

Verified locally:

- Core-only dependency phase:57tests pass with no skips. Its freeze/log is
  preserved before extending that environment with the network extra.
- Core+network phase: IFC and Manifold are physically absent; actual MCP recovery
  completes, retains the failed baseline and leaves manual review pending.
  Five profile tests pass without skips, including the actual SDK case.
- Coupled IFC/network/clash profile: the previously failing coupled SDK case
  passes after its legitimate geometry dependency is explicitly installed.
- Fifteen pump/import/controller and14fan/recovery checks pass. These groups
  overlap; their counts must not be added into a unique-suite total.

## Measured import cost

With identical optional libraries available, three fresh Windows processes per
case compared the retained pre-change source copy with the current source.
Only the three affected product modules differed.

| Pure pump module import | Before | After |
|---|---:|---:|
| Median peak working set | 101.23 MiB | 28.56 MiB |
| Median elapsed import | 0.513 s | 0.042 s |

This measures import overhead, not an entire solver, model or host session.
Actual numerical/model operations still load their required libraries when used.
The profiler now includes a `pump_import` probe. No dependency was deleted;
unused optional geometry is no longer an entry prerequisite for the pure task.

[Evidence and source/log hashes](evidence/ci-bootstrap-lazy-recovery.json) retain
the remote failure observations, local tests and before/after counters. New
remote checks must be inspected after push; previous failures are preserved.
This is candidate hardening, not release or user design acceptance.
