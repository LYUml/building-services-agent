# Whole-agent regression - 2026-11-14

The completed run selects all 385 current test modules in 20 sequential batches.
All terminal receipts independently verify against the current selected source
and interpreter. The 1,617 executed instances comprise 1,477 passes, 126 skips,
one failure and 13 errors. Imported repeated test instances are included; these
are not 1,617 distinct capabilities or a percentage of engineering completion.
The full suite completed and is not green.

[Complete aggregate evidence](evidence/agent-regression-complete.json) retains
per-batch receipt hashes, counts, exact failed test names and grouped skip reasons.
Raw logs/runtime records remain local and excluded from public snapshots.
Earlier checkpoints remain historical rather than overwritten.

## Actual failures

All 13 errors have the same observed import failure: OpenStudio
`_openstudioutilitiesunits` is blocked by host Application Control. Four occur in
native HVAC rule setup (batch7), four in sizing humidity (batch15), and five in
saved thermal geometry/material/window checks (batch18). No native model/result
acceptance follows for those cases. No host security policy was changed.

The remaining failure is
`HVACWorkflowTests.test_actual_variants_and_postrun_native_tampering`: its HK task
was expected to pass but stays pending because the upstream energy producer did
not pass. Pending downstream work is preserved; the assertion was not weakened.
These failures were not converted to skips or attributed to an unobserved solver
result. Native energy acceptance needs execution on an approved environment.

## Skips and supplemental actual runs

The original 126 skips remain in their original receipts. Their reasons include
explicit EnergyPlus/Radiance availability, official source cache, MOOSAS,
AutoCAD, isolated numerical runtimes and document/OCR fixture opt-ins. A skip is
not a pass; an installed runtime alone does not satisfy these integrations.

Separately completed source-frozen opt-in runs provide narrower actual evidence:

- Five actual AutoCAD integration cases cover source export/base overlay,
  riser/true-arc route and three-view save/reopen/plot references. Synthetic
  fixtures retain pending visual review; no completed project is claimed.
  See [initial native checks](evidence/agent-regression-checkpoint.json),
  [riser/route checks](evidence/native-riser-route-regression.json) and
  [three-view check](evidence/native-multiview-regression.json).
- Nine Hong Kong cable controls execute against the unchanged pinned official
  PDF cache. See [source-bound evidence](evidence/hk-cable-regression-source-check.json).
- Twenty-four MOOSAS geometry/source/rule cases execute using the existing pinned
  Apache-2.0 upstream and isolated dependencies. Their original tests cover IFC
  source correspondence, recognition, source/rule workflows and explicit grid
  controls. This does not run MOOSAS airflow or thermal simulation. See
  [MOOSAS evidence](evidence/moosas-geometry-regression.json).

Supplemental counts are not added to the primary1,617instances or used to rewrite
its skipped outcomes. Test requirements and numerical tolerances stay unchanged.

## Remaining whole-agent work

This closes the interrupted/full-regression verification task. It does not close
general document interpretation, complete multi-discipline physical design,
Hong Kong applicability/coverage, native Revit authoring, performance simulation
or full engineering and visual delivery acceptance. Continue the full capability
and gap matrix in [whole-agent status](AGENT_STATUS.md). Additional isolated
numerical-runtime opt-ins should be checked against their existing pinned hosts
before claiming electrical/three-phase integration coverage.
