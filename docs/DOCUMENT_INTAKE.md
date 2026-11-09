# Document intake and OCR

```powershell
.venv/Scripts/python -m pip install -e ".[documents]"
.venv/Scripts/python -m bsa.workflow intake path/to/brief.pdf --out runs/intake.json
.venv/Scripts/python -m bsa.workflow intake path/to/brief.docx --out runs/word-intake.json
```

PDF passages retain 1-based page and extracted line ranges. Line ranges refer to extraction output, not a guaranteed printed reading order. Word paragraphs retain package part, XML path (including table row/cell) and logical block index; no invented Word page numbers. Main body, tables, headers, footers, footnotes, endnotes and comments are read. Images, cached fields, automatic numbering, equations and layout-sensitive content produce explicit review issues. Empty text, missing PDF page text and unresolved Word tracked changes block planning. Intake saves the diagnostic result even when blocked and exits 2.

Plan `document_review` maps every extraction review issue ID to a specific source-inspection note. `validate` rejects unacknowledged review issues and any blocking issue. A nonempty note is a recorded assertion, not machine proof of inspection. The host AI must actually inspect the source, including tables and figures, and add omitted requirements before authoring project data. Quotes are matched to extracted content; this is traceability, not semantic accuracy verification.

## Conservative plan bootstrap

`python -m bsa.workflow_draft project/brief.md --supplement project/rubric.md --out project/plan.json` creates a new blocked interpretation scaffold using the existing extractor and workflow schema. Optional --ocr applies to the primary source. All sources must lie under the plan directory; originals are not copied or modified. Every extracted paragraph is retained as a full quote and a provisional requirement with a manual task and source-cited unresolved interpretation issue. No paragraphs are silently classified as context. Exit 2 explicitly retains pending interpretation.

The agent must inspect originals, split compound requirements, identify units/missing inputs and applicability, choose verified adapters and author actual acceptance criteria. The draft is not semantic requirement extraction or an engineering plan ready for execution. Unknown figure/table content is not invented: extraction issues are returned and document_review stays empty, so existing validation gates reject unreviewed or blocking sources. A wholly empty extraction creates no plan. Run provenance and delivery checks prevent a pending interpretation issue being cleared by a reviewer pass assertion. Removing issues remains a plan-author decision requiring actual evidence; the tool does not certify that decision.

## Offline OCR

Nested Word text-box paragraphs are extracted separately with their actual XML paths, rather than concatenated into the enclosing paragraph. Package traversal order is not rendered reading order; embedded-content and layout review remain required. This correction can change passage IDs/text for previously indexed text-box documents: regenerate intake and re-author/review their source-bound plans instead of reusing old quotes or locators.

```powershell
.venv/Scripts/python -m pip install -e ".[ocr]"
.venv/Scripts/python -m bsa.ocr path/to/brief.pdf --out runs/ocr --pdftoppm path/to/pdftoppm.exe
.venv/Scripts/python -m bsa.workflow intake path/to/brief.pdf --ocr runs/ocr/ocr.json --out runs/ocr-intake.json
```

Requires local Poppler pdftoppm (or found on PATH). Recognition uses pinned RapidOCR ONNX Runtime with bundled detection/recognition/classification models; no remote inference service or runtime model download is used. Every PDF page is rasterized at 180 DPI. Sidecar records model checksums, renderer checksum, package versions, raw text, confidence, pixel quadrilaterals, image hashes and source PDF hash. Model threshold is 0.1 to retain more uncertain text; detection can still miss text entirely. Confidence is not a calibrated correctness guarantee.

OCR supplements pages that had no extractable text. Existing machine-readable pages retain their original extraction; figures and mixed text/image requirements on those pages still need visual inspection. Empty OCR pages remain blocked. Equations, wiring topology, symbol semantics and table relationships are not inferred from OCR.

For a plan with OCR, put the sidecar in the plan directory tree and specify `ocr` (relative path), `ocr_sha256` and the required `document_review` notes. Every page image must remain present under the sidecar directory with its recorded hash. Workflow execution includes the sidecar and page images in input integrity checks. A changed source, sidecar or image invalidates its bindings. Hashes do not prove that an externally authored sidecar is honest.

## Multiple source documents

Keep the task brief, marking rubric and requirement-bearing appendices under the same project directory. Index them together:

```powershell
.venv/Scripts/python -m bsa.workflow intake project/brief.pdf --supplement project/rubric.docx --supplement project/appendix.md --out runs/project-intake.json
```

In the source-linked plan, retain the primary `brief`/`brief_sha256` and add `supplemental_briefs`, an ordered list of objects with `brief` and `brief_sha256`. Paths are relative to the plan directory and must stay inside it. Each supplemental entry may also declare its own `ocr` and `ocr_sha256` using the existing sidecar contract. CLI `--ocr` applies to the primary document; to index supplementary scans with OCR, use the plan contract and `plan_documents`, not an invented transcription. The intake CLI's supplemental paths must be inside the primary brief directory. Intake emits their relative paths/hashes; review them relative to the eventual plan location rather than copying paths blindly.

The primary document retains `P001`/`I001` IDs. The second document uses `D002:P001`/`D002:I001`, and so on in declaration order. With supplements present, passage locators include `source_document` and `source_sha256`; Word/PDF-specific locators remain intact. Classify every document's passages and review every issue. Empty or blocked supplementary content blocks planning. Duplicate document paths and modified source bytes are rejected, and all declared documents/OCR images enter workflow integrity checks and delivery-review binding.

Declaring the source list is still the agent's responsibility: the tool cannot detect an undisclosed appendix, decide whether two requirements conflict, or prove that a paragraph classified as context contains no requirement. Resolve conflicts using the actual assignment instructions; do not silently select the more convenient value. Reordering documents changes supplemental IDs, so regenerate intake and review the plan when changing the list.

The existing synthetic AutoCAD output had no extractable text. Offline OCR recognized three label regions, but one included a circle symbol and some slashes became fullwidth. The agent inspected the rendered page and retained the raw errors, leaving transcription acceptance pending. See docs/evidence/document-intake. This is an OCR integration test, not proof of general drawing interpretation or Chinese/handwritten/formula recognition accuracy. Chinese text retention is covered by a Word parser fixture, not a Chinese OCR benchmark.

Public real-brief intake: benchmarks/mit-4401-2018 now pins five official educational PDFs with separate attribution/CC-BY-NC-SA material notices, 21 preliminary obligation groups and classified facts/decisions/gaps. Existing document extraction/workflow_draft staged 41 interpretation tasks and 29 unacknowledged PDF layout/annotation reviews. Actual source-hash tampering and unreviewed execution controls reject. Only five selected pages have visual review; no models/simulation answers or completed independent designs are claimed. Reuses existing intake engines, no new dependency. See benchmark README and docs/evidence/document-intake/public-course-benchmark.json.

Public course source QA: all 26 pages and annotation destinations were inspected, with 29 source-specific notes in benchmarks/mit-4401-2018/source-review.json. Reviewed-byte/issue/context-text guards permit only seven boilerplate context dispositions; 34 technical interpretation blockers remain. Actual unified CLI produces pending diagnosis and delivery-review without engineering acceptance; two source-loss controls pass. Pinned official archive inventory (305 files) contains matching five PDFs but no referenced GH/model/weather/workbook files; absence is limited to that archive. See archive-review.json and docs/evidence/document-intake/public-course-review.json.
