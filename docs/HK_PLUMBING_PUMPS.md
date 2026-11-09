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

Workflow kind `plumbing_pump_regulations` takes project, curve, basis, pack and sources, inventories their files and official source, and executes fresh calculation. Use requires_pass for downstream gates. It does not inherit an IFC producer or verify an unrelated downstream model. Scope planning recognizes this adapter as scheduling the selected pack.

If no converged operating point exists, no capacity fact is fabricated. Converged but insufficient flow retains both hydraulic failure and regulatory review. Other hydraulic failures also prevent overall pass even if the numerical capacity comparison passes. Missing/changed official sources preserve pending results. Outputs include the pump report, bound facts, report/artifact hashes and explicit remaining checks.

The official-PDF-backed synthetic trial produces approximately 1.253 L/s against a 1.0 L/s target; the same system fails at 1.5 L/s. These are software-test dimensions and curves, not product selections. Evidence: docs/evidence/hk-plumbing-pump-binding/native-trials.zip. Independent analytic solver tests, identity/override rejection, no-intersection behavior and workflow failure gates were exercised. Full plumbing conformity, actual pump data, duplication, controls and IFC verification remain unresolved.


### Downstream source correspondence

A plumbing capacity prerequisite now binds known downstream `network`, explicit-input `pump_operating_point` and repeated `plumbing_pump_regulations` tasks to the same source network bytes. Pump consumers also require identical curve bytes; repeated plumbing checks require identical basis bytes. Ancestor checks propagate through intermediate tasks, including manual review, and the workflow records these hashes in regulatory_source_bindings. Different source content is rejected at plan validation, while an identical copy at another path is allowed.

These comparisons apply only to the supported shared input fields. They do not verify arbitrary IFC/drawing consumers or prove that a prescribed-flow network result is the same physical operating scenario as a pump intersection. Changing the design intentionally requires a new corresponding check and plan, not reuse of a passing prerequisite for the old inputs.
