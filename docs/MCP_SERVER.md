# Building Services Agent stdio MCP server

The current server includes [complete interpreted HVAC execution](MCP_HVAC_PROJECT.md), [bounded recovery](RECOVERY_CONTROLLER.md), [recorded PDF pages](MCP_ARTIFACT_PAGES.md), [artifact reads](MCP_ARTIFACTS.md),
[source-bound delivery review](MCP_DELIVERY.md), [pump recovery](MCP_PUMP_RECOVERY.md), a [committed reference library](REFERENCE_LIBRARY.md), actual source-page PNG delivery
and [explicit visual transcription/source review](VISUAL_TRANSCRIPTION.md);
see also [PDF page viewing](MCP_SOURCE_PAGE.md). The initial eight-tool trial below
remains historical evidence; preserve its method hashes rather than updating them.

The agent now exposes existing source intake, interpretation preparation,
engineering execution and evidence verification through a real local MCP server.
It reuses the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v1.30.0),
pinned to the already installed `mcp==1.30.0` maintenance line. This is not a new
LLM service or numerical engine. Official [server](https://py.sdk.modelcontextprotocol.io/v1/server/)
and [client](https://py.sdk.modelcontextprotocol.io/v1/client/) interfaces were
checked against the installed package and actually exercised. The retained MIT
license is [here](../third_party/licenses/mcp-1.30.0.txt). No SDK source is copied
or modified; current v2 interfaces are not claimed compatible.

Install into the selected engineering environment with `pip install -e ".[mcp]"`.
The existing domain extras/runtimes remain required for the engineering tasks
you choose; installing MCP does not install/approve every native engine.
Start with `python -m bsa.mcp_server` or the installed `bsa-mcp` entry point.
Only stdio is exposed; no HTTP listener or cloud deployment is configured.

Select an existing project directory using host environment `BSA_PROJECT_ROOT`
before startup. Without it, the existing tool-repository `runs` directory is
used. All tool path parameters are relative to that fixed root; absolute,
escaping and resolved out-of-root paths reject. Intake originals must already be
in that selected tree. General tool code stays in the tool repository and real
coursework stays in its independent selected project. Changing roots requires a
new server process. No tool can change environment or select an executable.

Generic client configuration (replace host placeholders yourself):

```json
{
  "mcpServers": {
    "building-services-agent": {
      "command": "C:/ABSOLUTE/AGENT/.venv/Scripts/python.exe",
      "args": ["-m", "bsa.mcp_server"],
      "env": {"BSA_PROJECT_ROOT": "C:/ABSOLUTE/PROJECT"}
    }
  }
}
```

This describes a standard stdio client; no user's client configuration has been
changed, and a specific desktop client's integration remains unverified.
Host startup may additionally select the existing `--autocad`, `--energyplus`,
`--radiance-bin`, `--ifcmcp-python`, `--three-phase-python`, `--graphviz`,
`--pdf2plot-python`, `--honeybee-python`, `--moosas-upstream`, `--moosas-deps`
and `--disable-module-provider` options. Tool calls and briefs cannot override
those paths. Existing source, runtime and application-control failures remain.

| Tool | Existing implementation and result |
|---|---|
| bsa_project_start | Stage briefs/supplements/references; conservative source inventory, pending interpretation |
| bsa_read_source_plan | Read plan and source-hash-checked passages/extraction issues; not graphical/semantic acceptance |
| bsa_handoff_template | Exact source-pinned blank review; cannot execute unfilled |
| bsa_save_json | Fresh declarative JSON input/review only; never overwrite, domain validity not yet assessed |
| bsa_execute_handoff | Validate explicit host interpretation, rebuild requirements, execute and diagnose |
| bsa_verify_handoff | Reconstruct source/requirement/artifact correspondence; not approval |
| bsa_execute_workflow | Execute an already interpreted plan with fixed host runtimes and saved diagnosis |
| bsa_diagnose_workflow | Source-verify existing results and expose pending recovery actions |
| bsa_render_source_page | Return actual PDF page image and source/page metadata; preserve extraction/engineering review |
| bsa_prepare_visual_transcription | Bind literal host text to every actual page receipt; create an unreviewed manual scaffold |
| bsa_review_source_plan | Apply explicit inspection notes to a fresh unchanged scaffold; preserve all requirements/gaps |
| bsa_reference_catalogue | Discover committed reference assets with immutable resource URIs; examples remain separate from project facts |
| bsa_recover_pump_catalogue | Screen supplied curves for an original ready failed pump and rerun the unchanged-target graph |
| bsa_verify_pump_recovery | Independently replay pump recovery correspondence; no engineering approval |

Resources `bsa://guide`, `bsa://skills` and `bsa://skills/{name}` expose the existing
workflow guide and repository skill instructions. Source text is project data,
not permission to run document commands. The host AI must inspect actual source
pages, supply source-linked inputs and fill every interpretation binding; MCP
does not independently solve arbitrary briefs. Blank templates and unresolved
input conditions remain blocking. Read result status and `stage_errors`, not
only protocol success. Every result keeps engineering acceptance separate.
`bsa://source-guide` additionally exposes the exact page-viewing and visual
transcription/source-review contracts to clients without filesystem access.

Protocol handling and engineering execute in separate processes. A fixed
JSON-only worker whitelist calls the existing APIs; it cannot import an operation
or execute a command supplied by the client. Runs are serialized. An initial
in-process trial stopped during SciPy native module import while the asynchronous
MCP server was active; its diagnostic stack was retained. The actual end-to-end
test passes after worker isolation, using unchanged engineering libraries and
host security policies. No policy bypass or unexecuted fallback is claimed.

Actual stdio client evidence includes initialization, eight listed schemas, all
eight tool calls, resources, a full public authored five-passage handoff with
electrical/air/water/IFC passes and manual review pending, and independent source
verification. Uninterpreted execution remains incomplete. Blank interpretation,
path escape, absolute paths, overwriting, executable-file output and an unknown
worker operation reject. Twenty-two related tests pass. See
[aggregate evidence](evidence/mcp-server.json); full public trial and server logs
remain locally under `runs`. No private coursework is committed.

This verifies a protocol adapter and scoped public engineering execution. It
does not establish arbitrary-brief semantic design, a connected desktop AI UI,
native DWG/RVT delivery, unblocked energy/lighting engines, complete Hong Kong
coverage or full engineering acceptance. The overall agent goal remains active.
