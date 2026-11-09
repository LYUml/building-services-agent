# Source-bound cable bend limits

The standalone bsa.cable_bend_limits command now compares supported saved circular cable bends with explicit declared product/installation requirements. It reuses the existing pinned IfcOpenShell/Manifold native reader and source-hash machinery. No new engineering engine, dependency or universal bend-radius table is introduced. Source interpretation, electrical cable selection, current rating, conductor/neutral/earth configuration, pulling forces, physical installation and complete regulatory conformity remain unverified.

## Why the source distinctions matter

The [official Nexans FNHP11AA003OMAA product page](https://www.nexans.com.au/en/products/Low-Voltage/Orange-Circulars/PVC/PVC-Circul24464/product~FNHP11AA003OMAA~.html), retrieved 2026-11-10, lists nominal diameter 15.1 mm, an installed minimum radius of 60 mm and a pulling-under-tension minimum of 91 mm. The page does not establish the radius measurement reference for this adapter. These product facts are research evidence, not a selection for the existing example or a Hong Kong suitability decision. The complete public HTML remains only in ignored local runs; the retained evidence records URL, source hash and scoped facts, without redistributing the page or a manufacturer catalogue.

The current synthetic cable model has a 20 mm envelope diameter. Deliberately attaching that product reference/source to a copy of the model does not make it correspond to the manufacturer's nominal diameter. Actual native execution rejects that comparison and separately records the unresolved radius reference. It does not infer inside/centreline meaning from a radius number, nor substitute the smaller installed limit for pulling conditions. See [executed counterexample](evidence/pandapower/cable-bend-limits.json).

## Input and native identity contract

A version-1 basis JSON has exact sources and bends dictionaries. Each source has relative path, SHA256, locator and kind (manufacturer, assumption, course_given, measured or design_target). All supported bends in the selected electrical system must have exactly one basis row; omitted or additional line IDs fail. Unsupported geometry already fails the native geometry reader. A no-bend case remains pending rather than manufacturing an all-clear result.

Each bend row declares product_reference, diameter_m, diameter_basis, condition, radius_reference, minimum_radius_m and source. Values are SI metres; null dimensions and explicit unknown enums remain unresolved. Diameter basis is nominal/maximum/unknown; condition is installed/during_installation_under_tension/unknown; radius reference is inside/centreline/unknown. There are no default factors or conditions. Product-appropriate source interpretation remains a review responsibility; merely labelling a local file manufacturer is not authenticity or applicability proof.

The native cable must carry BSA_CableSelection text properties ProductReference, SourceSHA256 and InstallationCondition matching the declared requirement. Missing identity/condition stays pending; conflicting declared/native values fail. These properties represent explicit authored intent, not proof that physical hardware was installed. Updating a native property changes IFC bytes; any model-derived study and release gates must deliberately use the revised model, not borrow the old model's pass.

Nominal mode assumes the round model envelope represents the stated nominal diameter, with a 1 micrometre numeric comparison tolerance. It does not validate manufacturing tolerances or padded envelopes. Maximum mode requires the model envelope to cover the sourced maximum diameter without undersize allowance; do not relabel a nominal value as a guaranteed maximum. Wider model envelopes are conservative for the supported inside-radius comparison. Neither mode proves clearance or product shape fidelity.

For a supported round bend, centreline radius is R and inside envelope radius is R-a, where a is the native envelope radius. Compare only the explicitly declared reference to its minimum. Unknown reference never becomes a centreline test. Pending facts cannot clear a failed/unevaluated requirement. The report retains numerical diagnostics, failures, pending reasons, source kind and exact input hashes; design_accepted and manufacturer_selection_verified always remain false.

## Run and verification

```powershell
.venv/Scripts/python -m bsa.cable_bend_limits examples/three-phase-bend/project.json --ifc runs/your-revised-cable-model/cables.ifc --binding runs/your-revised-cable-model/binding.json --basis examples/cable-bend-limits/limits.json --out runs/new-bend-limit-check
```

The example limits are synthetic. The generic geometry fixture lacks the required selection metadata, so it cannot be advertised as passing this check without a deliberate sourced model revision. The module is read-only; it never adds selection properties or alters a model. Pass means the declared scoped comparison passed; fail/pending exits nonzero. The command is not yet registered as a workflow task, and a radius pass does not select a conductor or establish manufacturer/Hong Kong approval.

Ten tests pass, covering inside versus centreline distinction, installed-versus-pulling mismatch, maximum/nominal diameter behavior, missing native metadata, unknown datum, source changes, actual positive native correspondence and omitted-bend rejection. The positive native test uses explicitly synthetic requirements. The real manufacturer-source counterexample fails as expected. No native drawing or complete engineering acceptance is claimed by this new command.
