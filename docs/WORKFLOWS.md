# Requirements-to-tools orchestration

The host AI reads and interprets the user's brief. The deterministic workflow runner checks that the interpretation quotes the actual source and calls known engineering adapters. It does not invoke a hidden model API or claim arbitrary engineering language can be understood by keyword matching.

## Commands

```powershell
.venv/Scripts/python -m bsa.workflow intake examples/workflow-brief.md --out runs/intake.json
.venv/Scripts/python -m bsa.workflow validate examples/workflow-plan.json
.venv/Scripts/python -m bsa.workflow execute examples/workflow-plan.json --out runs/workflow --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe' --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python -m bsa.workflow verify runs/workflow
```

The sample contains an explicit manual review task. Execute therefore returns exit code 2 with a durable workflow report: three technical tasks succeeded but manual review remains pending. This is intentional. Do not suppress the pending task to obtain a successful exit code.

## Plan contract

See examples/workflow-plan.json. Version 1 requires:

- `brief`: relative source path and `brief_sha256`: digest of the interpreted bytes.
- `passage_dispositions`: every source paragraph classified as requirement or context. The AI must review context classifications; validation cannot prove that a requirement was not misclassified.
- `requirements`: unique id, source passage id, exact source quote, task id and a complete acceptance description. Multiple requirements may cite a paragraph. Partial quotation alone is not evidence that the complete paragraph has been interpreted correctly.
- `tasks`: unique path-safe ids and one of electrical, energy, native_cad or manual. Electrical/energy tasks specify relative project JSON inside the plan directory. Native tasks depend on an earlier electrical task. No arbitrary shell commands or executable paths can be supplied in plan data; optional engine paths are explicit CLI arguments.

Source changes invalidate the brief digest. Escaping input paths, unknown adapters, uncovered paragraphs, fabricated quotations and unreferenced tasks are rejected before execution. Missing optional tools remain pending. Adapter exceptions are recorded as failures; later independent tasks can still run.

## Evidence and acceptance

`workflow.json` records input hashes, source line locators, task scopes, output evidence paths and task-artifact hashes. `index.html` summarizes the matrix. `verify` rehashes recorded inputs and task outputs, and detects missing or changed files. This is integrity checking, not a signed tamperproof ledger. It does not assess semantic correctness or hash its own report.

Task execution statuses pass/fail/pending are separate from requirement acceptance, which remains pending review. A task's success proves only the named adapter scope. For example, native conversion verifies circle/text entities and emits a PDF, but cannot prove arbitrary quoted layout requirements, print scale, visual quality or all electrical safety conditions.

Intake now reads UTF-8 Markdown/text, PDF and DOCX with explicit coverage/review gates; optional offline OCR supplies page-bound text for otherwise unreadable PDF pages. See DOCUMENT_INTAKE.md. General drawing-note semantics remain pending. CAD is limited to the supported overlay, energy to two synthetic thermal zones/design days. Broad MEP authoring, hydraulic analysis and full engineering acceptance remain outstanding.
