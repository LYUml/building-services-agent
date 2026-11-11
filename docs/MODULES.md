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

## Drawing from a common model artifact

The existing ifc_views task may now depend directly on module_authoring. It
resolves and verifies the IFC4 model-artifact payload rather than assuming the
provider's output filename. Other unsupported IFC consumers do not automatically
gain this ability. The existing circular hollow-profile/port/complete-label
requirements still apply;equipment and fittings are reported as excluded.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/modular-drawing-plan.json --out runs/modular-drawings --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe'
```

This public synthetic ring reuses water-loop-ifc/model.json and its exact sourced
view settings. It executes common-module authoring → plan/front/side DXF views →
existing guarded isolated AutoCAD save/reopen/plot → pending engineering review.
It does not execute the separate water hydraulic adapter or imply hydraulic
acceptance. No GUI documents are attached to,closed or written. AutoCAD binary
bytes are pinned for this native workflow.

Actual execution saves/reopens3DWGs with complete entity/geometry/GUID matching.
All three5m references measure99.991333mm against100mm within the declared0.2mm
tolerance. The merged3-page PDF matches verified source page streams and all
three150dpi renders were inspected:labels,titles,symbols and leaders are readable
without visible clipping. Raw source PDFs retain duplicate PageMode dictionary
warnings from pypdf;merged content,scale and rendering checks pass. Centreline
projection overlap,hidden lines,finite fittings,equipment,insulation and
installation sheets remain outside the accepted scope. Source-bound audit and
every engineering review remain pending.

Missing native runtime and disabled-author controls preserve blocked work;
incomplete-label and disabled native-dispatch regression controls are tested.
Eighty-two targeted invocations complete:81pass,1optional native test skipped;
the native end-to-end workflow above executes separately. See
[evidence](evidence/modular-native-drawings.json). This is scoped native drawing
integration,not full multi-discipline design or general DWG/RVT authoring.

## Typed rectangular air-budget analysis

fluids.rectangular-air-budget reuses the existing rectangular_network CLI and
network pressure-budget code with fluids1.3.1 (Caleb Bell,MIT). No solver,
friction correlation or domain limit is rewritten. It requires capability
analysis.air.rectangular-tree and exactly one source-pinned project. There is
one verified analysis implementation at this boundary;replacement by another
solver is not verified.

```powershell
.venv/Scripts/python -m pip install -e ".[modules,network]"
.venv/Scripts/python -m bsa.workflow execute examples/modular-analysis-plan.json --out runs/modular-air-budget
```

module_analysis uses the same trusted registry,host provider selection/disable,
source/hash and artifact checks. This initial analysis consumes a declared
project;native-geometry inheritance is not implemented and depends_on is rejected.
The public example reuses the existing explicit synthetic rectangular air tree.
No AutoCAD,Revit,EnergyPlus or prior generated file is required for that example.
It remains a prescribed level constant-density,fully-developed turbulent
hydraulic-diameter approximation;it is not a flow-balancing or fan operating-
point solution. Lengths,K and applicability remain declared source inputs.

bsa.air-budget/1 preserves explicit m3/s,Pa and m/s units,numerical pass/fail,
velocity/pressure/continuity checks,supply flow,required source total pressure and
a hash-linked full report. The raw report/CSV/HTML retain all branch/node results
and unresolved scope. geometry_bound=false and design_accepted=false remain
explicit;no thermal/electrical power or jurisdiction pass is inferred.

Execution completed and numerical pass are separate. The existing engine's
exit2 with valid failed-check artifacts becomes execution completed with numerical
fail;invalid input without a calculation report is execution failed. Workflow
status uses numerical fail to block requires_pass consumers. Unavailable/disabled
modules remain pending. Verification checks the common numerical summary against
retained engine evidence;delivery context rejects a workflow pass contradicting
that result. Diagnosis distinguishes failed declared checks from failed execution
and retains original targets and engineering acceptance gaps.

Five actual baseline/pressure-fail/velocity-fail/invalid/disabled scenarios retain
independent native IFC work while blocking the required review as appropriate.
All source/diagnosis/review contexts verify with every review pending.101 targeted
test invocations complete:100pass,1optional native test skipped. The new budget
tests execute the real existing calculator,including rejected summary/status
forgery and wrong units. See [evidence](evidence/modular-air-budget.json). This
does not establish physical routes,component K,leakage,acoustics,fan/product
selection,full code applicability or complete multi-discipline design.

## Saved-native rectangular air-budget binding

fluids.rectangular-ifc-budget adds capability analysis.air.rectangular-ifc-tree.
It reuses network_binding._prepare,rectangular_binding.inspect_saved and the
existing rectangular_network calculation. Values derive from canonical authoring
input and independently reconcile against saved native solids,wall profiles,
ports,connections and complete duct coverage. This is not an arbitrary IFC
importer or automatic interpretation of an unexplained external revision.

```powershell
.venv/Scripts/python -m pip install -e ".[modules,bim,network]"
.venv/Scripts/python -m bsa.workflow execute examples/modular-bound-analysis-plan.json --out runs/modular-bound-air
```

The public plan authors the existing straight-wall example through module_authoring.
A module_analysis depending on it uses an inherited request containing exactly
project and binding sources. The template omits bound length,width,height and
node elevation. The workflow supplies ifc from the verified model artifact and
model from its canonical project source,requires matching frames and pins all
four final sources. Replacement model/IFC fields in inherited templates reject.
Standalone requests may supply all four project/model/binding/ifc sources.

bsa.bound-air-budget/1 requires geometry_bound=true and hash-linked copied IFC4/
binding-report artifacts. Declared-only air-budget/1 remains geometry_bound=false.
Original engine reports are unchanged:their geometry_bound=false describes the
standalone calculator;the wrapper's true flag records the additional native
reconciliation. Verification reconstructs the network and repeats native
inspection. Analysis does not edit or reauthor source models. Numerical failure
still blocks required consumers;engineering acceptance remains separate.

The retained calculation must hash-match the actual derived input,and binding/
numerical reports must agree on calculated-check status. Altering either record
cannot promote a contradictory result through verification.

Six actual straight/bend/pressure/duplicate/disabled-author/disabled-analysis
workflows verify source,diagnosis and review contexts,with all reviews pending.
Two direct controls reject source-metadata mismatch and a changed real hollow
profile with original metadata preserved.105 targeted invocations:104pass,
1optional native test skipped;added profile controls pass. Existing engines are
fluids1.3.1 (MIT) and IfcOpenShell0.8.5 (LGPL-3.0-or-later). See
[evidence](evidence/modular-bound-air-budget.json).

Native agreement is not surveyed as-built truth or installation approval.
Flow,roughness,K,method applicability,junction physics,fan operating point,
products,acoustics and code conformity remain independently sourced/reviewed.
This does not establish a complete HVAC design.

## Existing fan intersection from a common bound budget

rectangular_fan_operating_point can depend on a passing module_analysis with
analysis.air.rectangular-ifc-tree. It reuses rectangular_fan_binding.run and the
existing fixed-speed single-path solver;no new fan or friction engine is added.
The consumer takes only the parent ID and explicit source curve. Repeating
project,model,flow or pressure inputs is forbidden.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/modular-fan-plan.json --out runs/modular-fan
```

