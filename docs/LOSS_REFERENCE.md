# Signed coefficient reference review

loss_reference.rebase translates a signed coefficient using the same pressure
contribution and explicitly supplied positive source/target velocity pressures.
No circular diameter is inferred for a rectangular duct. This is arithmetic
binding around existing verified port quantities, not a new fitting correlation.
The upstream python-hvac convert_zeta pressure ratio and installed Fluids1.3.1
change_K_basis documentation/source were inspected first. The latter exposes a
diameter interface, so it is not called on invented rectangular diameters.

Primary background:
https://fluids.readthedocs.io/fluids.fittings.html#fluids.fittings.change_K_basis
https://github.com/TomLXXVI/python-hvac/blob/94247560a667905bfbf67e45a58965a58254fce8/hvac/fluid_flow/fittings/duct/smacna.py

```
python -m bsa.loss_reference run CANDIDATE_STUDY --out FRESH_AUDIT
python -m bsa.loss_reference verify AUDIT
```

Use explicit host BSA_PROJECT_ROOT. The audit replays the saved candidate study
and its complete native/source ancestry, then compares bounded candidates on
the actual small downstream port reference. It checks owned reference identity,
equal transition flow, native area/velocity correspondence, common implied
density convention, recorded reference velocity pressure and both saved signed
contributions. Source coefficients and candidate numbers remain unchanged.
No differing flows, negative/zero reference pressures or nonfinite values are
silently accepted. Negative coefficients preserve their signed contributions.

Current arithmetic checks use1e-12 relative tolerance and zero absolute floor;
zero agrees only with zero. These are numerical correspondence checks, not
engineering or method-selection thresholds. Even
identical normalized numbers would not establish source applicability. Unequal
normalized numbers do not identify which physical correlation is appropriate.
The original correlation, construction, stations/friction and interaction basis
remain review-required. No formal loss value or full fan duty is added.

Seven tests across reference translation, candidate interpolation and the
pressure ledger pass with verified durable receipt. Reference controls cover
negative signs, roundtrip pressure invariance, reference-only coefficient
changes versus actual pressure differences, wrong owners, differing flows,
density/velocity-pressure inconsistency and altered saved pressure values.
Source/native replay and saved output reconstruction are separate from tests.

Actual source/native generation and saved-audit reconstruction both pass for
all four bounded candidates. Their numerical differences persist after
normalization to the actual small downstream port: reference conversion alone
does not remove them. The original formal fitting record is not changed and no
physical method is selected. This does not prove a source error or permit
averaging/replacing values. Original correlation applicability and pressure
station/friction/interaction scope still require evidence.

## Small-value correspondence correction

The previous fixed1e-10 absolute tolerance was reproduced accepting differing
very small transition flows, velocities and pressure contributions. A separate
reproduction also returned zero after nonzero coefficient/pressure underflow.
The current guard validates finite scalar types, uses relative-only equality,
checks finite positive derived area/velocity/density quantities and rejects
nonzero underflow and nonfinite intermediate results. Genuine zero coefficients
remain supported. It rejects unrepresentable calculations rather than silently
returning zero. This does not extend physical correlation validity.

Nine candidate/reference/ledger tests pass with a verified durable receipt,
including unequal tiny flows and velocities, low-pressure disagreement, changed
stored contributions, underflow and genuine zero. Older receipts retain their
original method hashes; they are historical evidence, not current verification
after this method change. Fresh real-source audits are stored separately.

Fresh source/native generation and independent saved-audit reconstruction both
pass with the stricter guard. All four candidate differences remain; formal
loss values are unchanged. Previous audit directories and receipts are retained
without rewriting method hashes.
