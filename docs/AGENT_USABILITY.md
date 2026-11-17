## Current complete usability audit

The current supported-workflow checkpoint has an independent fresh installation,
actual native CLI/new MCP execution and a requirement-by-requirement audit.
Use [START_USING.md](START_USING.md) for the normal entry and
[USABILITY_ACCEPTANCE.md](USABILITY_ACCEPTANCE.md) for evidence and limits.
Historical repairs and receipts below remain preserved; the full engineering
roadmap and coursework acceptance are separate.

# Agent usability milestone

Missing known optional imports now produce an actionable exit2/profile hint in
the installed CLI and a structured worker failure for MCP. No package is
installed automatically. Unknown/nested imports do not get guessed profiles;
native DLL/policy import failures keep their adapter-specific diagnostics.
An actual minimal drawing/MCP profile without rectpack reproduces the former
traceback and now reports `drawing-layout` with no drawing directory created.
15related CLI/worker/startup tests pass. See
[missing-profile evidence](evidence/missing-dependency-errors.json).

The installed `bsa drawing run/inspect` commands now use the same existing
seven-schema boundary as the MCP tools. No second drawing engine or new CAD
dependency is introduced. `bsa doctor --extra drawing --extra mcp` reads the
declared exact direct dependency pins and optional host executable presence.
It neither imports native engines nor proves their execution.

Two actual setup defects were reproduced and repaired:

- Native drawing could leave a DXF directory before discovering a missing
  AutoCAD executable or PDF dependency. Shared preflight now rejects first.
  A drawing extra declares pypdf and the tested ezdxf dependency versions.
- A clean `drawing,mcp` installation could not start the server: imports of
  terminal iteration required Shapely, then pump imports required IfcOpenShell.
  The protocol now sends the same fixed39 operation names to a worker; only
  the chosen engine is imported in that isolated process. Its40 tools remain.
  Unknown operations cannot select Python modules or functions.

The existing host runtime option names moved to a lightweight constant module.
New handoff/catalogue/terminal/recovery records pin that module as method input;
verifiers retain the corresponding required pin. Old method-bound runs remain
historical: no recorded hashes/statuses were rewritten to claim fresh validity.

## Executed evidence

A fresh Python3.12 virtual environment installed `.[drawing]`, then
`.[drawing,mcp]` without IFC, Shapely, fluids or the development environment.
The first install resolved NumPy2.5.5; the drawing extra was then tightened to
the previously tested2.5.4, and the clean environment was updated before execution.
No environment or downloaded package is committed.

- Installed CLI authoring saves/reopens actual AutoCAD DWG and checks18editable
  entities, including3native dimensions. The plotted105/55/30dimensions and
  plan/system/detail were visually inspected. The clean-install plot pixels
  exactly match that inspected plot. This is a synthetic capability fixture.
- Clean MCP protocol runs two existing tests: actual author/inspect plus TEXT
  and LINE/CIRCLE/ARC revision; and DXF inspection with path/runtime-override
  rejection and artifact-corruption controls. Both pass.
- A clean intake produces five original requirements and five retained input
  gaps; the generated engineering review stays non-executable until interpreted.
-36targeted startup,doctor,CLI,handoff,catalogue,terminal/recovery tests pass.
- Existing MCP server suite:3pass,1explicit PDF-preview fixture skip. Native
  source-to-engineering and pump/electrical recovery execute in the full runtime.
- Clean environment's9doctor/CLI/startup tests pass. Startup is additionally
  tested with optional native imports explicitly denied.

See [machine-readable evidence](evidence/agent-usability.json).

## Current boundary

An executable file's existence is not native acceptance. `drawing inspect`
retains visual/design pending even after source/native integrity succeeds;
the separate human/host visual observation belongs to the exact plotted PDF.
Optional-engine tools return errors when their required libraries are missing;
their presence in the inventory is not availability or engineering acceptance.
Arbitrary brief interpretation, complete physical design and full statutory
coverage remain the long-term goal. BSE3227 files were not changed in this phase.
