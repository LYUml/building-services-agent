# Source-pinned terminal throw lookup


Catalogues may now declare `source_document` as a relative original-PDF path
alongside `source_sha256`. The adapter checks that file before output and after
lookup,records it in inputs and reports original_document_pinned. Workflow input
discovery includes it and rejects source PDFs outside the plan directory tree.
Missing/changed bytes reject;without that optional field,the legacy JSON-only
path remains available and reports original_document_pinned:false.
This pins original bytes;it does not prove manufacturer authenticity,correct
transcription,selected installation conditions or ADPI applicability.

Actual project execution in its coursework workspace binds an inspected9row
manufacturer table and independently reconciles640direction/load lookup cases.
Native save/reopen and the actual plot are reviewed separately. The reference
lecture's product-family typo is retained and distinguished from the primary
brief/manufacturer family rather than silently normalized. Only scoped source/
configuration/interpolation requirements receive manual review passes;physical
lengths,room loads,ADPI and installation remain unresolved. See
[evidence](evidence/terminal-original-source.json).


Run `python -m bsa.terminal_throw <project.json> --out <new-directory>`.
The adapter reuses fluids 1.3.1 piecewise-linear interpolation, with explicit
range checks instead of upstream endpoint clamping. It computes maximum and
turndown flow throw and T0.25/L for each supplied direction.

The project contains `catalogue` (relative to the project), `catalogue_sha256`,
an explicit `basis` statement, numeric `turndown` in (0, 1], and a nonempty
`terminals` array. Each terminal has a unique `id`, `maximum_flow_L_s`, and
`characteristic_lengths_m`, a mapping from direction names to positive lengths.
The catalogue contains `rows`, each with positive `flow_L_s` and `T025_m`;
flow must strictly increase. Units are litres/second and metres.

The saved `terminal-results.json` records input hashes, interpolation brackets,
the basis statement and every out-of-range case. Exit 0 means the bounded
lookups executed within the catalogue; exit 2 means one or more lookups are
outside its range. Neither exit establishes ADPI or design acceptance. Invalid
input or a changed catalogue raises an error before creating output. Existing
output directories cannot be reused.

The hash authenticates the reviewed JSON bytes, not the transcription against
the manufacturer's original document. Review the original document separately,
including product size, mounting, test conditions and applicability. Supplied
characteristic lengths and load basis remain caller-reviewed inputs. The tool
does not infer diffuser class, ADPI, pressure loss, noise or regulatory compliance.

Verification: seven terminal tests cover interpolation, range rejection,
invalid numerical inputs, changed catalogue, saved results, duplicate IDs,
missing directions and output reuse. An actual private assignment run processed
80 terminals in four directions at maximum and minimum flow (640 lookups), all
within the selected reviewed table. ADPI and design acceptance remain false.
Private coursework and manufacturer documents are not distributed here.

## Unified workflow

Register a task with `kind: "terminal_throw"` and `project: "project.json"`.
The plan inventories both the project and its hash-pinned catalogue, plus the
adapter module. Catalogue paths must be relative and stay within the plan root.
A successful lookup task means only bounded interpolation; out-of-range cases
fail the task and block tasks declaring `requires_pass`. Preserve separate
source/applicability and ADPI review requirements.

Ten terminal tests plus eight existing workflow tests pass. Actual private
assignment execution retains all 14 original interpretation tasks as pending
while the added 80-terminal lookup task passes; no coursework requirement is
silently removed or declared accepted by this integration.

Criterion applicability needs a separate edition/product/load/geometry basis; see ADPI_BASIS.md. Official 2015 and 2023 source review does not justify silently reusing a generic course interval. No new ADPI acceptance is implemented.
