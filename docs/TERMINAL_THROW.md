# Source-pinned terminal throw lookup

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
