# Active goal and user-authorized scope

Status: active;full completion remains unproven.

User-authorized modular revision recorded2026-11-11. This is an additive revision
of the same active Building Services Agent goal,not a new goal or a reduced
coursework-only objective. The user explicitly requested modular construction
and direct reuse of mature MOOSAS components where applicable.

Build a reusable,modular Building Services Agent in this repository:
requirements and source drawings → AI interpretation and traceable engineering
inputs → CAD/BIM modelling → performance and jurisdiction checks → iteration →
editable models,drawings,calculations and reports for the user to inspect/use.
Preserve HVAC,electrical,lighting,water/drainage and the full original building
services scope across different projects. Automatic coursework submission is
not part of the objective.

## Required architecture and reuse

1. Prioritize MOOSAS for architectural geometry transformation,space recognition/
   zoning,analysis-model exchange and energy/daylight/radiation/airflow workflows.
   Prefer direct calls or licence-compatible code reuse of mature modules over
   rewriting their engines. Pin versions,retain author/licence/NOTICE/modification
   records and execute compatibility tests. Latest upstream documentation is not
   evidence of an installed or executed capability.
2. Keep public data contracts and task orchestration independent of application,
   engine,jurisdiction and course. Version units,coordinate frames,IDs,source and
   assumption records,diagnostics and execution/acceptance states explicitly.
3. Keep AutoCAD,Revit and IFC as replaceable authoring/read/write adapters.
   Native MEP objects,connectors and DWG/RVT delivery belong to the corresponding
   adapter. MOOSAS space modelling is not native MEP installation modelling.
4. Use independent,replaceable performance adapters around MOOSAS or other
   verified upstream engines. Test,disable and replace modules independently.
   Host paths/environments belong in configuration;core code must not depend
   on private coursework paths or execute commands selected by a brief.
5. Keep Hong Kong as the first independent replaceable jurisdiction pack.
   Editions,applicability and official sources remain separate from modelling
   and calculation. MOOSAS templates are neither HK regulations nor measured
   project facts.
6. Separate intake,professional design,analysis,checking/iteration and delivery.
   Different assignments reuse project configuration and their own sources.
   Avoid accumulating course-specific helpers as the primary architecture.

Existing verified tools remain reusable. No wholesale rewrite is requested.
Implement [modular boundaries and contracts](MODULAR_ARCHITECTURE.md),starting
with the [MOOSAS reuse map](MOOSAS_MODULE_MAP.md). Exercise real coursework and
other projects,including actual component substitution,without narrowing scope
to whatever already passes.

## Completion evidence

Completion requires real editable artifacts,source traceability,appropriate
native save/reopen/visual evidence and applicable performance/regulation checks.
It also requires demonstrated cross-project reuse and component replacement.
Plans,contract drafts,compiled bridges,synthetic examples and successful narrow
tasks do not establish the complete agent. Missing inputs,blocked engines,
failed designs and unverified integrations remain explicit.

All development/generated files stay in this repository. Completed polyu_bse3124
remains read-only. Do not publish private coursework,credentials or generated
environments. Preserve third-party attribution and push verified milestones.
Retain all original requirements and distinguish thermal/electrical power.
Host security policies remain unchanged;blocked native execution stays blocked.
Coursework deliverables omit internal iteration/version labels.

## Goal metadata limitation

The available goal tool can read/create goals and update status;it cannot edit
the existing objective text. Its original objective remains active. This file,
the architecture plan and ROADMAP persist the authorized revision for the same
goal. No replacement goal was created and no metadata update or completion is
claimed. Subsequent continuations must apply this additive user direction.
