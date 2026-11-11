# Registered whole-path electrical rule provider


Host configuration can now select the existing registered electrical or water
rule provider on a direct rule task without editing its source plan:

```powershell
.venv/Scripts/python -m bsa.workflow execute runs/project/plan.json --out runs/project-run --module-provider rules=bsa.electrical-path-rules
```

For a saved-native HVAC water rule task,use `rules=bsa.hvac-water-rules`.
Only the compatible trusted provider is accepted for each rule-task domain;
manual/native tasks and cross-domain substitutions reject. Existing plan-level
provider fields still work,and an omitted host/plan provider retains direct
legacy dispatch. Host disable selection applies to the effective provider.
Delivery repeats effective-provider/source/disable correspondence. Diagnostics
use the retained selection rather than guessing from the plan field.
This is configuration independence,not a demonstrated second implementation
of either rule capability or a second jurisdiction. Those remain unfinished.
See [executed evidence](evidence/rule-host-selection.json).


Automatic workflows now support provider `bsa.electrical-path-rules` on the
existing `module_electrical_rules` task. Exact producer/topology/basis/pack/cache
correspondence and host disable selection are rechecked during execution and
at delivery. Native device schematics inherit the same verified rule result.
Use `--registered-rules --drawings` with the public source-only builder.
Actual native chain and four blocked controls execute;visual presentation
review remains separate. Diagnostics expose registered rule state. See
[evidence](evidence/electrical-rule-provider-workflow.json).


`bsa.electrical-path-rules` implements `regulation.electrical.radial-paths`
through the existing `module_electrical_rules` consumer and returns the common
`bsa.rule-assessment/1` payload. It reuses existing radial voltage-drop and
regulation engines;no new clause,coefficient or dependency is introduced.
Adapter licence metadata is NOASSERTION;upstream licences remain unchanged.

Requests use exactly four hashed repository-local source roles:producer,
topology,basis and pack. The producer is a verified passing electrical module.
Project/scenario/frame must match it. The host supplies the repository-local
official source cache using `--sources`;a document cannot supply executable
commands or a module import path.

```powershell
.venv/Scripts/python -m bsa.modules runs/project/rule-request.json --provider bsa.electrical-path-rules --sources runs/official-sources --out runs/project-rule-module
```

Use the same module request envelope as the electrical producer,change its
capability and replace sources with the four explicit paths/hashes above.
Verification repeats producer identity,full-path binding,official-source
availability and common-payload correspondence. The registered result must
match the existing direct consumer assessment exactly.

Missing cache configuration and host-disabled provider return unavailable
without a payload. Missing official bytes produce a completed execution with a
pending assessment. A numerical rule exceedance is completed execution with a
failed assessment;it is never engineering acceptance. Invalid producer identity
or source/frame mapping produces failure without a successful payload.

Plans without a provider retain direct dispatch. The registered workflow is
now available as described above. Interchangeable jurisdiction implementations
and complete electrical/multi-discipline design remain unfinished.
Historical results pinned to an older registry need fresh execution;do not
rewrite their original inventories.

See evidence/electrical-rule-provider.json for actual pinned official-source
execution and direct/registered equality. Synthetic tests cover disable,missing
cache,missing bytes,exceedance,identity/frame/source-role rejection and common
payload mutation. They are integration controls,not a finished installation.
