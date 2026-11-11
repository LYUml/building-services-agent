# Executed module contract and MOOSAS provider

The first executable modular slice exposes a common request/result boundary and
a separately registered MOOSAS provider. The core runner does not import MOOSAS
or implement its geometry/model engine. Existing scripts/moosas_space_exchange.py
still performs the original directly reused upstream XML/GEO calls in an
isolated subprocess. No new space-recognition or performance solver is added.

Install the contract validator with `pip install -e ".[modules]"` in the chosen
environment. It pins jsonschema4.26.0 (MIT). The selected MOOSAS exchange runtime
also needs the already documented IFC/geometry dependencies and isolated
rdflib7.1.4/pyparsing3.2.3. See REVIT_MOOSAS_DIRECTION.md for exact upstream
setup,compatibility workaround and attribution.

```powershell
.venv/Scripts/python -m bsa.modules runs/project/request.json --provider moosas.box-space-exchange --upstream tools/moosas-review --deps tools/moosas-exchange-deps --out runs/project/exchange
```

`--disable-provider` records unavailable without invoking the provider. Omitted
host runtime directories likewise return unavailable. Runtime locations come
from host arguments;the request cannot contain commands,import paths,engine
paths or provider implementation code. Only trusted code is registered. Unknown
provider IDs and unsupported request versions reject before output creation.

## Public contracts

The schemas are in contracts/modules and use JSON Schema Draft2020-12:

| Schema | Purpose |
|---|---|
| bsa.module-request/1 | Project/scenario/capability IDs,source-world SI frame,and relative source-role/path/SHA256 references |
| bsa.module-result/1 | Request/provider identity,independent execution and acceptance,source/method/schema hashes,artifact inventory and typed payload |
| bsa.spatial-boxes/1 | Neutral box-space IDs,metre origins/dimensions,derived floor areas and geometric contacts |

For capability spatial.ifc-boxes.exchange,the request source roles are exactly
ifc and binding. Sources resolve relative to the request within this repository.
Each has path and sha256. Coordinate_frame contains id,kind=source-world-si,
length_unit=m and georeferenced=false. This identifies a local source-world
frame;it does not establish geographic north or a surveyed placement.

The provider returns metre/m2 geometry-derived boxes with original IFC GUIDs.
Contacts preserve source surface IDs:box suffixes0/1 are bottom/top,2/3/4/5 are
negativeY/positiveX/positiveY/negativeX. Raw upstream evidence retains actual
per-space face vertices and ownership checks. Contacts mean whole-face
coordinate contact,not a thermal partition or airflow opening.

Execution is completed,failed,unavailable or pending. Engineering acceptance is
separate and remains pending for this spatial-only provider;design_accepted and
simulation_ready remain false. Failed/unexecuted results cannot expose a success
payload or pass acceptance. Invalid provider payloads become structured failed
results. Source changes prevent the result record from being published.

JSON readers reject duplicate keys and nonfinite numbers. The validator rejects
unknown fields/versions,wrong units,duplicate IDs and inconsistent box areas.
`bsa.modules.verify_result(path)` checks schemas,current source/method hashes,
request correspondence,declared source coverage,provider identity,frame and the
complete output artifact inventory. These are consistency checks,not signed
execution authentication or semantic engineering certification.

## Provider boundary and current limits

The trusted registry is bsa.providers.get_provider. An implementation declares
DESCRIPTION,CAPABILITY,PAYLOAD,validate_request and execute. The runner handles
request/provenance/result checks;the adapter owns domain execution and legacy
format translation. MOOSAS is pinned to
dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c with Apache-2.0 attribution.
Actual execution requires a clean checkout and checks it again after exchange.
Used upstream Python/JSON and wrapper sources enter the evidence inventory.

The MOOSAS adapter uses the existing source-validated IFC box extractor,then
upstream MoosasModel/MoosasSpace/surface and XML/GEO save/reload. It does not
promote the previously failed ordinary MOOSAS IFC loader to supported status.
The empty version5 geometry-only catalogue workaround still applies;no
construction/HK template,thermal/airflow solve or native MEP authoring occurs.

These providers are repository-local and box-space only. Result provenance
uses local file paths;portable artifact resolution,
workflow DAG integration,dependent disable propagation and other
analysis/authoring/rule contracts remain to be implemented and verified. A mock
dispatch test is not evidence of successful engine substitution.

## Executed evidence

