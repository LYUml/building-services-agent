# Plumbing demand basis under development

Keep supply loading units, drainage discharge units and simultaneous-use probabilities distinct. The course task requires sourced fixture data and an applicable method; the water-network solver does not supply these inputs automatically.

The retrieved private course lecture distinguishes identical-appliance binomial reasoning, mixed-appliance fixture-unit equivalence and a drainage square-root DU relation. These are different contracts. No project fixture inventory or authenticated table transcription has yet been supplied to a production demand adapter.

## Reuse choice and executed diagnostic

PPMtools was inspected as a stochastic household-use research candidate; see adapters/ppmtools/research.json. It is not adopted as the requested IOP conversion tool. For exact identical-appliance binomial calculations, reuse installed SciPy 1.18.1 `scipy.stats.binom` rather than implementing a probability engine. Official API reference: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binom.html . Existing SciPy/Boost license attribution remains applicable; no new upstream source is copied.

An actual lecture-example diagnostic with100 appliances, operating probability0.01 and allowed exceedance0.01 gives a minimum integer provision of4 appliances. SciPy survival probability is0.00343232; provision3 gives0.0183740. An independent sum of the binomial terms agrees within1e-12. The lecture's continuous approximation gives3.53 appliances; its resulting flow must not be called an exact integer-quantile guarantee. Preserve the stated classroom method when presenting its answer, and label the exact comparison separately.

This is method investigation, not a completed design-demand adapter, mixed-fixture selection, drainage-stack sizing or local-code acceptance. Next integration must require sourced probabilities/fixture rates, explicit exceedance choice and declared independence/identical-appliance scope. Never substitute textbook example probabilities for actual project data.

## Bounded identical-appliance API

Install the `demand` optional dependencies and call
`bsa.plumbing_demand.identical(count=..., operating_probability=...,
fixture_flow_L_s=..., exceedance_probability=..., basis=...)`. Every input is explicit.
The adapter uses SciPy isf/sf, verifies minimal integer provision and both tail
probabilities, and retains design_accepted=false. A possible zero provision is a
mathematical quantile result, not permission for zero-capacity installation; project
minimum-flow and method applicability need separate evidence. Four tests cover
independent summation/minimality, limiting provisions, monotonic service level and
invalid/missing data. No mixed-fixture or IOP table method is implied. Source-bound
CLI/workflow integration remains pending.

## Source-bound study command

`python -m bsa.plumbing_demand_study <project.json> --out <new-result.json>`
accepts exactly inputs, model_facts, basis and references. Each of the four input
quantities has value/unit/classification/source; units are1 except fixture_flow_L_s
which uses L/s. References map relative document paths to SHA256. Model facts are
identical_appliances and independent_use, each true/false/null. Unknown facts or
values retain pending without a calculation; false facts retain inapplicable.
Calculated cases retain source hashes, original classifications, numerical tail
checks and design_accepted=false. CLI exit2 preserves outstanding acceptance.

Actual source-pinned classroom example produces4 appliances; unknown independence
produces no flow and changed reference hashes reject. Four probability tests pass.
This command does not verify the truth of declared facts and is not yet registered
in the multi-task workflow or connected to a real home-survey design.

## Supplied discharge-unit relation

`bsa.plumbing_demand.discharge_units(rows, frequency_factor=..., basis=...)`
computes only K*sqrt(sumDU). Each connected fixture group supplies a unique id,
positive integer count, DU_per_fixture, source and classification. The factor and
connection/use basis are explicit; no fixture table, system type or floor multiplier
is inferred. Scope excludes continuous/pumped discharge additions, largest-outlet
minimum criteria, stack/vent capacity and jurisdiction acceptance. Those must be
resolved before using the wastewater relation as complete drainage design demand.

The actual private lecture example is reproduced: ten connected floors in an
eleven-storey block give78DU and4.41588L/s; ground-floor fixtures are explicitly
separate. Five probability/discharge tests pass, including aggregation, duplicate
identity, unknown factor and invalid-count controls. No hydraulic engine or new
dependency is introduced; this is thin sourced arithmetic using Python math.

## Source-bound DU study command

`python -m bsa.discharge_demand_study <project.json> --out <new-result.json>`
accepts fixtures, frequency_factor, model_facts, basis and references. The factor
has value/source/classification; fixtures use the DU API rows. Model facts are
connected_inventory_verified and frequency_classification_verified (true/false/null).
Unknown scope produces no wastewater calculation; rejected scope is inapplicable.
Reference files use relative path/SHA256 entries through the same helper as the
identical-appliance study. Output hashes sources and retains full acceptance false.

The source-pinned78DU classroom example, unknown-connection no-calculation branch
and changed-source rejection execute. Five numerical tests pass, and the original
identical-appliance source-bound example remains correct after helper reuse. These
standalone commands are not yet registered workflow tasks.

## Unified workflow tasks

`plumbing_demand` and `discharge_demand` now accept project plus ordinary id,
requires_pass and optional description. All reference files must stay within the
plan root and their hashes join workflow integrity. Calculated maps to scoped pass,
unknown to pending and rejected applicability to fail; downstream requires_pass
blocks both unresolved branches. Results are saved as demand.json. No diagram or
engineering requirement is accepted by the mathematical task.

An actual private method-only workflow runs both lecture examples and retains
manual engineering review; the full15-package coursework intake is unchanged. Six
focused tests cover probability/DU arithmetic, both executed task types, unknown
and rejected scope, downstream blocking and changed-source integrity failure.
