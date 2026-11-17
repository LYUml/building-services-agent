# Use the supported agent workflows

The supported source-bound workflows are usable through the installed CLI and
project-scoped MCP. The [architecture acceptance audit](ARCHITECTURE_ACCEPTANCE.md)
records current execution and remaining gates; the earlier
[usability audit](USABILITY_ACCEPTANCE.md) retains its own source-version scope.
The long-term engineering roadmap remains open.

## Start in this checkout

```powershell
python -m pip install -e ".[drawing,mcp,codex-setup]"
bsa doctor --extra drawing --extra mcp
# After configuring MCP with actual host paths:
bsa doctor --extra drawing --extra mcp --mcp-config .codex/config.toml
```

Use the intended virtual environment's Python and `bsa`. Optional domains need
their own pinned extras and host engines. Doctor checks distributions/path
presence, not native execution. Follow [MCP setup](CODEX_LOCAL_SETUP.md) to
configure a new connection. Saved settings alone do not prove that an existing
chat loaded them; verify its actual tools and effective host paths.
The current project profile has actual AutoCAD, Graphviz, EnergyPlus, Radiance
and Poppler paths; it does not automatically configure every optional engine.

For a real project, select its existing directory in the host environment as
`BSA_PROJECT_ROOT`. Keep its inputs and outputs there. Without a selection,
development outputs use this checkout's ignored `runs` directory. Completed
BSE3124 stays read-only. BSE3227's existing delivery remains awaiting user review.

## Give the host AI a project

An appropriate starting request is:

> Continue from the existing project results in the host-selected workspace.
> Read the original brief and drawings, preserve every requirement and inspect
> the saved status before executing. Use existing supported tools and sourced
> inputs. Record assumptions separately from measured facts and design targets;
> retain missing inputs. Interpret the source plan explicitly, calculate and
> author native deliverables, then independently check the saved results and
> inspect the actual plots. Reuse unchanged results where their evidence still
> verifies. Preserve failed baselines during iteration. Return usable files and
> the remaining review items; do not infer my design acceptance.

The host AI supplies semantic interpretation and engineering judgments. The
toolkit does not turn arbitrary brief text into an autonomous approved design.
Use `bsa project-start BRIEF --out FRESH_PROJECT` and its returned `effective_plan`.
Then `bsa handoff-template PLAN --out FRESH_SIBLING_REVIEW` prepares the exact
interpretation contract. An untouched template cannot execute. See
[project/handoff commands](PROJECT_CLI.md) for execution and host runtime flags.

## Run and inspect a capability

| Need | Executed entry | Remaining scope |
|---|---|---|
| General 2D CAD | [Drawing workflow](GENERAL_DRAWING_WORKFLOW.md) | Source-bound recipes; actual native reopening and plot review required |
| Electrical, air, water and IFC | [Engineering handoff](ENGINEERING_HANDOFF.md) | Explicit host interpretation; example disciplines are independent |
| Annual/IFC/PTAC energy | [Native energy](NATIVE_ENERGY_USABILITY.md) | Explicit weather/model/equipment basis; synthetic cases are not project designs |
| Shared lighting and native CAD | [Shared lighting](SHARED_LIGHTING_USABILITY.md) | IES/source geometry applicability, glare and full code review remain separate |
| Failed operating-point iteration | [Pump recovery example](../examples/pump-recovery/README.md) | Supplied catalogue only; retain product/installation review |
| Common identities, units and source inputs | [Engineering data](ENGINEERING_DATA.md), [input ownership](ENGINEERING_INPUTS.md) | Air/electrical/lighting views; other capabilities retain their typed contracts |
| Source-linked knowledge | [Knowledge workflow](KNOWLEDGE.md) | Explicit selected sources/pages/conditions; retrieval does not establish applicability |
| Changes and safe numerical reuse | [Change impact](CHANGE_IMPACT.md) | Verified checkpoint required; numerical reuse whitelist is air/electrical only |

Inspect saved output without recomputing:

```powershell
bsa workflow-verify RUN
bsa workflow-status PLAN RUN
bsa delivery template PLAN RUN --out FRESH_REVIEW
bsa delivery audit PLAN RUN --review REVIEW --out FRESH_AUDIT
```

Intact evidence, successful execution and engineering review are distinct.
Exit2 can mean pending interpretation/manual review, not a crash. Inspect the
returned JSON and [exit-code contract](PROJECT_CLI.md). Record only observations
actually made; all other requirements remain pending. Methods/source changes
may invalidate old receipts: retain them as history instead of rewriting hashes.
Tool success never substitutes for user acceptance or statutory certification.
