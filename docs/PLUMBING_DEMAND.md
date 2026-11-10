# Plumbing demand basis under development

Keep supply loading units, drainage discharge units and simultaneous-use probabilities distinct. The course task requires sourced fixture data and an applicable method; the water-network solver does not supply these inputs automatically.

The retrieved private course lecture distinguishes identical-appliance binomial reasoning, mixed-appliance fixture-unit equivalence and a drainage square-root DU relation. These are different contracts. No project fixture inventory or authenticated table transcription has yet been supplied to a production demand adapter.

## Reuse choice and executed diagnostic

PPMtools was inspected as a stochastic household-use research candidate; see adapters/ppmtools/research.json. It is not adopted as the requested IOP conversion tool. For exact identical-appliance binomial calculations, reuse installed SciPy 1.18.1 `scipy.stats.binom` rather than implementing a probability engine. Official API reference: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binom.html . Existing SciPy/Boost license attribution remains applicable; no new upstream source is copied.

An actual lecture-example diagnostic with100 appliances, operating probability0.01 and allowed exceedance0.01 gives a minimum integer provision of4 appliances. SciPy survival probability is0.00343232; provision3 gives0.0183740. An independent sum of the binomial terms agrees within1e-12. The lecture's continuous approximation gives3.53 appliances; its resulting flow must not be called an exact integer-quantile guarantee. Preserve the stated classroom method when presenting its answer, and label the exact comparison separately.

This is method investigation, not a completed design-demand adapter, mixed-fixture selection, drainage-stack sizing or local-code acceptance. Next integration must require sourced probabilities/fixture rates, explicit exceedance choice and declared independence/identical-appliance scope. Never substitute textbook example probabilities for actual project data.
