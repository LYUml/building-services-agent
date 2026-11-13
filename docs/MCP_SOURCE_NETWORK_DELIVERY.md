# Composed source-native delivery through MCP

The existing one-command source_network_delivery pipeline now has two fixed
MCP tools through the existing isolated worker and pinned MCP SDK1.30.0:

- bsa_run_native_network_delivery(source,out,scale=null)
- bsa_inspect_native_network_delivery(out)

The host starts the server with explicit BSA_PROJECT_ROOT and --autocad. Client
tools cannot choose executable paths or change the root. Missing host AutoCAD
stops before producer execution. Optional scale is a positive numeric composition
choice; physical source scale is not inferred. Source and output paths are
relative to the fixed project, and the existing producer requires fresh outputs.

Execution reuses verified source-native projection, deterministic review layout,
actual AutoCAD DWG save/reopen/export and fixed-scale PDF calibration. Inspection
independently replays source/native geometry, layout, native evidence and PDF
vector measurements. There is no new engine, runtime or dependency. The original
source model, requirements and earlier deliveries remain unchanged.

Compact summaries return product/requirement counts and the original pending
visual/engineering scope. Artifacts include delivery record, DWG and PDF with
absolute path, project_path, size and SHA256. project_path is directly usable by
bsa_render_source_page when the host also supplies --pdftoppm. Compare its returned
source_sha256 with the inspected PDF identity, then actually inspect the image.
Image delivery alone does not perform visual or physical engineering acceptance.
The inspector binds its summary to unchanged delivery-record bytes across replay.

Run and inspect calls may take several minutes because they replay source ancestry.
Use an adequate client read timeout. An observation timeout is not evidence that
a producer stopped; inspect its actual process before starting another producer.
Tool success preserves review_required, pressure_budget_complete=false and
design_accepted=false. The interface begins at already-reviewed native analysis;
arbitrary brief interpretation and complete engineering design remain unfinished.

The access gap was manual CLI handoff from the AI client. Existing package,
workflow, source-page and saved-request tools retain their original contracts.
No protected coursework models, drawings or publisher tables enter public code
snapshots; only safe aggregate execution evidence is published.

## Executed evidence

A real stdio client performs all three stages on BSE3227: fresh composed native
production, independent inspection and actual PDF-page image delivery. The first
two summaries agree exactly except the inspector's added integrity_pass=true.
All102 products and33 source requirements remain, DWG reopening and fixed-scale
PDF checks pass, and the returned PDF project_path directly renders through the
existing source-page tool. Returned source/image hashes match the inspected PDF
and stored image. The actual page is visually inspected for geometry coverage,
readable title/notes/reference and no clipping or overlap; producer visual pending
is preserved with a separate review receipt.

Six targeted and four existing source-handoff/recovery/package regressions pass;
both current runner receipts verify with no final-suite skips. Missing host
runtime, attempted runtime overrides, invalid scale and outside-project reads
reject without a new producer directory. Current MCP inventory has32 tools.
This does not establish named desktop-client UI setup, arbitrary brief design,
complete fitting/terminal/equipment losses or full jurisdiction/installation
acceptance. Private source/model/DWG/PDF/client records stay in the selected
coursework workspace. Safe aggregate evidence is in evidence/mcp-source-network-delivery.json.