This public synthetic plan runs native authoring → bound budget → existing fan
intersection → pending review. The total-pressure curve and free-flow,fixed
terminal boundary are explicit. This is not a multi-terminal balancing solver.
Original design demand remains separate from operating flow;no upstream model
or original network is overwritten. Air power remains air_power_kw;electrical
motor input and real product selection remain unresolved.

The bound payload gains an optional hash-linked network_input reference,which
the current provider emits. Earlier payloads remain structurally readable but
cannot feed this consumer without that reference;no provider filename is guessed.
Common reference validation checks path/hash inventory correspondence. Parent
result and curve identities enter fan.json with source/method hashes.

Verification replays the same existing solver from original inherited inputs,
checks the point,trace,targets,bracket,pass/fail and saved operating-network rerun.
This is source/result consistency,not an independent solver or authenticated
execution proof. Delivery rejects false fan-pass records. A converged point
below design demand remains fail;no sign bracket gives no fabricated/extrapolated
point. Density mismatch rejects without an inferred correction. Failed/disabled
upstream work leaves fan output absent and required review blocked.

Seven actual straight/bend/capacity/no-bracket/density/upstream-failure/disabled
workflows verify source,diagnosis and delivery context with all reviews pending.
134 targeted invocations complete:133pass,1optional native test skipped.
Tests include point/trace tampering and false workflow-pass rejection. See
[evidence](evidence/modular-fan-handoff.json). Real curves/installation category,
stable operation,mechanical limits,native fan equipment,electrical input,HK rules
and full design acceptance remain unfinished.

## Steady water analysis provider

`wntr.epanet-steady` implements `analysis.water.steady-graph` using the existing
fixed `python -m bsa.epanet` CLI and WNTR1.5.0/EPANET2.2. See
examples/modular-water-plan.json and the commands in examples/modular/README.md.
Its request has exactly one source role,project. It accepts the existing declared
withdrawal and circulation graph formats;it does not inherit a model artifact
or import arbitrary IFC geometry. Windows-x64 library selection is verified on
this host;other deployment profiles/provider replacements remain unverified.

The `bsa.water-graph/1` payload retains junction head/static pressure head and
delivered/design demand,pipe signed flow and speed,pump flow/head gain,12 explicit
numerical checks plus circulation checks where applicable,and raw/report refs.
Units are m3/s,m and m/s;head denotes metres of water,not Pa or source total
pressure. No pump motor power is inferred. Geometry remains unbound and all
engineering acceptance stays pending.

