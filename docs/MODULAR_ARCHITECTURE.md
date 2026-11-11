# Modular architecture and next implementation sequence

This is the execution plan for [the active goal](GOAL.md). The contracts and
provider registry below are proposed work,not implemented capability claims.
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

1. Define and implement the minimum envelope/validator/provider boundary for the
   existing executed MOOSAS space exchange. Preserve its original source checks
   and failures. Add no replacement geometry/space-recognition engine.
2. Promote that wrapper from script-only use into a pinned provider with explicit
   inputs,outputs and availability. Map transform/model/simulation modules using
   MOOSAS_MODULE_MAP.md;test real upstream calls before marking each available.
3. Execute replacement/disable controls and the same contracts with another
   genuinely applicable implementation. A mock validates dispatch only,not
   successful engine replacement. Include incompatible-version and dropped-space/
   boundary-ownership controls.
4. Route existing AutoCAD/IFC,Revit and performance adapters through the boundary
   incrementally. Keep blocked Revit/analysis execution visible;do not bypass
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
