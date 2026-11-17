# Common engineering data: first executed slice

This is the first additive slice of the2026-11-18 modular/data goal. Existing
module request/result contracts and domain engines remain authoritative. It is
not yet a complete editable cross-discipline project model.

## Boundaries and reuse

`engineering_data.model` owns common identity/relationship validation;
`quantities` owns an explicit bounded exchange-unit table; `module_bridge`
independently verifies existing module producers and maps their data; `report`
is a consumer of the same model. CLI is thin and lazily imports the bridge.
No solver is copied, no new dependency is introduced. Validation reuses pinned
jsonschema4.26.0, source reading/workspace guards and existing provider replays.
The unit table is not a general unit-expression parser or physical method.

The initial mappings cover classified air allocation and conditional single-phase
circuits. They preserve original provider acceptance, pending/numerical checks,
geometry limitations and a hash-bound workspace-relative producer reference.
Original provider artifacts remain available; selected common fields are not
advertised as a lossless replacement for every domain field.

IDs derive from explicit project ID, entity kind and original source ID, not
row order, scenario name or output location. They remain stable across quantity
changes when original identity stays stable. IDs currently assume source IDs
are unique within one project/entity kind; there is no automatic cross-model
merge or fuzzy entity matching. Conflicts need explicit source interpretation.
An exported supply relationship is not native installation/port acceptance.

Every quantity retains original value/unit, semantic dimension, explicit SI
value/unit, classification and JSON pointer into the original producer.
Thermal W, electrical real W and apparent VA remain distinct. Ambiguous kW,
nonfinite values, inconsistent conversions, duplicate IDs and dangling links
reject. Classification `declared` preserves an upstream declaration, not a
verified measured fact. This slice exports derived values; it does not authorize
editing calculated values as if they were source design inputs.

## Run and inspect

Install the existing `modules,spatial` extras for these two mappings, using a
dedicated environment. Air geometry needs Shapely; no Fluids/IFC/Manifold is
needed by this common-data profile. Other provider verification keeps its own
runtime requirements. The existing full-HVAC example fixture additionally
needs network for terminal lookup and duct sizing; do not confuse that fixture
with the smaller allocation data boundary.

```powershell
bsa engineering-data export PROJECT_MODULE_RESULT --out FRESH_COMMON_DIRECTORY
bsa engineering-data verify FRESH_COMMON_DIRECTORY
```

The standalone `python -m bsa.engineering_data` uses the same functions.
Input must be a supported, completed, independently verified module result.
Unavailable providers cannot become empty successful models. Completed numerical
failures stay fail in source flags. Output is restricted to tool runs or the
explicit host project, with three files: model.json, summary.html, receipt.json.

Verification checks exact file/method hashes and reconstructs the common model
from independently replayed producer evidence. It then reconstructs the report.
Rewriting all exported hashes cannot clear changed quantities, missing pending
items or a forged report. Original input/result bytes are not modified.

## Executed evidence

- 10 new controls pass, including the installed CLI, unit semantics, stable IDs,
  failure retention, workspace guards and coherent-hash forgery rejection.
- 31 current data/provider/CLI compatibility tests pass in the development profile.
- A new modules/spatial environment passes pip check and16data/electrical controls
  without Fluids, IfcOpenShell or Manifold. Its initial nine errors exposed a
  full-HVAC test-fixture dependency; the minimal new fixture is now independent,
  and original full-HVAC compatibility cases remain in the broader CI profile.
- The existing isolated actual HVAC layout maps80terminal rows to81entities and
 244quantities. Every terminal row and the load equal the prior native project
  result; three original source files remain unchanged. No course adoption.
- The actual common HTML first viewport was rendered in an isolated headless
  browser and viewed. Entire244row visual review is not claimed.
- Three fresh Windows imports of the common core show median0.0246s and
 28,463,104byte peak working set using the existing profiler harness. Import-only
  scope; no whole-host memory or improvement over a different workload claimed.

See evidence/engineering-data-first-slice.json and engineering-data-import.json.
The new Windows/Ubuntu CI profile is configured; its remote outcome is pending.

## Next steps, in the authorized order

1. Extend actual workflow/MCP consumption and explicit source design-input
   bindings/identity ownership. General spatial/system/port contracts remain to
   be integrated; no universal data editing or provider replacement is claimed.
2. Build source/version/page/applicability-aware knowledge retrieval, reusing
   existing source readers, reference library and rule packs.
3. Add change impact, invalidation and safe reuse using existing workflow gates
   and input/method hashes. No cache/resume claim from this export alone.
4. Validate with a different real project type and real output propagation;
   synthetic electrical controls are not that second real-project acceptance.

The previous release candidate remains a historical checkpoint. This new goal
is active, not complete. No formal release or user acceptance is asserted.
