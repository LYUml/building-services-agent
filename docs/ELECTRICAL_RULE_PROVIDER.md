# Registered whole-path electrical rule provider

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

This initial registered provider is CLI/API only. Automatic workflow tasks and
native electrical drawings still use the existing direct consumer. Registered
workflow dispatch and interchangeable jurisdiction implementations remain next
work;this does not establish complete electrical or multi-discipline design.
Historical results pinned to an older registry need fresh execution;do not
rewrite their original inventories.

See evidence/electrical-rule-provider.json for actual pinned official-source
execution and direct/registered equality. Synthetic tests cover disable,missing
cache,missing bytes,exceedance,identity/frame/source-role rejection and common
payload mutation. They are integration controls,not a finished installation.
