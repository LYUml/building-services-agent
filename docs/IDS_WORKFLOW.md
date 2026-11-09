# Upstream IDS checks in delivery workflows

The `ids_check` workflow adapter runs pinned IfcTester 0.8.5 against either a declared saved IFC or an earlier supported IFC producer. It reuses upstream IDS interpretation. Install the optional `ids` dependency group first; see REUSE_SURVEY.md for attribution and standalone commands.

Example task fragments (inside a complete source-linked workflow plan):

```json
[
  {"id": "model", "kind": "bim", "project": "model.json"},
  {"id": "information", "kind": "ids_check", "ids": "requirements.ids", "depends_on": "model"},
  {"id": "drawing", "kind": "ifc_drawing", "depends_on": "model", "settings": "drawing-settings.json", "requires_pass": ["information"]}
]
```

Alternatively replace `depends_on` on the IDS task with `ifc: "saved.ifc"`. Exactly one input mode is allowed. The producer must be earlier and have a supported IFC artifact; a failed producer prevents IDS execution. Every task still needs a source-linked requirement under the ordinary workflow contract.

The IDS file and any explicit IFC enter the source hash inventory. For inherited models the adapter records the actual producer IFC path and hash; the workflow inventories generated artifacts. `python -m bsa.workflow verify <run>` detects subsequent input/artifact changes. The audit includes the native JSON report and engine log. Upstream exit code 0 is insufficient: the adapter requires a passing audit with nonzero specification and check counts. Failed information checks block tasks declaring `requires_pass`.

The gate is explicit, not automatically inferred for every drawing. A passing IDS check on one model does not validate another model used by a consumer. Review producer identities and require the other relevant physical, calculation and regulatory gates as well.

`examples/ids/pump-selection.ids` is a synthetic presence-only contract. It requires four provenance fields on at least one pump. It does **not** validate field truth, curve physics, product suitability, geometry or Hong Kong compliance. Even a passing workflow retains `design_accepted: false`.

## Executed regression evidence

`python -m unittest discover -s tests -p test_ids_workflow.py -v` exercises the real IfcTester CLI against freshly authored synthetic IFC: required fields present; four fields absent on an inherited model (native exit 0 but workflow failure); no applicable pump; blocked downstream execution; inherited input replacement rejection; and changed IDS detection. A separately injected upstream authoring failure verifies that IDS is not run against a failed producer. These fixtures are information-contract tests, not engineered pump selections.
