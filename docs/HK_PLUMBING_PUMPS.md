# Hong Kong sump-and-pump requirement

The modular pack `hk-plumbing-pumps-2026.11.09` implements a **sourced-facts comparison**, not native plumbing design. Its official basis is WSD Technical Requirements, April 2026, #6.3.1 (printed page 52, PDF page 61): duplicate pumpset provision and pumping capacity relative to the supplied storage tank's design outflow. The Preface classifies hashtag clauses as Water Authority requirements; do not relabel this as an independently verified statutory clause.

[Official publication index](https://www.wsd.gov.hk/en/plumbing-engineering/requirements-for-plumbing-installation/technical-requirements-for-plumbing-works-in-bldgs/index.html), [PDF](https://www.wsd.gov.hk/filemanager/en/content_1804/TR_2026_04%20%28Eng%29.pdf), [current circulars](https://www.wsd.gov.hk/en/plumbing-engineering/requirements-for-plumbing-installation/wsd-circular-letters/index.html). Reviewed publication/circular hashes are retained in `evidence/hk-plumbing-pumps/source-review.json`; originals stay in the ignored cache. CL6/2026 announces consolidation. Later CL5/2026 addresses 3.1.5 and figures. Project dates, applicability and other amendments remain explicit review responsibilities.

## Execution and interpretation

```powershell
.venv/Scripts/python -m bsa.regulations examples/hk-plumbing-pumps/facts.json --pack regulations/hk/plumbing-pumps-2026.11.09/pack.json --sources runs/hk-regulation-sources --out runs/new-plumbing-check
```

Use the existing `regulations` workflow adapter with this pack and facts project, and explicit `requires_pass` gates. The separate coverage snapshot `regulations/hk/coverage-2026.11.09-plumbing.json` includes this partial plumbing module; previous snapshots are unchanged.

Inputs require source-backed applicability, edition decision, duplicate-set declaration, positive capacity/outflow in m3/s, tank identity, duty basis and pump configuration basis. Capacity equality passes; insufficient capacity or absent duplication returns `review_required`. Missing sources, invalid units/values or unknown basis remain `pending`. An explicitly inapplicable case cannot establish supported-check success.

The example values and configurations are synthetic. Descriptive source strings are assertions, not authenticated manufacturer evidence. Do not use a pump's zero-head maximum flow, sum duty and standby capacities without a justified operating basis, or equate an IFC pump count with verified duplication. The fresh single-line capacity binding below is available separately. Standby/control arrangement and actual tank-demand derivation remain unverified. Results retain `binding_status: sourced_assertions_only`, `regulatory_compliance: not_established` and `design_accepted: false`.

Clause 6.5.1 does not itself supply a universal numeric 60 m pressure limit. No such limit is encoded here. Backflow, materials/GA approval, metering, storage, excessive-pressure design, drainage and fire services remain outside this check.


## Fresh single-line operating capacity

`bsa.plumbing_pump_binding` replaces the declared capacity with the conservative lower-bracket flow from a freshly executed `bsa.pump` solve and selected network rerun. It reuses the existing pinned fluids 1.3.1 pressure engine. It requires a single free-flow line with a sourced fixed terminal total-pressure boundary and equal pump-port elevation basis; it does not solve multiple operating pumps, changing tank levels or suction/NPSH.

```powershell
.venv/Scripts/python -m bsa.plumbing_pump_binding --project examples/hk-plumbing-pumps/network.json --curve examples/hk-plumbing-pumps/curve.json --basis examples/hk-plumbing-pumps/binding.json --pack regulations/hk/plumbing-pumps-2026.11.09/pack.json --sources runs/hk-regulation-sources --out runs/new-plumbing-capacity
```

The binding file contains regulatory_basis plus a sourced connection: terminal_id, tank_id, capacity_mode, hydraulic_boundary_basis and source. Capacity mode is explicitly one operating pump with standby capacity excluded. Tank identity must match the regulatory basis, and terminal design demand must equal tank design outflow in m3/s. Omit available_pumping_capacity and capacity_duty_basis: the adapter computes them and rejects overrides. Neither descriptive associations nor model-independent duplication assertions prove installed configuration.

Workflow kind `plumbing_pump_regulations` takes project, curve, basis, pack and sources, inventories their files and official source, and executes fresh calculation. Use requires_pass for downstream gates. The inherited IFC-route mode below is also available; unrelated downstream models remain unverified. Scope planning recognizes this adapter as scheduling the selected pack.

If no converged operating point exists, no capacity fact is fabricated. Converged but insufficient flow retains both hydraulic failure and regulatory review. Other hydraulic failures also prevent overall pass even if the numerical capacity comparison passes. Missing/changed official sources preserve pending results. Outputs include the pump report, bound facts, report/artifact hashes and explicit remaining checks.

The official-PDF-backed synthetic trial produces approximately 1.253 L/s against a 1.0 L/s target; the same system fails at 1.5 L/s. These are software-test dimensions and curves, not product selections. Evidence: docs/evidence/hk-plumbing-pump-binding/native-trials.zip. Independent analytic solver tests, identity/override rejection, no-intersection behavior and workflow failure gates were exercised. Full plumbing conformity, actual pump data, duplication, controls and IFC verification remain unresolved.


### Downstream source correspondence

A plumbing capacity prerequisite now binds known downstream `network`, explicit-input `pump_operating_point` and repeated `plumbing_pump_regulations` tasks to the same source network bytes. Pump consumers also require identical curve bytes; repeated plumbing checks require identical basis bytes. Ancestor checks propagate through intermediate tasks, including manual review, and the workflow records these hashes in regulatory_source_bindings. Different source content is rejected at plan validation, while an identical copy at another path is allowed.

These comparisons apply only to the supported shared input fields. They do not verify arbitrary IFC/drawing consumers or prove that a prescribed-flow network result is the same physical operating scenario as a pump intersection. Changing the design intentionally requires a new corresponding check and plan, not reuse of a passing prerequisite for the old inputs.


## Saved IFC route inheritance

`plumbing_pump_regulations` can now use `depends_on` referencing an earlier passing `network_coordination` instead of `project`. Keep curve, basis, pack and sources; project/model/binding/IFC/producer replacement fields are forbidden. The template, original model and route binding come from the producer.

Before and after fresh capacity checks, `bsa.ifc_plumbing_pump` verifies all original input identities and hashes plus saved artifact coverage. It reconstructs the complete derived network from those originals, then reconciles saved IFC geometry/ports with that network. Editing generated dimensions and rewriting their manifest hashes cannot bypass the source reconstruction. Failed producer tasks block execution.

Known downstream pump consumers should inherit the same route producer and require this capacity check. Network-template, model, binding and curve source correspondence is recorded; explicit replacement network inputs cannot satisfy an inherited plumbing prerequisite. These are scoped source/route proofs, not arbitrary downstream model checks.

The example uses route-template.json, route-model.json and route-binding.json under examples/hk-plumbing-pumps: explicitly synthetic 5 m vertical hollow pipe geometry, 32 mm bore and 40 mm OD. It reuses the earlier synthetic riser structure with a separate namespace and explicitly revised dimensions. It is not measured project geometry. Real pipe product validity, tank/booster shapes, physical pump/tank identity, standby controls and saved-model clashes remain separate. Evidence: docs/evidence/hk-ifc-plumbing/native-trial.zip retains actual IFC, derived inputs and official-PDF-backed capacity results.


## Repeatable three-scenario demonstration

```powershell
.venv/Scripts/python scripts/run_hk_plumbing_demo.py --wsd-pdf runs/hk-regulation-sources/wsd-tr-2026-04.pdf --out runs/new-hk-plumbing-demo
```

The runner checks the official PDF against the pinned pack before staging a new repository-local output. It preserves the source examples and creates independent source-linked plans for: (1) sufficient capacity, (2) a sourced synthetic 1.5 L/s target exceeding available capacity, and (3) missing duplicate-set evidence. Each executes saved IFC route authoring, capacity checks and a gated same-source pump rerun. It records workflow integrity and dependency diagnosis, plus source/artifact hashes in summary.json.

Observed task statuses (route / capacity / downstream pump) are pass/pass/pass, pass/fail/pending and pass/pending/pending respectively. The latter two create no downstream pump output. The runner's demonstration_checks_pass means these expected behaviors were observed; it does not convert negative tasks to passes or approve an engineering design. Existing output directories are not overwritten. Evidence is retained in docs/evidence/hk-plumbing-demo with official PDFs excluded from redistribution.

For a real assignment, interpret the actual brief and source drawings into a separate plan. Do not edit the demonstration to masquerade as project data or reuse its flow/dimensions as measured inputs. Native DWG, actual pump/tank identity, standby controls and complete regulatory/engineering acceptance are not supplied by this runner.


## One-duty / one-standby capacity scenarios

Use `bsa.plumbing_pump_set` or workflow kind `plumbing_pump_set` for an explicitly sourced **one operating pump at a time** design. This operating mode is a project contract, not a new universal interpretation of WSD redundancy requirements. The two role IDs and source descriptions do not prove that physical duplicate equipment is installed.

```powershell
.venv/Scripts/python -m bsa.plumbing_pump_set --project examples/hk-plumbing-pumps/pump-set.json --basis examples/hk-plumbing-pumps/binding.json --pack regulations/hk/plumbing-pumps-2026.11.09/pack.json --sources runs/hk-regulation-sources --out runs/new-pump-set
```

The set contract contains exactly one duty and one standby row, each with a unique ID, source and relative network/curve file paths. Paths must stay in the set directory. Separate routes/curves are permitted, but fluid properties and receiving-terminal identity/elevation/total-pressure boundary must match; each terminal design flow must match the common tank-outflow basis. A physically justified common datum and fixed boundary remain source responsibilities.

Both roles execute the existing fresh pump/pipe/WSD adapter independently. Each must meet the complete design target alone; capacities are never added. A failed standby cannot be masked by a passing duty pump. Missing evidence remains pending, rejected/failed role results remain in the report, and all nested inputs are hash-tracked. Workflow inputs include both networks and both curves. Downstream repeated set checks compare the full role-specific source inputs; supported single-pump consumers must explicitly select and match a role as described below.

Official-PDF-backed synthetic positive and weak-standby negative evidence is in docs/evidence/hk-pump-set. The latter retains duty pass / standby fail and overall failure. Tests cover actual separate solves, gated downstream blocking, source modification, duplicate identities and mismatched receiving boundaries. This does not simulate simultaneous parallel pumps, switching/interlocks, isolation valves, common-cause reliability, dynamic tank levels, actual suction/NPSH or physical IFC identity. Full engineering acceptance remains false.


### Downstream role binding

A downstream `network`, `pump_operating_point`, `plumbing_pump_regulations` or `water_pipe_regulations` task can require the set check (directly or through prerequisite ancestors) and declare `pump_role: "duty"` or `pump_role: "standby"`. Its explicit project must contain identical network bytes to that role. Pump calculations additionally require identical curve bytes; repeated WSD checks also retain the same plumbing basis. The workflow records role-specific source hashes. Copies at different paths are permitted only when their bytes match.

Missing/invalid roles, unrelated source replacements and role declarations without an upstream set gate are rejected before execution. Inherited geometry producers are not yet supported by this role handoff. The complete set must pass before either downstream role runs; a good duty pump cannot bypass a failed standby through an intermediate prerequisite. This is source correspondence, not physical equipment identity or a new regulatory approval.


### Repeatable role-handoff and delivery demonstration

```powershell
.venv/Scripts/python scripts/run_hk_pump_set_demo.py --wsd-pdf runs/hk-regulation-sources/wsd-tr-2026-04.pdf --out runs/new-pump-set-workflow
```

This runner reuses the existing workflow, pump-set, role binding, diagnosis and delivery-review tools. It pins the official PDF before staging three separate synthetic briefs and source-linked plans. Each requirement maps to its own brief passage. The sufficient-capacity case executes the set, duty rerun and standby rerun; weak standby blocks both reruns; missing duplication evidence leaves the set and both reruns pending. Inputs remain unchanged and all workflow artifacts are checked.

A separate delivery-review template and audit are created for every scenario. Passing calculation tasks do not automatically approve any requirement: the positive and missing-evidence cases remain needs_review, while the failed capacity case remains failed. The runner verifies these states as part of its software demonstration, retaining design_accepted=false. It supplies no IFC geometry, installation drawings, authentic equipment specifications or control verification. Use the saved-IFC runner for that separate supported route demonstration; neither is a complete assignment.

Actual official-source-backed evidence is archived under docs/evidence/hk-pump-set-workflow; the WSD PDF is omitted from redistribution. The included manifests retain original execution paths, so reproduce with the command above for a fresh integrity audit rather than treating the relocated archive as a live run.
