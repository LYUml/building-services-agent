# General drawing in the project workflow

The existing document author now participates in the source-bound project
executor. Task kind `drawing_document` takes only `id`, `kind`, `project`, optional
`requires_pass` and `description`. Its project must be a
`bsa.drawing-document/1` document; the other standalone drawing schemas are not
silently accepted here. This bounded task adds orchestration, not a CAD engine.

```powershell
bsa workflow examples/drawing-workflow-plan.json --out runs/my-project-drawing --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe" --review runs/my-project-drawing-review.json
```

Install `.[drawing]` for this CLI workflow, or `.[drawing,mcp]` for chat tools.
Use your actual AutoCAD path and fresh output/review names. The public example
contains source-linked synthetic requirements and the existing plan/system/
detail sheet. It is not a real building design. File references stay inside the
plan directory; executable paths come only from the host.

Execution pins the original document, author/reader/plotting method files and
the explicit AutoCAD executable. It saves/reopens the native DWG, independently
reconstructs editable entity correspondence and checks the actual PDF scale.
The workflow verifier invokes the same drawing inspection again; changing DXF
geometry cannot pass merely by rewriting file hashes in the receipts.
Missing runtime remains pending without a drawing folder. Failed source/guard
checks do not release later `requires_pass` tasks.

The example intentionally includes a separate manual review task. A normal
successful native execution therefore returns exit2, with the sheet passed,
review pending, both original requirements retained and `design_accepted=false`.
The CLI saves `workflow.json`, `index.html`, `diagnosis.json` and a separate
pending review JSON. In chat, use the existing `bsa_execute_workflow`,
`bsa_diagnose_workflow` and `bsa_delivery_template` tools with project-relative
paths. No new MCP tool is added; the actual existing desktop connection executed
the fixed worker route without a client restart.

## Executed checks

- A clean drawing/MCP installation executes the public workflow through the
  installed CLI: actual native sheet passes, manual review remains pending,
  two original requirements and a separate review are retained.
- The actual current desktop-chat MCP connection executes that same task chain,
  diagnoses it and creates the separate pending review. The real PDF pixels
  match the visually inspected standalone sheet.
- Five clean-environment workflow tests pass, including actual AutoCAD and a
  changed DXF with rewritten inner/outer hashes. Independent reconstruction
  rejects that forgery. A further actual MCP workflow/delivery test passes.
-45existing delivery,diagnosis,water/electrical-rule and spatial BIM/inlet/stub
  workflow tests pass after conditional verifier imports (315.703seconds).

The first clean full-workflow attempt exposed another unrelated IFC dependency
in delivery review. The existing per-kind verifiers now load only when their
corresponding task kind occurs; their checks and arguments are preserved for
relevant projects. Failed prior output is retained privately, not rewritten.
Current source/native evidence is in [the receipt](evidence/general-drawing-workflow.json).

This does not infer geometry or engineering decisions from an arbitrary brief,
accept installed construction, or certify regulatory conformity. Actual visual
observations remain separate from the workflow's numerical/native status.
