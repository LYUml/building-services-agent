# Shared project command entry

The installed `bsa` command now exposes the existing source intake and reviewed
engineering handoff alongside the original electrical and workflow commands.
No new interpretation service, numerical engine or external dependency is added.

```powershell
bsa project-start path/to/brief.pdf --supplement path/to/rubric.md --reference path/to/guide.pdf --out runs/new-project
# The host AI inspects the original pages, extraction issues and resulting plan,
# then writes the explicit engineering-handoff review described below.
bsa handoff runs/new-project/plan.json runs/new-project/interpretation.json --target runs/new-project/engineering-plan.json --out runs/new-engineering-run
bsa handoff-verify runs/new-engineering-run
```

Use the `effective_plan` returned by intake (possibly `role-plan.json`) rather
than assuming `plan.json`. See [engineering interpretation](ENGINEERING_HANDOFF.md)
for the exact review contract. The intake work-review template belongs to the
older work-plan review interface; it is not an engineering-handoff review.
Interpretation remains a host AI task requiring complete source inspection and
explicit input/acceptance bindings. These commands do not infer a design from
keywords or fill missing survey/product/regulatory facts.

For an external project, select `BSA_PROJECT_ROOT` in the host environment first;
keep sources, configurations and generated work there. Existing source/path
guards apply. Fresh plans and output folders are required. Original commands
remain available, including `bsa workflow` for an already interpreted plan.

`handoff` accepts host runtime paths for `--energyplus`, `--autocad`,
`--radiance-bin`, `--ifcmcp-python`, `--three-phase-python`, `--graphviz`,
`--pdf2plot-python` and `--honeybee-python`. It also forwards existing
`--module-provider TASK=PROVIDER` and `--disable-module-provider PROVIDER`
selections through existing validators. A document cannot choose executables.
Unsupported provider bindings and missing runtime checks remain adapter errors.

Intake and handoff return exit 2 while interpretation or engineering acceptance
is pending. Inspect JSON `status`, `stages` and `stage_errors`; code 2 does not
necessarily indicate a process crash. `handoff-verify` returns 0 only for intact
correspondence, and still reports `design_accepted=false`. It is not a design
approval or semantic completeness test.

Executed public synthetic trial: electrical, air, water and IFC tasks pass while
manual review remains pending; all five original requirements survive and the
independent handoff reconstruction passes. A disabled source-inventory trial
stops before workflow execution and produces no workflow directory. Seventeen
related CLI/intake/handoff/workflow tests pass. See
[aggregate evidence](evidence/project-cli.json). This is unified access to scoped
existing tools; full integrated design, native delivery and arbitrary brief
interpretation remain unfinished. Existing upstream attribution is unchanged.
