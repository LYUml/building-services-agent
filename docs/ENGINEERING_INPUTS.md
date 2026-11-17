# Source parameter ownership

The new real recorded-lighting source-power adapter also executes this path;
see [lighting audit](LIGHTING_SOURCE_AUDIT.md) for188entities,4owned inputs,
actual typed10W change/report propagation and bounded project-knowledge proof.
Lighting has no result-cache eligibility or new photometric/geometry acceptance.
Earlier counts and domains below describe their historical checkpoints.

The common view now optionally includes a read-only `bsa.engineering-inputs/1`
catalogue beside calculated data. Existing calculators and their primary project
JSON remain authoritative; this does not grant permission to edit any parameter
or accept a source's measured/given claims without review.

Each parameter has a stable entity owner/name-based ID, original project JSON
pointer, raw value, original source-unit label, explicit semantic/SI units,
source classification and source-note pointer/text. Producer, original request
and primary project references are workspace-relative and hash-bound. Stable
IDs do not depend on array positions, current values or report row order.

Electrical mappings cover supply voltage, declared circuit design/rating/route
inputs and device load/power-factor/position fields. They do not mistake computed
current or voltage drop for input parameters. Existing bare fields are marked
declared; per-value measured/manufacturer classifications are not invented.
Air mappings preserve the original air_load classification/source records,
turndown and declared terminal coordinates. Bare source W/m2 is retained as
source_unit while the known cooling-allowance field gives it thermal semantics.
The shared unit table does not accept ambiguous bare W/m2 outside that mapping.

Coverage counts numeric leaves in the primary project JSON and lists every
unmapped pointer. Optional service-cell coordinates, for example, remain explicit
unmapped inputs, still retained/verified by the original geometry provider.
Referenced drawings, boundaries and PDFs are not falsely counted as primary-JSON
numeric coverage; their source pins remain in original producer evidence.

## Use through existing interfaces

```powershell
bsa engineering-data export MODULE_RESULT --include-inputs --out FRESH_BUNDLE
bsa engineering-data verify FRESH_BUNDLE
```

Or set `"include_inputs": true` on a source-bound `engineering_data` workflow
task. The existing MCP workflow/artifact tools execute and read that bundle.
No new tool, solver, runtime command or dependency is introduced.

Default export still writes bundle1's model.json/summary.html/receipt.json.
Opt-in bundle2 adds inputs.json and a source-input table in the same HTML report.
The calculated model schema stays unchanged. Both bundle formats are verified;
source/method changes still require fresh results, not patched historical hashes.
A task requesting inputs cannot pass after replacing its output with an otherwise
valid bundle1 and coherently rewriting outer hashes.

Verification independently replays the original provider and reconstructs input
ownership, exact values, units, classifications, notes, coverage and report.
Coherently rehashed changes to an input, measured/given claim, valid alternative
entity owner or source-unit label reject. This catalogue is an inspection and
future-change-location interface, not a generic JSON patch/revision engine.
Use existing reviewed source authoring and domain validation for new inputs;
retain original constraints, plans and engineering review.

## Executed results

- 9 source-input controls pass, including array reordering, explicit unmapped
  geometry and coherent-hash input/ownership/format-substitution controls.
- Current durable regression:74passed, zero skips, unchanged source and receipt
  independently verified. The36minimal-profile cases overlap this group and pass
  without Fluids/IFC/Manifold. The current two actual SDK cases cover old/new
  bundles, including reading source inputs through existing artifact tools.
- The historical actual HVAC integration replay performs6real MCP calls and
  exposes167primary-project numeric inputs:4originally given,2assumed and
 161declared. Every source classification is retained rather than authenticated.
  All244common-view quantities equal the prior replay;3original sources remain
  unchanged. The shared CLI also exports/verifies the167parameter bundle.
- The source-input HTML section was extracted verbatim from the actual report,
  rendered and its first viewport viewed. Entire report visual review/native CAD
  acceptance is not claimed; two text-fragment screenshot attempts were blank
  and are not counted as proof.

See [aggregate evidence](evidence/engineering-inputs.json). This new source
revision's Windows/Ubuntu data profiles pass at2e33930:36minimal tests,8retained
full-HVAC compatibility tests and2actual MCP cases per platform; all seven core
profile jobs succeed. See [CI evidence](evidence/engineering-inputs-ci.json).
Whole-repository regression and later goal phases remain separate. Knowledge retrieval,
change-impact/safe reuse and different-real-project acceptance are unfinished.
Existing water/spatial/etc. typed contracts and capabilities are preserved;
their broader common-view mappings are not implied by these two input adapters.
