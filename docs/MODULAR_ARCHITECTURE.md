# Modular architecture and next implementation sequence

Common source-linked requirements inventory now executes through the trusted
module runner and automatically after validated project_start intake. Exact
passages,requirements,locators and unresolved inputs survive source replay on
electrical,water and real BSE3227 plans. Semantic completeness and design-input
binding remain unfinished. See REQUIREMENTS_MODULE.md.

Conditional single-phase electrical analysis now also has an executed common
provider/contract through the existing engine and workflow gates. Source replay
and explicit electrical units preserve fault/protection/native/code gaps. This
does not complete three-phase or physical electrical provider coverage. See
MODULAR_ELECTRICAL.md.

The saved-water jurisdiction consumer now emits an initial validated
`bsa.rule-assessment/1` alongside its detailed legacy report. Entity/rule IDs,
pack/jurisdiction,producer hash,source hash/edition/clause and original check
states remain explicit. The scoped projection now also runs through the registered
standalone bsa.hvac-water-rules provider (RULE_PROVIDER.md). Unknown/exempt states
remain pending in this contract. The existing water rule task now optionally
dispatches that registered provider while retaining exact-producer gates.
Other disciplines and actual jurisdiction-provider replacement remain unfinished.

The initial rule contract also requires per-entity implemented/pending coverage
lists. Every assessed entity has exactly one coverage record;pending lists remain
nonempty while coverage_complete is false. The consumer reconstructs these
lists from the original evaluator on verification. Historical outputs without
these required fields reject the current contract;rerun instead of patching old
assessment bytes. Full regulatory conformity remains not_established.

This is the execution plan for [the active goal](GOAL.md). The first request/result
and box-space contracts plus MOOSAS provider now execute as described in
[MODULES.md](MODULES.md). Remaining boundaries/registry coverage below are planned,
not implemented capability claims.
Existing workflow/project formats remain authoritative until explicit adapters
and migration tests are executed.

## Boundaries

| Module | Responsibility | Must remain outside it |
|---|---|---|
| Requirements | Source passages,obligations,missing facts and acceptance | Executable commands,assumed equipment facts |
| Common engineering data | IDs,SI quantities,frames,spaces,systems,ports and provenance | Private course paths or application object handles as sole IDs |
| Design | Source-backed choices,alternatives and discipline topology | Hidden code defaults presented as supplied facts |
| Authoring providers | AutoCAD/Revit/IFC native objects,connectors,save/reopen | Selecting regulations or changing engineering criteria |
| Spatial/performance providers | MOOSAS exchange/geometry and other pinned analysis engines | Native MEP acceptance or invented material/operating inputs |
| Jurisdiction providers | Independent HK and later regional applicability/rule packs | Engine/application-specific geometry ownership |
| Check/iteration | Source/geometry/performance review and retained alternatives | Clearing unknowns merely to pass a gate |
| Delivery | Editable artifacts and evidence-bound acceptance | Portal submission or success inferred from file existence |

Orchestration selects supported contracts/providers and declared dependencies.
It must not contain geometry kernels,duplicate solvers or course-specific design
rules. Existing bsa workflow adapters may initially act as compatibility wrappers.

## Public contract design

First implement a small versioned module envelope around an actual MOOSAS
vertical slice. Do not require a simultaneous rewrite of every legacy domain.
The envelope must identify contract/schema version,capability,provider/version,
project/scenario IDs,source/artifact hashes,quantity units and coordinate frame.
References preserve exact source bytes,locators and classifications:measured,
given,manufacturer,assumed or design_target as appropriate to the domain.

Execution and engineering acceptance remain separate. Execution needs explicit
completed/failed/unavailable/pending states with structured diagnostics and raw
engine evidence;acceptance needs pass/fail/pending by requirement and scope.
Legacy task pass/fail/pending records must remain available without semantic
relabeling. A provider unavailable on this host cannot return synthetic results.
Unknown units,frames,editions,IDs or unsupported versions reject or remain
pending;no implicit unit/axis/coordinate conversions or regulatory defaults.

Initial shared payloads should cover source-linked SpatialModel,ModelArtifact,
AnalysisRequest/Result,RuleAssessment and DeliveryBundle. Specify exact schemas
and executable validators before advertising interoperability. Preserve detailed
domain payloads rather than flattening thermal kW into electrical kW or kVA.

Provider manifests must declare contract compatibility,upstream pin/licence,
runtime profile,availability and executed evidence. Runtime/application paths
are host configuration,not document-provided commands. A listed provider is not
necessarily installed,available or verified. Disabling a provider must preserve
dependent failures/pending work while independent tasks continue.

## Next milestones in order

1. Initial bounded slice implemented:module request/result,box-space schemas and
   the existing executed MOOSAS wrapper as a trusted provider (MODULES.md).
   Preserve original source checks/failures;extend contracts incrementally.
2. MOOSAS exchange now has explicit inputs,outputs and availability outcomes.
   Continue transform/model/simulation mapping using MOOSAS_MODULE_MAP.md;test
   real upstream calls before making additional modules available.
3. Initial replacement now executes with native IfcOpenShell and MOOSAS on two
   saved IFC projects,including disabled/zero-space controls (MODULES.md).
   Shared extraction limits this to interoperability. Existing workflow gating
   now propagates disabled/failed results and preserves independent branches.
   Neutral box payload inheritance into annual thermal preparation now executes;
   actual inherited simulation remains unexecuted. Next:broader consumers/contracts,
   including dropped-space/boundary ownership
   controls. A mock validates dispatch only.
4. Route existing AutoCAD/IFC,Revit and performance adapters through the boundary
   incrementally. Native IFC now has an initial model-artifact authoring provider
   and executed downstream chain;other authoring-provider substitution remains
   unverified. The existing rectangular air-tree budget now has a typed analysis
   provider with separate completed/numerical-fail gating. Bounded canonical
   source/native rectangular binding now executes;arbitrary native-model intake
   and replacement by another solver remain unfinished.
   Steady declared water/circulation graphs now also use the common analysis
   boundary via the existing WNTR/EPANET worker. Scoped native IFC water-model
   inheritance now also executes. Scoped HVAC-pipe rule handoff now executes in
   the workflow;typed common rule output and full acceptance remain unfinished. Keep blocked
   Revit/analysis execution visible;do not bypass
   signing policy or silently upgrade EnergyPlus versions.
5. Bind independent HK rules and requirement/delivery review to the same common
   source IDs. Reproduce the real HVAC project and another independent project,
   retaining every original obligation and scoped engineering limitation.

The finite-elbow milestone278bce6 is closed for review:8 authored,2 blocked,
40 remaining intersection pairs and complete design pending. Prefer the modular
vertical slice next over more course-specific authoring helpers. Continue real
engineering work with existing tools;put necessary new capabilities behind the
same boundaries. Do not substitute architecture documents for executable reuse
or the original complete multi-discipline outcome.