Ten targeted module/contact tests pass,including closed request versions/fields,
disable/missing runtime,wrong frame/units/area,nonfinite/duplicate JSON,source
mutation,incomplete inventories and stale artifacts. Mocked provider tests only
test boundary behaviour.

Actual pinned MOOSAS calls pass for a3-space native fixture and a2-space saved
public-course concept model,retaining2 and1 geometric contacts respectively.
The same interface returns unavailable when disabled. A real MEP-only IFC with
no architectural spaces returns failed and no payload. This demonstrates bounded
cross-project data reuse,not completed real designs,arbitrary IFC conversion,
thermal readiness or module substitution. See
[executed evidence](evidence/module-moosas-exchange.json).

## Executed provider substitution

`--provider ifcopenshell.box-spaces` selects the existing native IfcOpenShell0.8.5
box extractor behind the same request/result/payload contracts. It does not need
MOOSAS checkout or dependencies. The native library is LGPL-3.0-or-later;no engine
source was copied. A fixed isolated worker reuses thermal_binding.extract and
the existing whole-face contact helper. There is no new geometry engine.

Actual calls of both providers on the same two requests produce exactly equal
neutral payloads (3 spaces/2 contacts and2 spaces/1 contact). Both reject the
MEP-only0-space source and both return unavailable when disabled. All eight
results pass source/method/artifact verification. Eleven targeted tests pass.
See [substitution evidence](evidence/module-substitution.json).

This verifies switching the selected spatial provider at this boundary. It is
not independent geometric validation:both paths share the same source extractor
and contact logic. Only the MOOSAS path saves/reloads XML/GEO. Equal payloads do
not establish equivalent simulation,thermal boundaries or native MEP authoring.
DAG dependency propagation and broader module replacement remain unverified.

## Existing workflow integration

The existing source-linked workflow accepts this bounded task:

```json
{"id":"spaces","kind":"module_exchange","request":"request.json","provider":"moosas.box-space-exchange"}
```

The request path is relative to the plan;its source hashes and common contracts
validate before output creation. Tasks may use the existing `requires_pass`
array with earlier task IDs. No engine paths or commands may enter the task.
Use host CLI options to select runtime/replacement/availability:

```powershell
.venv/Scripts/python -m bsa.workflow execute runs/project/plan.json --out runs/project/run --moosas-upstream tools/moosas-review --moosas-deps tools/moosas-exchange-deps
.venv/Scripts/python -m bsa.workflow execute runs/project/plan.json --out runs/project/native-run --module-provider spaces=ifcopenshell.box-spaces
.venv/Scripts/python -m bsa.workflow execute runs/project/plan.json --out runs/project/disabled-run --disable-module-provider moosas.box-space-exchange
```

Module completed/failed/unavailable/pending map to workflow pass/fail/pending/
pending respectively,for execution only. The original module result remains
unchanged with separate pending acceptance. Every requirement remains pending
review. Provider selection is explicit;there is no silent fallback. Override
IDs must name existing module tasks and trusted compatible providers.

Before each following task and workflow completion,the runner verifies produced
module source/method/artifact inventories. Workflow verification also checks
nested module results and their current source evidence. Native/upstream pins
are preserved in runtime_inputs. A blocked dependent has no output directory;
independent valid branches continue. This reuses existing workflow gating.

Five actual native/MOOSAS workflows exercise normal,replacement,disabled,missing
runtime and0-space failure. Normal/replacement execute all3 tasks;the latter3
leave the dependent unexecuted while independent native exchange passes. Exact
replacement payloads and all workflow inventories verify. A CLI disabled run
also executes and verifies;21 targeted tests pass. See
[workflow evidence](evidence/module-workflow.json).

These are scheduling controls,not a new analysis consumer:the gated task still
uses its declared request. Direct consumer inheritance of upstream neutral
payloads,automatic design/iteration and complete multi-discipline modularization
remain unfinished. Earlier substitution evidence above predates this workflow
milestone;its statement about unverified DAG propagation is historical.

## Thermal input inheritance

An existing module producer can feed the annual thermal input adapter:

```json
[
  {"id":"spaces","kind":"module_exchange","request":"request.json","provider":"moosas.box-space-exchange"},
  {"id":"thermal","kind":"module_thermal_project","depends_on":"spaces","project":"template.json","binding":"mapping.json"},
  {"id":"annual","kind":"annual_energy","depends_on":"thermal","weather":"weather.epw.gz"}
]
```

