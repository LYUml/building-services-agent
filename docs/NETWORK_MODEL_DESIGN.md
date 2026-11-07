# Model-aware network sizing and IFC revision

This adapter connects NETWORK_BINDING.md and NETWORK_DESIGN.md. It derives baseline geometry from a source model, applies explicit outside-envelope constraints, runs conditional sizing, authors a new model and verifies saved IFC against the original endpoints and selected pressure calculation.

```powershell
python -m pip install -e ".[network,bim]"
python -m bsa.workflow execute examples/network-model-design/plan.json --out runs/model-design
python -m bsa.workflow verify runs/model-design
```

The `network_model_design` task has five source inputs: `project` (network skeleton without repeated length/diameter/elevation), `model`, `binding`, hydraulic `catalogue` and outside-envelope `geometry`. The direct CLI accepts the same inputs via `python -m bsa.network_model_design <network> --model <model> --binding <binding> --catalogue <catalogue> --geometry <geometry> --out <new-run>`.

The source model must declare a canonical `project_uuid`. Keep that UUID for revisions of the same project; generate a fresh UUID for a different project rather than copying the example's namespace. IFC authoring uses namespace-based stable object IDs keyed by class/input ID and stable port IDs keyed by device/port IDs. Root project identity does not depend on the display title. Other auto-generated relationship/representation IDs are not promised stable, and IFC bytes may change. Existing models without a namespace retain their prior generated-ID behavior outside this adapter.

Outside geometry explicitly covers every hydraulic catalogue option with `outside_diameter_m` and provenance. The required basis is `circular outside-diameter envelopes; fixed centrelines and endpoints`. Outside diameter must be at least internal diameter; the tool never infers wall thickness, outside size, insulation or clearance from internal diameter. Source dimensions remain required even for a synthetic case.

Each permitted segment/option is probed against the source model's containing space. Straight axis-aligned pieces resize about their existing centrelines: only transverse origins/sizes and local port offsets change; world endpoints and longitudinal lengths stay fixed. Out-of-space options are removed with explicit reasons before exhaustive hydraulic search. This containment constraint is separable per route piece; combinations are not subjected to physical clash or fitting-shape checks. Original/geometry-feasible candidate counts are recorded, and no admissible envelope or no hydraulic solution produces a failed task with baseline evidence retained.

The selected candidate produces `selected-model.json`, with new size/outer-envelope provenance and catalogue IDs, then a coordinated IFC/pressure run. Reopened IFC geometry-engine bounds are compared against the original world endpoints and explicit outside diameter. Saved internal/outer diameter properties and selected option IDs must match. The independently model-derived pressure requirement must agree with sizing. Baseline IFC/calculations, filtered catalogue, rejected options, sizing candidates and selected coordination evidence remain separate. Original inputs are hashed and unchanged; output overwrite is refused.

The synthetic example permits A (0.20 m internal / 0.22 m outside), B (0.40 / 0.45 m) and a deliberately oversized, cheap C envelope (0.25 / 2.00 m). C is excluded because its outside envelope leaves the containing space. A is selected, produces a 0.22 m transverse envelope and retains the original 3 m route endpoints. The computed source total-pressure requirement is about 61.827 Pa under the explicit synthetic flow/K assumptions. This is not a product or installed-system acceptance.

Tests exercise unchanged endpoints and non-route devices, multi-piece chains, axis permutations, repeated revisions without provenance loss, same-project stable IDs, different-project ID separation, out-of-space failures, metadata tamper rejection and workflow integrity. IFC schema/geometry checks do not replace BIM-viewer inspection. Detailed product solids, junction/connector sizes, collisions, balancing, operating points and full code acceptance remain pending; `design_accepted` remains false.
