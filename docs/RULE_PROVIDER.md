# Registered saved-water rule provider

`bsa.hvac-water-rules` implements `regulation.water.saved-native` through the
existing `module_water_rules` consumer and pinned existing rule pack. It returns
`bsa.rule-assessment/1` using the same common module runner as analysis/authoring.
No new calculation engine,regulation clause or third-party dependency is added.
The adapter's own licence metadata is NOASSERTION;this does not relicense
upstream libraries or official documents.

The request has exactly producer,basis and pack source roles,each with a relative
repository-local path and hash. Producer references an existing verified passing
saved-native water module result. Request project/scenario IDs must match it;
the coordinate frame must equal the producer's. Entity/producer/source identities
and exact assessment contents are reconstructed during verification. The payload
retains per-entity pending coverage and full conformity stays not_established.

```powershell
.venv/Scripts/python -m bsa.modules runs/project/rule-request.json --provider bsa.hvac-water-rules --sources runs/official-sources --out runs/project-rule-module
```

The official-source cache is an explicit host path,not a document-selected
command. It must be repository-local. Missing host configuration returns
unavailable;missing official files retain the underlying pending assessment.
`--disable-provider` returns unavailable with no payload. Invalid upstream/frame
or rule evidence fails without a successful payload. A completed check can have
a failed or pending engineering status;module execution completion is separate
from its payload status and acceptance always remains pending.

This is a standalone CLI/API registered provider. Automatic workflows still use
the existing `module_water_rules` task and its same-producer gates. Do not dispatch
this rule payload as module_analysis or infer automatic workflow replacement.
A second jurisdiction provider and broader discipline replacement are unfinished.
Historical rule payloads lacking the required inherited coordinate frame reject;
create a fresh run instead of patching old evidence.

Actual fresh synthetic IFC/EPANET/official-source execution produces the same
assessment through legacy and registered calls. Disabled/unconfigured branches
retain no payload. These are integration evidence,not a real product design or
complete HK compliance.
