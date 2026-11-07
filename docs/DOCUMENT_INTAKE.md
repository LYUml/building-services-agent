# Document intake and OCR

```powershell
.venv/Scripts/python -m pip install -e ".[documents]"
.venv/Scripts/python -m bsa.workflow intake path/to/brief.pdf --out runs/intake.json
.venv/Scripts/python -m bsa.workflow intake path/to/brief.docx --out runs/word-intake.json
```

PDF passages retain 1-based page and extracted line ranges. Line ranges refer to extraction output, not a guaranteed printed reading order. Word paragraphs retain package part, XML path (including table row/cell) and logical block index; no invented Word page numbers. Main body, tables, headers, footers, footnotes, endnotes and comments are read. Images, cached fields, automatic numbering, equations and layout-sensitive content produce explicit review issues. Empty text, missing PDF page text and unresolved Word tracked changes block planning. Intake saves the diagnostic result even when blocked and exits 2.

Plan `document_review` maps every extraction review issue ID to a specific source-inspection note. `validate` rejects unacknowledged review issues and any blocking issue. A nonempty note is a recorded assertion, not machine proof of inspection. The host AI must actually inspect the source, including tables and figures, and add omitted requirements before authoring project data. Quotes are matched to extracted content; this is traceability, not semantic accuracy verification.

## Offline OCR

```powershell
.venv/Scripts/python -m pip install -e ".[ocr]"
.venv/Scripts/python -m bsa.ocr path/to/brief.pdf --out runs/ocr --pdftoppm path/to/pdftoppm.exe
.venv/Scripts/python -m bsa.workflow intake path/to/brief.pdf --ocr runs/ocr/ocr.json --out runs/ocr-intake.json
```

Requires local Poppler pdftoppm (or found on PATH). Recognition uses pinned RapidOCR ONNX Runtime with bundled detection/recognition/classification models; no remote inference service or runtime model download is used. Every PDF page is rasterized at 180 DPI. Sidecar records model checksums, renderer checksum, package versions, raw text, confidence, pixel quadrilaterals, image hashes and source PDF hash. Model threshold is 0.1 to retain more uncertain text; detection can still miss text entirely. Confidence is not a calibrated correctness guarantee.

OCR supplements pages that had no extractable text. Existing machine-readable pages retain their original extraction; figures and mixed text/image requirements on those pages still need visual inspection. Empty OCR pages remain blocked. Equations, wiring topology, symbol semantics and table relationships are not inferred from OCR.

For a plan with OCR, put the sidecar in the plan directory tree and specify `ocr` (relative path), `ocr_sha256` and the required `document_review` notes. Every page image must remain present under the sidecar directory with its recorded hash. Workflow execution includes the sidecar and page images in input integrity checks. A changed source, sidecar or image invalidates its bindings. Hashes do not prove that an externally authored sidecar is honest.

## Evidence

The existing synthetic AutoCAD output had no extractable text. Offline OCR recognized three label regions, but one included a circle symbol and some slashes became fullwidth. The agent inspected the rendered page and retained the raw errors, leaving transcription acceptance pending. See docs/evidence/document-intake. This is an OCR integration test, not proof of general drawing interpretation or Chinese/handwritten/formula recognition accuracy. Chinese text retention is covered by a Word parser fixture, not a Chinese OCR benchmark.
