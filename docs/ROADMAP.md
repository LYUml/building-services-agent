# Roadmap

## Current stage

The ordered architecture stage is complete for scoped user review: module
boundaries, common source-linked data, knowledge retrieval, change impact and
real HVAC/lighting verification. User acceptance is pending; no formal release.
See [current status](AGENT_STATUS.md) and [acceptance evidence](ARCHITECTURE_ACCEPTANCE.md).

## Full goal

Preserve an end-to-end building-services workflow:

1. Extract requirements and source interpretations; retain missing inputs.
2. Author editable AutoCAD/BIM models, diagrams, details, annotations and sheets.
3. Perform source-backed electrical, HVAC, lighting, water and energy analysis.
4. Revise designs with dependency tracking and independently verified reuse.
5. Reconcile drawings, calculations, equipment information and reports.
6. Verify native reopening/plots and return explicit engineering review items.

Measured values, assumptions and targets stay separate. Reuse pinned verified
upstream engines and preserve their attribution; do not replace them gratuitously.

## Remaining engineering work

| Area | Remaining boundary |
| --- | --- |
| Shared data | Broaden air/electrical/lighting projections while preserving other typed domain contracts; refine conservative dependency consumers |
| Knowledge | Curate more applicable primary sources with edition/page/conditions; retrieval alone does not establish applicability |
| CAD/BIM | Extend layouts/annotations and source geometry; retain GIS/site, room-program and shading gaps, native Revit creation and installation/product verification |
| HVAC | Complete source-backed full pressure, fitting/equipment losses, physical joints, manufacturer applicability and fan/motor/operating constraints |
| Water/electrical | Extend supported networks, real equipment, protection/coordination and model-driven handoff within explicit source/rule boundaries |
| Lighting/energy | Retain optical/geometry/weather applicability; sparse photometric coordinates and new simulations require their separate checks |
| CFD | Keep existing mesh/solver/convergence evidence and unresolved physical validation; CFD is not a coursework delivery prerequisite |
| Regulations | Expand scoped rule coverage without inferring whole-project statutory compliance or inventing clauses |
| Distribution | Validate additional platforms/package layouts and broader real projects before expanding supported release claims |

Domain construction choices, raw failed controls, product/curve limitations and
unresolved obligations remain in their focused guides and evidence. A successful
local study does not clear an entire real network or certify installation.

## Working rules

Work from existing project results. Keep coursework in the selected project;
BSE3124 remains read-only and BSE3227 is not automatically revised. Preserve
source originals, failed baselines, engineering limits and upstream notices.
Use [START_USING.md](START_USING.md) for operations and
[DEVELOPMENT.md](DEVELOPMENT.md) for implementation references.

Previous detailed progress narrative is retained in
[the immutable pre-cleanup roadmap](https://github.com/LYUml/building-services-agent/blob/19e29fb41a7c3dd80e59813d28c6a79310075a24/docs/ROADMAP.md).
It is history, not the current task list.
