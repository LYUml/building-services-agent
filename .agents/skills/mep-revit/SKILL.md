---
name: mep-revit
description: Develop and validate native Revit MEP adapters, inspect saved pipe and fitting inventories, and diagnose model revisions. Use for RVT-specific workflows; native creation and saved reopening are still awaiting host verification.
---

# Revit MEP integration

Read [the native adapter guide](../../../adapters/revit/README.md) for invocation, request fields, supported observations and current evidence. Use [the Revit/MOOSAS review](../../../docs/REVIT_MOOSAS_DIRECTION.md) when choosing a bridge or analysis interface. Commands below run from the repository root.

## Select the actual capability

The C# adapter is compiled against the installed Revit 2027 API. Revit has discovered its registered read-only command, but actual invocation was blocked by Windows Code Integrity (events 3077/3033); no native inventory was produced. See [the load evidence](../../../docs/evidence/moosas-review/revit-native-policy-block.json). Do not repeat registration or switch loaders as a remedy for this policy failure. Revit Home startup, a successful build or a generated manifest does not establish model access. A bridge advertising pipe creation may only generate DirectShape cylinders; inspect actual native Pipe objects and connectors before calling it MEP authoring.

For a saved inventory, use the offline diagnostic directly. For live work, establish an available host entry point and active saved test-model identity first. Check current desktop availability before using UI; a pending desktop handoff is not permission to interrupt another task. Never close unsaved models or restart the user's application to make an integration load. A timeout after a write requires reading actual state before retrying.

The remaining product goal includes connected systems, analysis, schedules, drawings and saved reopening. An isolated pipe or diagnostic report is not a substitute for those deliverables. If an adapter is missing, implement or verify the required capability rather than silently simplifying the assignment.

## Read and diagnose

`scripts/inspect_revit.ps1` checks installation metadata. `scripts/prepare_revit_addin.ps1` prepares a local manifest/request; it does not install or execute it. The C# `InventoryCommand` requires the matching saved repository-local RVT without unsaved changes, and creates a new JSON report. Use its current output schema: the older Python/Dynamo inventory lacks newer fitting, provenance and revision fields.

```powershell
.venv/Scripts/python -m bsa.revit_connectivity --inventory runs/<capture>/inventory.json --model runs/<model>/test.rvt --tolerance-m <declared-metres> --out runs/<new-check>/diagnosis.json
```

Choose and record a diagnostic tolerance appropriate to the comparison; it is not a regulation or manufacturer's installation allowance. The diagnostic binds the inventory to saved-model bytes. It checks both directions of each reference, physical flags, domains, endpoint positions and original creation intent. A matching file hash does not prove native execution, authentic measurements or engineering validity.

Inspect `issues`, `pending`, `observed_open_ports`, `revision_checks` and the explicit scope. Missing equipment/accessory targets and absent provenance remain unresolved. Logical connections do not prove physical joins. Coincident connector origins do not establish flow paths inside a fitting. Open ends require sourced terminal intent; do not invent caps, outlets or loads to clear them.

Workflow kind `revit_inventory_check` takes `inventory`, `model` and `tolerance_m`. Put its ID in downstream `requires_pass`. Its status is fail or pending until broader acceptance exists; exit code 2 is expected for unresolved checks. Use `bsa.workflow_status` to diagnose dependencies, not to overwrite outcomes. Preserving unresolved requirements is essential, but do not make every future Revit task depend on this deliberately incomplete prototype when a different verified adapter can meet the requirement.

## Author and revise

`NativePipes.Create` currently creates one straight native pipe in a valid Revit API context using explicitly supplied type, system-type, level, coordinates, diameter and source declaration. It rejects active-document mismatches and pre-existing edits, verifies readback and rolls back failures. It does not connect fittings, save the model or create sheets. Do not invoke against the completed coursework.

Creation provenance is written inside the same transaction using Extensible Storage. It is historical intent, not proof of current dimensions or source accuracy; the schema's hash is not authentication. Inventory compares current endpoints, diameter, length and type/system/level IDs with that intent. An intentional design revision requires new source-backed evidence and fresh downstream calculations; do not edit history or waive a difference simply because the new geometry looks plausible.

Before presenting native creation as verified, execute positive and invalid-input cases in a new test RVT, verify rollback, save/reopen, read native objects and provenance again, and inspect the actual required sheets/exports. Add joined/unjoined controls for a connected system. Existing unit tests use synthetic observations and cannot prove any of these host behaviors.

## Engineering and delivery

Bind measured geometry and stable native IDs to the appropriate existing calculation adapter, retaining missing boundary conditions, equipment curves and source parameters. Revit's nominal diameter is not automatically the hydraulic internal diameter; family/type identity alone is not a product rating. Preserve thermal versus electrical quantities and actual route lengths.

Use [mep-regulations](../mep-regulations/SKILL.md) for the selected jurisdiction and edition, and [mep-delivery-check](../mep-delivery-check/SKILL.md) for full requirement review. Neither successful Revit creation nor an IFC export establishes Hong Kong conformity or accepted DWG/PDF delivery.
