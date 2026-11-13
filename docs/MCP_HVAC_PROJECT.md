# Complete interpreted HVAC projects through MCP

An AI client can now prepare and run the existing whole HVAC package through the
local MCP interface, then inspect its recorded outputs. This reuses hvac_project,
hvac_package, source-bound workflow verification and the pinned official MCP SDK
1.30.0. There is no new solver, drawing engine or dependency.

Start the host with BSA_PROJECT_ROOT and explicit --report-font, --autocad where
native output is required, and --pdftoppm for page viewing. Client calls cannot
choose runtimes or change the root. A missing font stops before package creation.

1. Call bsa_prepare_hvac_project with an already-reviewed plan, fresh configuration
   path, exact-plan requirements_result and original review settings/selectors.
   Source interpretation and missing project facts must already be explicit.
2. Call bsa_run_hvac_project with configuration and fresh out only. It executes
   the existing package and checks current configuration/source/method pins,
   receipt linkage, stage inputs, recorded artifacts and workflow correspondence.
3. Call bsa_inspect_hvac_project to audit again without executing. Read status,
   stage_errors and unresolved_tasks; tool success never approves the design.
4. Use the returned artifact inventory and existing bsa_render_source_page to
   inspect report/drawing pages. Its source path is package out plus artifact
   path. Require returned source_sha256 to equal the inventoried PDF hash; actual
   image bytes are returned. Store previews outside the immutable package.
   The renderer alone does not perform engineering or visual review.
5. Existing bsa_artifact_index/read/render and delivery tools continue to inspect
   the nested workflow using the returned original plan/workflow paths (converted
   to paths relative to the fixed host root). Keep requirement/gap states intact.

Inventory paths use forward slashes on Windows as well as other hosts. Stage
errors and review_required/incomplete domain results remain visible rather than
being converted into a successful engineering result. Historical stale packages
are preserved; use existing source review/refresh preparation rather than editing
old pins. The inspector checks recorded evidence correspondence, not authenticated
provenance or complete statutory/physical acceptance.

The pinned SDK's default argument model ignores unknown fields. The server now
uses its public list_tools/call_tool interface to reject unknown top-level fields
before execution and advertises additionalProperties=false. Nested declarative
JSON data retain their own schema. This avoids silently accepting attempted
runtime overrides; official SDK source was inspected and was not modified.

An actual stdio client exercises preparation, full synthetic package generation,
read-only inspection, source-bound report PNG delivery, changed source/artifact
rejection, workspace confinement, no-overwrite and extra runtime-field rejection.
This is executed protocol/adapter evidence; the synthetic model is not a real
engineering design. Real coursework protocol evidence is recorded separately in
evidence/mcp-hvac-project.json. Named client UI configuration and arbitrary brief
autonomous design remain unverified.

## Executed real protocol

A real stdio client completed six calls: configuration preparation, full package
execution, read-only inspection, report first/last page retrieval and drawing
page retrieval. Inspection agrees exactly with the execution inventory. The run
has 49 recorded artifacts, 33 requirements and six unresolved inputs. Actual
native reopening reconciles 718 generated entities; report output has 24 pages
and 388 checked numeric rows. Stage errors are empty and status remains
review_required. Both PDF page contents match current public deliverables.

Only report pages 1/24 and full A1 were inspected in this protocol trial; previous
full visual review retains its separate evidence. Full engineering, ADPI, physical
installation, pressure/fan duty and jurisdiction acceptance stay unresolved.
The broader regression has 16 passes and one explicit prior-PDF-fixture skip;
new package report-page delivery executes rather than relying on that skipped
fixture. Long native/package calls may need a client timeout of several minutes.
After a timeout, inspect the actual live worker/job before starting another run;
a timeout alone does not establish that execution stopped.
