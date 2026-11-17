# Candidate support and control boundaries

This contract describes the current candidate, not a stable release or user
acceptance. Preserve the full multi-service roadmap. Existing experimental
adapters do not become accepted simply because their module exists.

## Installation and platforms

Use an actual source Git checkout at the selected commit and install the needed
pyproject extras into its dedicated environment. The source ZIP retains resources
but lacks immutable reference Git objects; the wheel does not yet retain the
complete source-relative runtime layout. Neither is a full replacement for that
checkout. Source candidate artifacts are for inspection and scoped execution.

Core Python/MCP checks run on Python 3.12, Windows and Ubuntu. Metadata permits
Python >=3.11, but that declaration alone is not executed 3.11/3.13 acceptance.
Native DWG acceptance is verified with Windows AutoCAD 2027, including actual
reopening and plotted-output review. Ubuntu core success proves no native DWG.
Optional EnergyPlus, Radiance, IFC, hydraulic, geometry and isolated adapter
profiles retain their declared extras and explicit host runtimes. Their exact
evidence and unresolved scope remain in the domain guides and CI results.

The default install is small relative to the full development environment;
it intentionally does not install every optional solver. Use START_USING.md and
doctor for the selected profile. Doctor inspects direct pins/path presence and
does not certify native runtime behavior. Engineering assumptions, jurisdiction
applicability and human design acceptance remain separate from software checks.
The [lighter HVAC profile](HVAC_LIGHT_PROFILE.md) uses reports/network/spatial;
its actual native project replay works without Matplotlib or IFC. Add the mcp
extra for protocol access; a CLI profile is not itself a connected MCP session.

## MCP coverage

The current actual SDK catalogue has 40 tools. The following groups cover all
40; numerical engines remain shared with CLI/workflow adapters rather than
duplicated for MCP. Tool schemas and full descriptions are available through
the SDK catalogue. The committed reference read is also an MCP resource.

| Area | MCP tools |
|---|---|
| General drawing | bsa_draw_document, bsa_inspect_drawing_document |
| Native network and fittings | bsa_run_native_network_analysis, bsa_run_native_fitting_analysis, bsa_inspect_native_network_analysis, bsa_inspect_native_fitting_analysis, bsa_list_native_fitting_requests, bsa_read_native_fitting_request |
| Native network delivery | bsa_run_native_network_delivery, bsa_inspect_native_network_delivery, bsa_run_tagged_network_delivery, bsa_inspect_tagged_network_delivery |
| Pressure evidence | bsa_run_pressure_evidence_ledger, bsa_inspect_pressure_evidence_ledger, bsa_list_pressure_evidence_gaps, bsa_read_outlet_pressure_evidence |
| Project intake and interpreted handoff | bsa_project_start, bsa_read_source_plan, bsa_handoff_template, bsa_save_json, bsa_execute_handoff, bsa_verify_handoff |
| HVAC packages | bsa_prepare_hvac_project, bsa_run_hvac_project, bsa_inspect_hvac_project |
| Multi-service workflows | bsa_execute_workflow, bsa_diagnose_workflow |
| Source review and references | bsa_render_source_page, bsa_prepare_visual_transcription, bsa_review_source_plan, bsa_reference_catalogue |
| Iteration and recovery | bsa_recover_pump_catalogue, bsa_verify_pump_recovery, bsa_run_recovery, bsa_verify_recovery |
| Artifact access and delivery review | bsa_artifact_index, bsa_read_artifact, bsa_render_artifact_page, bsa_delivery_template, bsa_assess_delivery |

Energy, lighting, electrical, water, IFC and regulation task kinds use the
existing interpreted workflow/handoff entry points. This is not a claim that
every CLI module has a separate MCP tool, or that arbitrary incomplete briefs
can execute without interpretation. Source recipes, supported schemas and
domain evidence still govern which tasks can run.

No computer-use mechanism is needed by these MCP adapter execution paths.
AutoCAD work uses explicit host native processes and saved-data adapters.
Software installation/licensing, file access, startup executable paths, font and
plotting configuration are host preparation. External tools such as K-Select
retain their own integration scope; the 40-tool catalogue does not imply their
GUI or API is controlled by this server. Source interpretation, visual inspection,
missing manufacturer facts and engineering decisions still require the host AI
or a reviewer; they are not silently approved by tool success.

## Executed contract gate

`python scripts/check_mcp_contract.py --out runs/mcp-contract.json` reuses SDK
1.30.0 and Python AST inspection. It compares the actual tool catalogue with
source declarations and all 39 fixed worker operations, checks top-level schema
and known host-runtime exclusions, and actually submits an unknown-field call
to each tool to confirm rejection before dispatch. The single direct tool,
bsa_save_json, only saves fresh declarative JSON; domain validation is downstream.
The gate executes no valid engineering call or native engine and proves no UI
connection. It passed locally in the existing core-plus-network profile and is
now part of core CI; its new remote execution remains to be observed.

Full engineering executions keep their separate evidence: USABILITY_ACCEPTANCE.md,
REAL_PROJECT_REVISION.md and domain guides. Whole-repository regression is still
running at this checkpoint; no all-tests-passed claim is made.
