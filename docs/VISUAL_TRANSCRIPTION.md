# Source-page viewing to explicit visual transcription

Two additional MCP tools bridge actual PDF page viewing to the existing source
requirements/handoff flow. The server now exposes eleven tools. They reuse the
source-page renderer, document extraction/review validator, workflow scaffold,
common requirements provider and engineering template. No vision/OCR service,
LLM backend, engineering engine or dependency is added.
The exact source-page/transcription guide is available to MCP clients through
`bsa://source-guide`; no local filesystem access is needed to read this contract.

1. Render and actually inspect every required source page with
   `bsa_render_source_page`.
2. Call `bsa_prepare_visual_transcription(source, pages, sidecar, target)` with
   explicit literal text and pixel regions, bound to the actual page receipts.
3. Read the resulting source plan and extraction issues. It remains
   `needs_source_review`; an engineering template cannot yet be prepared.
4. After actual source inspection, call
   `bsa_review_source_plan(plan, notes, out)` with a nonempty note for every
   extraction issue. Blocking extraction issues cannot be waived with notes.
5. The fresh reviewed manual plan remains `needs_interpretation`. Use the existing
   engineering template and provide actual sourced design inputs and any missing
   parameters before execution. Source inspection is not engineering approval.

The transcription is `bsa.visual-transcription/1`, with exactly `schema`,
`source_sha256` and `pages`. Each page has exactly `page`, `receipt` (relative to
the sidecar directory) and `lines`. Each line has exactly literal `text` and
`box` (four finite nonempty pixel-locator points inside the rendered image).
Every original PDF page must have one record, including explicitly empty pages.
The source PDF and receipts/images must be inside the sidecar/plan tree; outputs
are fresh distinct JSON files beside that tree. Originals are never overwritten.

There is deliberately no confidence score. Host visual transcription is not
machine OCR and cannot borrow an OCR score. Pixel regions are host visual
locators, not measured drawing lengths, inferred dimensions or model coordinates.
Copy actual symbols, decimals and units faithfully; do not fill unreadable text
with plausible engineering values. Pure graphical meaning and missing geometric
facts still require appropriate source inspection/engineering inputs.

Page receipts must match the exact PDF path/hash/page/count and saved PNG/hash/
dimensions, and retain current source/method/renderer evidence. Every source
page remains reviewable. Filled `no_text` issues become explicit visual
transcription review issues; native layout/annotation issues remain. Native text
and visual passages are preserved with independent IDs, page/pixel/image/receipt/
sidecar provenance and `transcription_method=host_visual_transcription`.
The existing plan's `ocr`/`ocr_sha256` fields carry this separately identified
sidecar for compatibility; this does not label the data as automated OCR.

The source-review adapter copies only the manual scaffold's explicit inspection
notes and original-plan ancestry into a fresh sibling JSON. All tasks, full
quotes, requirements, acceptance criteria and unresolved inputs remain identical.
Empty/missing notes, blocking extraction, already-reviewed or engineered plans
reject. The original scaffold is pinned as a planning record. Generic
interpretation gaps remain until an explicit engineering handoff; actual missing
survey/product/code facts cannot be removed by source-review notes.

Source files and renderer runtime evidence remain separate. An initial common
inventory trial correctly rejected the system renderer as an out-of-workspace
project input. The fix preserves the existing module path restrictions: system
renderer evidence remains in the page receipt and is checked during source
replay; it is not misclassified as project source. Actual common inventory and
verification now pass, and a changed-renderer control still rejects.

Actual stdio client execution reads a public rendered graphical fixture, supplies
an explicitly authored literal transcription, retains the blocked unreviewed
state, applies explicit inspection notes and produces an unfilled engineering
template. The original image/source hashes and all three requirements/generic
gaps survive; no physical dimensions or engineering tasks are invented. The same
session still executes the separate public four-domain engineering case with
manual review pending. Common requirements preserve the new locator type.
Thirty-four related tests pass with one existing explicit-input OCR test skipped.
Missing page, fabricated confidence field, invalid pixel region, changed PNG/
source receipt, missing review notes, altered transcription and renderer evidence
controls reject; a concurrent candidate is preserved if exclusive creation fails. See [executed evidence](evidence/visual-transcription.json).

This verifies an explicit host-authored source handoff, not automatic vision,
diagram-to-BIM, complete source transcription correctness or semantic design.
The renderer does not review its own output. A named desktop client's image/UI
integration, complete CAD/BIM/performance/regulatory delivery and full agent
acceptance remain unfinished. Existing upstream attribution applies unchanged.
