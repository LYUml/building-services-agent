# Project regulatory planning coverage

`bsa.regulation_coverage` compares a sourced project scope decision for every catalog topic with the available rule modules and, optionally, a validated workflow plan. It helps the agent identify missing work before design or delivery. It does not infer legal applicability or certify an exhaustive list of obligations.

```powershell
.venv/Scripts/python -m bsa.regulation_coverage --catalog regulations/hk/coverage-2026.11.08.json --scope examples/regulations-hk/coverage-scope.json --plan runs/hk-hvac-workflow-positive-v1/plan.json --out runs/new-coverage-review
```

Omit `--plan` for intake-only review. Exit 2 means declared planning gaps exist. Exit 0 only means no gaps were identified in the declared scope, never compliance or complete coverage. JSON and Markdown outputs retain sourced decisions, official inventory metadata, available rules, scheduled task IDs and input hashes.

The initial Hong Kong catalog covers review prompts for electrical, lighting, HVAC, plumbing, drainage, fire, energy audit, government contract specifications and utility/referenced-standard requirements. It reuses the existing dated official-source inventory; no new technical clauses or legal thresholds are inferred. Catalog `modules` reference jurisdiction packs by explicit identity and rule IDs. A future region uses its own catalog and packs without changing the review algorithm.

Every topic must be declared `required`, `excluded` or `unresolved`, with a project evidence reference. Exclusions also require a rationale. Missing topics, invented decisions, absent evidence references and catalog/module identity drift are rejected. Evidence strings remain assertions for professional review. The example scope is synthetic and must not be reused as a real project's applicability decision.

Gap categories distinguish unresolved applicability, no implemented module, available modules omitted from a plan, and partial rule coverage within a module. Scheduling is matched by actual pack bytes, not merely a task name or claimed pack ID. Scheduled rules remain `execution_status: not_assessed`: use workflow execution, source binding and delivery review for actual results. A task behind an unresolved prerequisite can still be scheduled; this planning report does not claim it ran.

The catalog itself is not exhaustive and cannot prove whole-project completeness. All outputs retain `coverage_complete: false`, `regulatory_compliance: not_established` and `design_accepted: false`, including when every topic has a sourced exclusion. Existing legacy pack coverage notes are reported verbatim; consult current adapter documentation for subsequently implemented bindings.

Evidence under `docs/evidence/regulatory-coverage` compares the synthetic multi-discipline scope against the actual staged HVAC plan. It correctly recognizes the scheduled HVAC module while retaining its partial coverage, identifies unscheduled electrical/lighting modules and explicitly exposes unimplemented water/drainage/fire checks. Official PDFs are not redistributed.
