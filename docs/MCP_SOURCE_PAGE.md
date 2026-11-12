# Actual PDF source pages through MCP

The local MCP server now returns an actual PNG page and structured source/page
metadata with `bsa_render_source_page`. It reuses the existing Poppler invocation
from the OCR adapter; the OCR path still uses its original 180 dpi profile.
No PDF is edited and no OCR, diagram interpretation or engineering solver is
introduced by rendering. The existing pinned Pillow13.0.0/pypdf7.0.0 dependencies
are included in the MCP extra; the external Poppler binary is not redistributed.

Configure the trusted host renderer at process startup:

```powershell
python -m bsa.mcp_server --pdftoppm C:/APPROVED/POPPLER/pdftoppm.exe
```

The tool arguments are `source` (project-relative PDF), `page` (strict one-based
integer), `out` (fresh project-relative folder), and optional `max_side` (strict
512–2560 pixels, default2048). Renderer paths cannot come from calls or briefs.
Missing runtime, encrypted source, page beyond the actual page count, invalid
pixel bounds or existing output rejects. Errors retain renderer diagnostics
when execution fails; source/method/renderer changes prevent a successful receipt.
Existing root/path/source-preservation checks remain in force.

The native full MediaBox and rotation are rendered within the requested pixel
bound. Metadata keeps source PDF/hash, actual page/count, PDF coordinate box,
UserUnit, rotation, renderer/method hashes, PNG/hash and image size. This is a
visual preview: pixel dimensions do not establish a surveyed length or plotting
scale. It is not a cropped region, full-resolution zoom tool, OCR transcription
or geometric authoring. Inspect original documents and higher-detail views when
required instead of guessing unreadable dimensions.

The MCP result contains both `ImageContent` and the same structured metadata.
Vision-capable clients can view the actual page instead of relying solely on
extracted text. A client's ability to consume/display images must still be
verified separately. `visual_review=not_performed_by_renderer`,
`extraction_review_cleared=false` and `design_accepted=false` remain explicit.
Rendering or successful transport never acknowledges an extraction issue, binds
a design input, accepts a regulation or clears a source review gate.

Actual stdio trial initializes nine tools, renders an existing public graphical
PDF, receives the PNG and compares decoded bytes/hash exactly with the saved
page. The returned image was actually inspected. The original graphical intake
remains `needs_source_review` and byte-identical after viewing. Invalid page
does not create output. The existing five-passage engineering chain also executes
over the same MCP session, retaining manual review and all original obligations.
Independent handoff verification passes. Twenty-three related tests pass with
one existing explicit-input OCR test skipped; no new OCR execution is claimed.
Legacy 180 dpi rendering, missing runtime, bounds, mid-render source change and
retained failure-log controls are exercised. See
[evidence](evidence/mcp-source-page.json).

The source fixture is a public synthetic diagram. This verifies image transport
and source preservation, not arbitrary coursework understanding, automated
dimension extraction or full building-services acceptance. Existing upstream
Poppler/Pillow/pypdf/MCP attribution applies; no new third-party engine is copied.
