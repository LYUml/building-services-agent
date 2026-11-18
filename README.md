# Building Services Agent

Source-backed tools for a host AI: requirements, engineering calculations,
editable CAD/BIM, iteration and checked deliverables across building services.
The host interprets sources and assumptions; tool success is not design approval.

Windows source prerelease: [v0.1.0-beta.2](https://github.com/LYUml/building-services-agent/releases/tag/v0.1.0-beta.2).
Extract the source ZIP and run `Setup.cmd`; see the installation guide below.

## Start here

- [Use the agent](docs/START_USING.md): project setup, execution and review.
- [One-click installation](docs/INSTALL.md): Windows prerelease setup and profiles.
- [Supported capabilities](docs/CANDIDATE_SUPPORT.md):42MCP tools and host requirements.
- [Acceptance evidence](docs/ARCHITECTURE_ACCEPTANCE.md): actual results and limits.
- [Documentation index](docs/README.md): choose a focused guide.

Use a Git checkout and a dedicated Python environment (verified on Python3.12):

```powershell
python -m pip install -e ".[drawing,mcp,codex-setup]"
bsa doctor --extra drawing --extra mcp
```

Add only the domain extras and host engines needed by the project. Configure
[project-scoped MCP](docs/CODEX_LOCAL_SETUP.md) with actual host paths; inspect
its saved profile with `bsa doctor --mcp-config .codex/config.toml`.

## Draw and check an editable sheet

Use the [general drawing workflow](docs/GENERAL_DRAWING_WORKFLOW.md) or
[drawing contracts](docs/DRAWING_DOCUMENT.md). Native DWG acceptance requires
actual AutoCAD reopening and visual plot review. Synthetic examples demonstrate
capabilities; they are not completed building designs.

## Work on a project

Select the existing project through host `BSA_PROJECT_ROOT`; keep its sources
and outputs there. Documents cannot select workspaces or executables. Without
a project selection, development outputs use ignored `runs`. Completed BSE3124
is read-only; BSE3227's existing submission is not changed automatically.

The [workflow guide](docs/START_USING.md) covers source interpretation, execution,
saved-result inspection and separate engineering review. Shared
[engineering data](docs/ENGINEERING_DATA.md), [knowledge retrieval](docs/KNOWLEDGE.md)
and [change impact](docs/CHANGE_IMPACT.md) reuse existing calculation engines.
Knowledge is a source-linked SQLite index; engineering models/results remain
typed files, not a single all-purpose database.

## Current verification and limits

The architecture candidate is ready for user review; no stable release or user
acceptance is asserted. Full regression records1949cases, zero failures/errors
and258retained skip outcomes. Actual HVAC and lighting workflows are checked;
scope and original evidence are in the [acceptance audit](docs/ARCHITECTURE_ACCEPTANCE.md).

Arbitrary automatic design, complete pressure/CFD, Revit native creation and
whole-project statutory certification remain outside this acceptance claim.
See the [roadmap](docs/ROADMAP.md). Upstream pins/licenses remain in
[THIRD_PARTY.md](THIRD_PARTY.md) and the [reuse survey](docs/REUSE_SURVEY.md).
Development and historical references are separated in [development notes](docs/DEVELOPMENT.md).