This reuses thermal_binding.validate_contract,thermal_geometry boxes/adjacency
and annual_energy.validate/run. The template omits spaces,dimensions and north
angle. Mapping contains exactly source,spaces (guid,id,source) and explicit
north_axis_deg,as in examples/thermal-ifc/binding.json. Every neutral GUID must
map exactly once. No equipment properties are imported by this bridge. Source
dimensions/origins are inherited from the verified producer,not template data.
Contacts recompute and must match the producer. Explicit orientation remains a
separate sourced input;source-world SI is not surveyed north/georeferencing.

Preparation writes bound-project.json and inheritance.json with source/method
pins. Source producer evidence is verified before/after preparation and before
following tasks. Verification reconstructs the expected bound project. Workflow
pass here means input preparation only;simulation_executed and design_accepted
remain false. Actual thermal applicability is still subject to the documented
legacy box/whole-face/material/system assumptions (THERMAL_BINDING.md).

Inherited annual_energy forbids a replacement project and requires an earlier
module_thermal_project. It uses that exact bound-project.json and declared EPW;
no executable means pending with no synthetic simulation output. With an engine
supplied it routes to the existing annual adapter. That inherited native-engine
branch has not executed on the currently restricted host. Existing native
startup restrictions remain in force;this milestone does not claim simulation.

Five actual workflows compare MOOSAS/native preparation and disabled/missing/
failed source controls. The two successful preparations yield exactly equal
3-space bound projects. All five verify;blocked preparations/simulations remain
unexecuted and an independent native branch passes. Twenty-five targeted tests
pass. The synthetic template and Chicago weather are test data,not Hong Kong
project facts or regulation. See [evidence](evidence/module-thermal.json).

The previous statement that direct payload inheritance was unimplemented is
historical:it now exists for this bounded annual-input bridge. Arbitrary geometry,
other performance/authoring consumers,actual simulation and full design remain
unfinished.

## Provider selection in diagnosis and delivery

Workflow reports retain module_selection with schema
bsa.workflow-module-selection/1,explicit task/provider overrides and disabled
provider IDs. These are host choices,not executable document content. Delivery
context reconstructs selected provider method inputs and verifies actual result
provider/disable states. Unsupported selection fields reject. This fixes a
reproduced single-task override whose valid native output previously failed
delivery input-set comparison. Older runs retain original evidence;rerun
overridden plans for selection-bound review.

workflow_status includes verified module_state (provider,execution diagnostics,
acceptance and result hash) in task and recovery-action records. Disabled and
missing-runtime conditions receive distinct host-configuration actions;failed
exchange keeps retained logs without inferring a physical cause. Recovery lists
preserve all affected tasks and requirements. Diagnosis does not enable modules,
launch engines,apply fallback or alter security policy.

Eight actual runs cover single-task MOOSAS/native switching,disabled/missing
runtime and thermal inheritance with disabled/missing/failed inputs. All pass
source/diagnosis/delivery-context checks;every initialized review remains pending
and design_accepted=false. Forty-four targeted tests pass,including selection
tampering and existing workflow/status/delivery tests. See
[evidence](evidence/module-selection-review.json). This is review integration,
not complete multi-discipline design or simulation.

## Newly authored IFC inheritance and public pipeline

module_exchange may declare depends_on on an earlier supported saved-IFC
producer from the existing workflow IFC_ARTIFACTS registry. Its request is then
a binding-only module-request/1 template. An explicit IFC source is forbidden;
the workflow supplies the actual producer artifact path and SHA256 after that
producer passes. Failed/pending authoring blocks materialization and exchange.
Native producer files are pinned immediately before later tasks execute.

The task writes request.json in its folder and executes the provider into
exchange/. Source selection/review reconstructs the request against the original
template and exact saved producer. Thermal inheritance resolves either direct
or inherited module result layout. No additional geometry engine is introduced.

[The public example](../examples/modular/README.md) runs the checked-in
examples/modular-plan.json without previous private/generated files. Four actual
native/MOOSAS/disabled/missing-runtime runs cover native authoring through neutral
space exchange and annual input preparation. Normal routes preserve3spaces and
produce equal thermal inputs. All diagnoses/review contexts verify;47 targeted
tests pass,including native public execution and blocked authoring. Annual
simulation and every engineering acceptance review remain pending. See
[evidence](evidence/public-modular-pipeline.json). The example retains explicit
synthetic geometry,Chicago weather and declared orientation assumptions;it is
not raw-brief automatic engineering or a completed coursework design.

## Separate jurisdiction checks using neutral space IDs

