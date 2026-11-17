# Recorded lighting source audit

The modular/data path now executes on a second real discipline using existing
office lighting sources. This is a recorded-report power/area audit, not a new
photometric calculation or acceptance of the original coursework. Source
workspaces remain read-only; copied inputs and private evidence stay in ignored
runs. The current BSE3227 submission is unchanged.

## Executed chain

Existing DIALux toolkit CLI → thin lighting provider → module result → common
model/input catalogue → HTML report → checkpoint/typed change impact → new
calculation/report. Existing knowledge retrieval also indexes the verified
lighting inputs, retaining entity/parameter identity and original JSON pointer.
No new MCP tool, retrieval engine or photometric solver is introduced.

Provider `bsa.lighting-source-power` serves capability
`analysis.lighting.source-power-audit`, payload `bsa.lighting-source-audit/1`.
The existing `module_analysis` task precedes `engineering_data` with
`include_inputs: true`. An explicit project context must match both request IDs.
Request roles are exactly `project`, `layout`, `design`, `native_metrics`,
`native_report`, `area_evidence`. Each is a relative, hashed selected-workspace
source. `contracts/lighting-source-project-v1.json` defines the normalized input;
per-value role/pointer bindings are checked against the original JSON sources.
The source adapter expects the existing design/layout/report binding structure;
it is not a generic importer for arbitrary DIALux projects.

The host must provision `BSA_DIALUX_TOOLKIT_ROOT`, an existing absolute checkout
at `ade128b7ae446c6ea253776a5ead866280d6bf4a`, with its existing interpreter and
clean tracked files. The host documents profile supplies pypdf7.0.0. Source
documents cannot select commands/interpreters. The bridge invokes only the fixed
`report-read` CLI, verifies the explicit room header and maps its two adjacent
summary pages to physical pages of the original PDF. Missing configuration
returns unavailable; extraction/source failures cannot become empty success.
The upstream root has no identified license (NOASSERTION); no code is vendored
or redistributed. See REUSE_SURVEY.md and THIRD_PARTY.md.

## Real evidence

The actual42tool SDK session executes nine calls, including calculation,
diagnosis, checkpoint, impact, artifact reading and a pending delivery template.
The two immutable executions use the same project/scenario context to test a
copied-input revision. All five original selected source files stay unchanged.

| Quantity | Baseline | Copied-input revision |
| --- | ---: | ---: |
| Actual fixture count | 186 | 186 |
| Luminaire body input, W electrical | 4,278 | 4,278 |
| Declared auxiliary allowance, W electrical | 50 | 60 |
| Input budget, W electrical | 4,328 | 4,338 |
| Recorded gross area, m² | 1,042.1 | 1,042.1 |
| Annotation area, m² | 1,022 | 1,022 |
| Body density on recorded area, W/m² | 4.105172 | 4.105172 |
| Recorded native body density, W/m² | 4.11 | 4.11 |

Native density matches the calculated body value at its two displayed decimals.
Auxiliary allowance is separately declared, not silently included in the native
body density. Neither area basis is automatically adopted as a regulatory
internal area. The common model has188entities/197quantities and4owned source
parameters. The impact ledger identifies exactly one10W electrical change and
invalidates calculation, common report and review. This provider is deliberately
outside the numerical reuse whitelist; each new run executes its original path.
All3requirements remain pending review.

The real lighting input index is40,960bytes with4records. Default lookup excludes
project facts; explicit matching-context lookup finds the allowance's entity,
parameter and original `/auxiliary_allowance/value` pointer. It is a declared
project fact, not normative guidance or authenticated manufacturer evidence.

## Review and reproduction

Private local review entry:

* `runs/lighting-real-milestone/project-attempt2/scenario/analysis/analysis/audit.html`
* `runs/lighting-real-milestone/project-attempt2/scenario/data/summary.html`
* `runs/lighting-real-milestone/proof.json` and `knowledge-proof.json`
* `runs/lighting-source-regression` contains182passing selected controls and its
  independently verified durable receipt. A separate48-case existing module/MCP
  compatibility group also passes with zero skips and verified receipt
  (`runs/lighting-module-compatibility`). Total230selected cases; this is not
  whole-repository discovery.

Use the existing source-bound workflow/MCP operations with the selected study's
explicit host project/toolkit roots. `bsa workflow verify` and
`bsa engineering-data verify` reconstruct source evidence; changing source or
method bytes intentionally invalidates old receipts. Preserve the original
workflow/checkpoint before revising copied inputs. No original coursework file
needs editing. Public aggregate evidence omits source documents and identities.

Fresh provider imports load none of pypdf/IFC/NumPy/SciPy/Fluids/MCP. Three local
tracemalloc samples take0.150–0.174s and peak about6.04MB Python allocation.
This is import scope only, not native runtime RSS or a measured speedup. Actual
MCP execution takes about44s per run; evidence replay also costs time. A later [operation-scoped optimization](AUDIT_REPLAY.md) measures reduced replay
work with unchanged outputs and retained checks. These earlier timings describe
the initial integration only.

## Remaining boundaries

No fresh DIALux calculation, sparse-field coordinate correspondence, circuit
design, native CAD change or statutory acceptance is established. Existing
upstream coordinate readers reject the sparse-array case; their guards remain
unchanged. Recorded WP1 average640lx and Uo0.002 are not desk-task results; no
task compliance or explanation of the low WP1 value is inferred. Product watts
and allowance retain declared source status. CLI/source/interpreter pins do not
authenticate all installed transitive package contents. Full-goal knowledge
ownership refinement, audit-performance work and user acceptance remain open.
