# Registered saved-water rule provider


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


The consumer now also checks the selected saved IFC distribution system against
the bound system GUID. Explicit DOMESTICCOLDWATER/DOMESTICHOTWATER labels reject
this HVAC-only provider before it writes a rule assessment. This catches a known
model/declaration conflict;other labels do not establish statutory applicability
or remove the required sourced facts. Existing IfcOpenShell and verified producer
binding are reused. A second independent native domestic ring passes hydraulic
checks but rejects HVAC rule application without payload;the chilled-water
positive control still passes. Domestic-water regulation support remains absent.

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

Automatic workflows may now add `"provider":"bsa.hvac-water-rules"` to the
existing `module_water_rules` task. Existing plans without that field retain
direct dispatch. The task still declares depends_on,basis,pack and sources;the
request is materialized from that exact passing producer. Results live under
the task's provider directory and the same rule verifier/delivery correspondence
checks cover both paths. Host disabled_module_providers can disable this rule
provider;pending/failed checks block requires_pass consumers. Host provider selection for rule tasks is now supported above. Do not dispatch rule payloads as numerical
module_analysis. A second jurisdiction and broader replacement remain unfinished.
Historical rule payloads lacking the required inherited coordinate frame reject;
create a fresh run instead of patching old evidence.

Actual fresh synthetic IFC/EPANET/official-source execution produces the same
assessment through legacy and registered calls. Disabled/unconfigured branches
retain no payload. These are integration evidence,not a real product design or
complete HK compliance.

The public builder's `--drawings` composition also executes with the registered
provider selected on its rules task. Actual model/water/rules/views/native stages
pass;two independently reopened DWGs and both1:30 plot references pass. Both
rendered pages were inspected. Disabling that provider blocks the dependent
views/native tasks before any DWG/merged PDF exists. This verifies same-model
rule-to-drawing gating,not equipment/fitting or installation completeness.
See evidence/registered-rule-native-drawings.json.
