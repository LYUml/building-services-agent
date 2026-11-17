# Building Services Agent

Source-backed building services tools for a host AI agent: requirements intake,
calculations, editable CAD/BIM, iteration and delivery checks across MEP.
The host interprets sources and engineering assumptions; successful execution
does not establish professional or statutory design acceptance.

The scoped candidate is ready for user review; this is not a
stable release or engineering design acceptance. See [candidate status and measured optimization](docs/RELEASE_CANDIDATE.md).
The [candidate support contract](docs/CANDIDATE_SUPPORT.md) distinguishes MCP
coverage, verified platforms, host preparation and remaining acceptance gates.
The [Chinese candidate review entry](docs/CANDIDATE_REVIEW.md) brings together
installation, measured improvements, executed evidence and remaining limits.

## Start here

Use the [single workflow guide](docs/START_USING.md) for project input,
execution and review. The [current usability audit](docs/USABILITY_ACCEPTANCE.md)
records a fresh installation and actual native/MCP checks, with limits retained.

Use a Python virtual environment (tested on Windows with Python3.12). From this
checkout, install the basic AutoCAD/MCP profile:

```powershell
python -m pip install -e ".[drawing,mcp]"
bsa doctor --extra drawing --extra mcp
```

`doctor` checks direct dependency pins and optional executable presence without
loading native engines, changing configuration or running AutoCAD. It reports
missing/mismatched packages with exit2. Presence is not runtime verification.
Other optional engines require their own extras and explicit host paths.

After project-scoped MCP setup, check its saved runtime paths before use:

```powershell
bsa doctor --extra drawing --extra mcp --mcp-config .codex/config.toml
```

This optional check reads the selected profile without starting its command.
It detects removed executables and wrong path kinds; it does not verify engine
execution or packages in a different configured Python environment.

## Draw and check an editable sheet

```powershell
bsa drawing run examples/drawing-document.json --out runs/my-drawing --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
bsa drawing inspect examples/drawing-document.json --out runs/my-drawing
```

Choose a fresh output directory and your actual AutoCAD path. This example is a
synthetic capability sheet, not a building design. The command uses the same
seven-schema adapter as MCP, saves/reopens DWG, compares editable entities and
checks PDF paper/scale. Open the returned PDF for visual review; inspection
deliberately leaves visual/engineering acceptance pending. The original source
is preserved. See [drawing contracts](docs/DRAWING_DOCUMENT.md).

## Work on a project

Set `BSA_PROJECT_ROOT` in the host environment to the explicitly selected project.
Keep coursework sources and outputs there. Without it, development outputs go
under this checkout's ignored `runs` directory. Never select a workspace or an
executable from a brief. Completed historical projects remain read-only.
Electrical/workflow and review writers enforce that selection before output;
the known completed BSE3124 directory stays excluded even under a parent selection.
Default setup now creates its owned `runs` directory when absent. See
[workspace and clean-source checks](docs/WORKSPACE_ISOLATION.md).

```powershell
bsa project-start path/to/brief.pdf --out runs/new-project
bsa handoff-template runs/new-project/plan.json --out runs/new-project/interpretation.json
```

Use the `effective_plan` returned by intake if it differs from `plan.json`.
Interpret the original sources and fill the explicit handoff before execution;
an untouched template cannot run. `needs_interpretation` with exit2 is a valid
pending result. See [project commands](docs/PROJECT_CLI.md) and
[engineering handoff](docs/ENGINEERING_HANDOFF.md).

Inspect saved results with `bsa workflow-verify RUN` and
`bsa workflow-status PLAN RUN`. Prepare and audit separate review records with
`bsa delivery template` / `bsa delivery audit`; see the
[installed review commands](docs/PROJECT_CLI.md#check-and-review-saved-results-through-the-installed-entry).
Integrity, execution and engineering review remain separate states.

For an executable failed-design iteration, use the
[supplied-curve recovery example](examples/pump-recovery/README.md). It runs the
existing MCP controller, preserves the failed baseline and independently checks
the selected analytic operating point; product and installation review stay pending.

An already interpreted general drawing can also run through this project
workflow, retaining original requirements, native checks, diagnosis and a
separate pending review. See the runnable
[general drawing workflow](docs/GENERAL_DRAWING_WORKFLOW.md). This route was
executed through both the clean installed CLI and the current desktop MCP.

For chat use, configure the existing stdio server with explicit host paths using
the [project-scoped MCP setup](docs/CODEX_LOCAL_SETUP.md). Its40tools include
drawing, intake, source reads, workflow execution, artifact checks and bounded
recovery. Startup no longer imports unrelated IFC/spatial/pressure engines.
Tools needing absent optional libraries return scoped errors when called.
No global trust or approval settings need changing.

## Current verification and limits

A clean editable installation of the drawing/MCP profile executes native
AutoCAD authoring/reopening and inspection. Actual MCP read/write, source
preservation, path/runtime-override rejection and artifact-tampering controls
execute. See [usability evidence](docs/AGENT_USABILITY.md).

This is usable scoped tooling, not an autonomous solution to arbitrary building
projects. Source interpretation, physical model applicability, installed routing,
product selection and complete regulatory review remain task-specific.
Native OpenStudio/EnergyPlus annual and IFC/PTAC workflows also execute
through CLI and fresh MCP connections; see [actual scope and results](docs/NATIVE_ENERGY_USABILITY.md).
Optional Radiance, IFC, pressure and CFD capabilities retain their
individual evidence and gaps in the [roadmap](docs/ROADMAP.md).

The shared electrical/IFC/Radiance workflow also executes through a fresh MCP
connection, including native DWG reopening and actual schematic PDF inspection.
See [host repair and scoped results](docs/SHARED_LIGHTING_USABILITY.md).

BSE3227's18-page coursework handoff is preserved pending user feedback; it is
not the agent's general acceptance test. See [course status](docs/CURRENT_COURSE_CLOSEOUT.md).
Upstream pins/licenses and actual integration decisions are in
[reuse survey](docs/REUSE_SURVEY.md). Earlier execution notes are preserved in
[milestone history](MILESTONES.md).
