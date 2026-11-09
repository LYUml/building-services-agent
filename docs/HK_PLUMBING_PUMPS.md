# Hong Kong sump-and-pump requirement

The modular pack `hk-plumbing-pumps-2026.11.09` implements a **sourced-facts comparison**, not native plumbing design. Its official basis is WSD Technical Requirements, April 2026, #6.3.1 (printed page 52, PDF page 61): duplicate pumpset provision and pumping capacity relative to the supplied storage tank's design outflow. The Preface classifies hashtag clauses as Water Authority requirements; do not relabel this as an independently verified statutory clause.

[Official publication index](https://www.wsd.gov.hk/en/plumbing-engineering/requirements-for-plumbing-installation/technical-requirements-for-plumbing-works-in-bldgs/index.html), [PDF](https://www.wsd.gov.hk/filemanager/en/content_1804/TR_2026_04%20%28Eng%29.pdf), [current circulars](https://www.wsd.gov.hk/en/plumbing-engineering/requirements-for-plumbing-installation/wsd-circular-letters/index.html). Reviewed publication/circular hashes are retained in `evidence/hk-plumbing-pumps/source-review.json`; originals stay in the ignored cache. CL6/2026 announces consolidation. Later CL5/2026 addresses 3.1.5 and figures. Project dates, applicability and other amendments remain explicit review responsibilities.

## Execution and interpretation

```powershell
.venv/Scripts/python -m bsa.regulations examples/hk-plumbing-pumps/facts.json --pack regulations/hk/plumbing-pumps-2026.11.09/pack.json --sources runs/hk-regulation-sources --out runs/new-plumbing-check
```

Use the existing `regulations` workflow adapter with this pack and facts project, and explicit `requires_pass` gates. The separate coverage snapshot `regulations/hk/coverage-2026.11.09-plumbing.json` includes this partial plumbing module; previous snapshots are unchanged.

Inputs require source-backed applicability, edition decision, duplicate-set declaration, positive capacity/outflow in m3/s, tank identity, duty basis and pump configuration basis. Capacity equality passes; insufficient capacity or absent duplication returns `review_required`. Missing sources, invalid units/values or unknown basis remain `pending`. An explicitly inapplicable case cannot establish supported-check success.

The example values and configurations are synthetic. Descriptive source strings are assertions, not authenticated manufacturer evidence. Do not use a pump's zero-head maximum flow, sum duty and standby capacities without a justified operating basis, or equate an IFC pump count with verified duplication. Native curve/system-head binding, standby/control arrangement and actual tank-demand derivation are still unimplemented. Results retain `binding_status: sourced_assertions_only`, `regulatory_compliance: not_established` and `design_accepted: false`.

Clause 6.5.1 does not itself supply a universal numeric 60 m pressure limit. No such limit is encoded here. Backflow, materials/GA approval, metering, storage, excessive-pressure design, drainage and fire services remain outside this check.
