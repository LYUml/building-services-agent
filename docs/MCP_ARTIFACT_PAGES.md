# Inspect recorded PDF deliverables through MCP

Use bsa_artifact_index to obtain a recorded PDF path and workflow_sha256.
Call bsa_render_artifact_page(plan,out,artifact,workflow_sha256,page,target).
The page is one-based; target must be fresh inside the host-selected project.
Optional max_side is 512..2560 pixels, default 2048. Host startup fixes pdftoppm.

The adapter reuses source-bound delivery.context/workflow verification before
and after rendering, relative_file for confinement, and source_page.run for
Poppler rendering and renderer/source/page hashes. It rejects unrecorded or
non-PDF files, stale workflow identity and changed evidence. It returns standard
MCP ImageContent plus metadata and saves page.png, original page.json and an
artifact-page.json adding workflow/artifact identity. No manifest is rewritten.

Actually inspect the returned page; rendering does not clear any review gate.
Record observations and original source/image hashes separately. To use the
existing delivery review attachment contract, choose a fresh target inside the
workflow directory and cite its recorded PDF source; added supplemental files
do not become original artifacts or replace the immutable manifest. Out-of-run
previews can be retained as observations but are not delivery attachments.
A raster page is not proof of print scale, native reopening or design approval.

No new engine, dependency or PDF authoring system is added. See MCP_ARTIFACTS.md,
MCP_SOURCE_PAGE.md and DELIVERY_REVIEW.md for underlying limits.

## Actual native workflow trial

A fresh public coupled source handoff generated the original two-segment
schematic using isolated AutoCAD Core Console. Eight engineering tasks passed;
final manual review remained pending. The saved DWG reopened with eight model
entities and six IFC-linked entities reconciled. The existing vector reference
check measured 49.9957 mm for a declared 50 mm, 1:50 reference.

A real SDK stdio client audited that workflow, rendered the recorded native PDF,
and received exactly the saved PNG bytes. It rejected traversal/unrecorded file,
wrong workflow hash, page 999 and an existing output target. The one actual PNG
was inspected: labels, leaders and source/scope notes were legible without
observed clipping or overlap. The PDF parser retains the original duplicate
PageMode warning; neither PDF nor workflow was rewritten to remove it.
The observations apply to this synthetic schematic only, not installation or
whole-agent acceptance. Evidence: evidence/mcp-artifact-pages.json.

Ten actual MCP/source-page tests passed, zero skips, 69.202 seconds. The public
PDF-workflow test requires explicit BSA_MCP_ARTIFACT_PLAN, BSA_MCP_ARTIFACT_RUN
and fresh BSA_MCP_ARTIFACT_PREVIEW; these were supplied for this run.
