# Shared project command entry

The installed `bsa` command now exposes the existing source intake and reviewed
engineering handoff alongside the original electrical and workflow commands.
No new interpretation service, numerical engine or external dependency is added.

```powershell
bsa project-start path/to/brief.pdf --supplement path/to/rubric.md --reference path/to/guide.pdf --out runs/new-project
bsa handoff-template runs/new-project/plan.json --out runs/new-project/interpretation.json
# The host AI inspects the original pages, extraction issues and resulting plan,
# then writes the explicit engineering-handoff review described below.
bsa handoff runs/new-project/plan.json runs/new-project/interpretation.json --target runs/new-project/engineering-plan.json --out runs/new-engineering-run
bsa handoff-verify runs/new-engineering-run
```

Use the `effective_plan` returned by intake (possibly `role-plan.json`) rather
than assuming `plan.json`. See [engineering interpretation](ENGINEERING_HANDOFF.md)
for the exact review contract. The intake work-review template belongs to the
older work-plan review interface; it is not an engineering-handoff review.
Use `handoff-template` to create the exact engineering review format. It pins the
validated source plan and includes every original requirement binding and generic
interpretation-note ID. Task lists, acceptance criteria and notes are deliberately
empty; unchanged templates cannot execute. Inspect the original quotes in the
source plan and its documents before filling them. Ordinary input gaps remain in
the original plan and are retained by handoff; the empty extra-gap list does not
clear them. Output must be a fresh sibling of the source plan. Existing engineering
plans cannot be replaced through this interpretation route.
The template/source-preservation controls and a fresh four-domain replay are
recorded in [template evidence](evidence/handoff-template.json); nineteen related
tests pass. This does not add autonomous semantic interpretation.
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

Both `bsa workflow` and `bsa handoff` also accept `--moosas-upstream` and
`--moosas-deps` as explicit trusted host directories. They forward these to the
existing isolated adapter; briefs/plans do not choose import paths. For example:

```powershell
bsa workflow examples/modular-plan.json --out runs/new-moosas-workflow --module-provider spaces=moosas.box-space-exchange --moosas-upstream tools/moosas-review --moosas-deps tools/moosas-exchange-deps
```

The same unchanged public source plan was actually executed with both native
IFC and MOOSAS providers through this entry. The three-space payloads and the
derived thermal project match exactly. Disabled and unconfigured MOOSAS controls
retain unavailable exchange and do not create thermal inputs. Annual analysis was
also attempted with installed EnergyPlus on both paths; host Application Control
blocks OpenStudio import before simulation, with explicit retained failure logs.
No annual result or security-policy change is claimed. Twenty related tests pass.
See [replacement evidence](evidence/shared-cli-moosas.json). This remains a
synthetic box-space case, not complete MEP or simulation acceptance.

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