Verification checks method/source/library pins,domain artifacts,worker source
copy,process status,common/raw report agreement and source/raw numerical replay
using the existing evaluator. This is consistency checking,not another solver,
authenticated execution or manufacturer/source applicability verification.
INP/RPT/BIN,CSV outputs and worker logs remain available. A successful solve with
failed targets is completed/numerical fail and blocks required downstream work.
A disabled/missing/incompatible runtime is unavailable;worker/timeout/policy
failure cannot expose a hydraulic payload. Policy classification requires the
actual retained log message and does not trigger policy changes.

Six actual baseline/capacity/velocity/disabled/invalid/circulation workflows
verify result,workflow,diagnosis and delivery context. The final numerical results
are respectively pass/fail/fail/absent/absent/pass;all reviews remain pending.
42 related modular tests,11 existing water tests and7 diagnosis tests pass.
These60 targeted invocations do not replace the last full regression at b74f030.
See evidence/modular-water-graph.json. Native BIM/routing handoff,HK rule binding
through this interface,products,efficiency/electrical input,controls,NPSH and full
water/MEP design remain unfinished.

## Saved-native water graph

`wntr.ifc-steady` implements `analysis.water.ifc-steady-graph` and emits
`bsa.bound-water-graph/1`. It directly wraps the existing water_binding.run,
derive/reconcile,ifc_drawing extractor and EPANET worker,with WNTR1.5.0 and
IfcOpenShell0.8.5 pins. No geometry or hydraulic engine is replaced.

An explicit request has project/ifc/binding sources. module_analysis may instead
depend on module_authoring with a project/binding-only template. The workflow
binds the exact verified IFC4 artifact and matching frame;no model filename,
dimensions or elevations are guessed. Repeated bound dimensions reject. The
source mapping must cover every element/port/connection in the selected system;
other systems remain outside the selected scope. Real saved hollow profiles,
world placements,owned bidirectional ports and coincident native connections
are checked by the existing adapter. Explicit zero-loss hydraulic nodes remain
an engineering idealization,not physical fitting acceptance.

Payload quantities preserve the declared water contract's static-head/signed-flow
units and numerical checks,and add explicit IFC4 model,binding and derived-input
artifact refs. The copied model must be byte-identical to its source. Verification
rederives/reconciles geometry and replays the same numerical evaluator against
the retained raw results. This proves scoped consistency,not independent solver
verification,authenticated execution or as-built truth. geometry_bound=true does
not clear products,K,physical junctions,clashes or complete engineering acceptance.

Use examples/modular-bound-water-plan.json. Six actual baseline/velocity/water-
disabled/author-disabled/repeated-dimension/circulation workflows verify result,
workflow,diagnosis and delivery contexts. Two independent public native projects
pass;the others preserve numerical failure,unavailability or input failure as
appropriate. All manual reviews remain pending. 46 modular and7 existing water-
binding invocations pass;see evidence/modular-bound-water.json. Native fitting
variants beyond these saved straight-pipe projects,other provider replacement,
HK consumer handoff,product/visual/installation drawings and full acceptance
remain unfinished. The earlier full regression is not replaced by these53
targeted invocations.

## Saved-water jurisdiction consumer: standalone boundary

`python -m bsa.module_water_rules <bound-water-result.json> --basis <basis.json>
--pack <pack.json> --sources <official-cache> --out <new-repository-folder>`
consumes a passing verified bsa.bound-water-graph/1 result. It resolves explicit
network-input/report artifact refs and uses the existing
epanet_pipe_regulations.prepare and regulations.evaluate routines. The pure
quantity-to-rule binding was extracted from the legacy adapter without changing
its equations,source checks or fresh-solve entry point. The consumer does not
rerun hydraulics or author a second model.

Only the existing hvac_water_piping method is supported. Current actual trials
select the pinned HK BEC2024 pack and its hash-matching EMSD PDF. These are
air-conditioning water-piping checks,not domestic-water/WSD rules. Code diameter,
fluid density/applicability,flow/control mode,edition and scope remain explicit
sourced assertions;none is inferred from bore diameter or a passing solver.
Velocity and distributed friction cannot be overridden. Known criterion breaches
map to fail;unknown facts or missing official bytes remain pending. Full
regulatory_compliance remains not_established and design_accepted stays false.

The report verifier reconstructs producer/method/source inventories,bound facts,
official-source availability,all rule checks and result status. A changed source
cache requires a new run. Same-evaluator replay is consistency,not independent
solver verification or authentication of project assertions.

Four official-source scenarios retain pass/fail/pending/pending for a synthetic
native circulation project. Eleven targeted invocations pass,including legacy
fresh solving,fluid consistency,existing rule checks and the new consumer's
override/tamper/unavailable controls. See evidence/module-water-rules.json.
This is a standalone CLI/API consumer;workflow task dispatch,automatic downstream
gates and a typed common RuleAssessment contract are still unfinished. It does
not establish complete HK applicability,physical acceptance or the full agent.