spatial_lighting_rules is a thin consumer of a completed module_exchange
result. It reuses regulations.evaluate and lighting_rules.office_check with an
explicit selected pack;it contains no new legal limits or geometry engine.
Only office_lighting_power_density methods are supported at this boundary.
Jurisdiction and rule-pack ID must match each supplied space basis.

```json
{"id":"lpd","kind":"spatial_lighting_rules","depends_on":"spaces","basis":"lighting-basis.json","pack":"lighting-pack.json","sources":"official"}
```

Every neutral GUID must have an explicit basis. Each basis uses the existing
jurisdiction/rule_pack/edition_decisions/facts fields and lighting_space containing
only luminaires;repeating an area is rejected. Luminaire IDs must be unique
across spaces. Full-output circuit W remain sourced inventory inputs. The saved
geometry-derived m2 supplies the numerical denominator. A separate sourced fact
must establish whether this geometry represents statutory internal floor area;
box geometry alone cannot establish that. No thermal kW,lighting W/m2 target,
demand or dimming factor supplies actual fixture watts.

Rule output retains official hashes,source snapshots,per-space calculated values,
applicability/edition reasons and regulatory_compliance=not_established. Missing
facts/sources stay pending;exceeded selected LPD criterion is fail without ruling
out separately reviewed alternative compliance routes. Replay verifies original
producer evidence,derived areas and rule results before following workflow tasks.
Use requires_pass on intended downstream tasks explicitly. A passing LPD result
does not establish branch,photometry,controls,product or whole-project acceptance.

For the public synthetic model,lighting-basis.json is provided under
examples/modular. After obtaining the unchanged pinned official source:

```powershell
.venv/Scripts/python scripts/fetch_regulation_sources.py regulations/hk/lighting-2026.11.08/pack.json --out runs/hk-lpd-sources
.venv/Scripts/python -m bsa.spatial_lighting_rules runs/public-modular/spaces/exchange/result.json --basis examples/modular/lighting-basis.json --pack regulations/hk/lighting-2026.11.08/pack.json --sources runs/hk-lpd-sources --out runs/public-modular-lpd
```

Six actual workflows cover native/MOOSAS equal rule results,exceeded watts,
unknown internal-area applicability,missing official source and disabled spatial
producer. Independent thermal preparation remains separate;required downstream
review stays blocked when LPD has not passed. All diagnosis/review contexts
verify and69 targeted tests pass. Inputs/facts are synthetic;the existing pinned
BEC2024 edition decision is not a real statutory applicability determination.
See [evidence](evidence/spatial-lighting-rules.json) and HK_LIGHTING_RULES.md.

## Native IFC authoring provider

The common bsa.model-artifact/1 payload identifies an IFC4 model and its native
verification report using relative artifact paths/SHA256,source-world SI frame,
geometry scope and passed scoped checks. Both references must match the complete
module artifact inventory. It is initially IFC4-only;no DWG/RVT support or
general native-application equivalence is claimed.

ifcopenshell.bim-authoring accepts capability authoring.ifc.bim with exactly one
project source. It executes the existing bsa.bim CLI in an isolated fixed
subprocess,requires installed IfcOpenShell0.8.5 and verifies saved-reopen report,
source/model hashes and all native scoped checks. No authoring engine is copied
or rebuilt. IfcOpenShell remains LGPL-3.0-or-later;the descriptor identifies that
upstream engine,not a new licence grant for unrelated repository code.

```json
{"id":"model","kind":"module_authoring","request":"modular/authoring.json","provider":"ifcopenshell.bim-authoring"}
```

module_authoring uses the same host-selection/disable/verification boundaries.
It has no depends_on geometry replacement path. A later module_exchange may
depend on it and resolves the actual IFC from the verified model-artifact
payload instead of a provider-specific filename. Coordinate frames must match;
failed/unavailable authoring blocks request materialization and later consumers.
Acceptance remains separate from authoring checks. Only this one native authoring
provider is verified;successful authoring-provider substitution remains pending.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/modular-authoring-plan.json --out runs/modular-authoring
```

This second public plan retains the original public example and reuses its exact
synthetic source brief,BIM,thermal mapping and weather. Native authoring/spatial/
thermal preparation pass;annual simulation and engineering review remain pending.
Six actual native/MOOSAS/disabled/invalid-source/frame-mismatch/HK-LPD workflows
pass source/diagnosis/delivery checks with pending reviews. Seventy-three targeted
tests pass,including a real native authoring chain and artifact-contract controls.
See [evidence](evidence/module-ifc-authoring.json). No visual/native DWG/RVT,
full installation or complete engineering design acceptance is established.
