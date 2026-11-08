# EPANET to HVAC pipe rules

`python -m bsa.epanet_pipe_regulations examples/hvac-circulation/project.json --basis examples/hvac-circulation/regulatory-bases.json --pack regulations/hk/hvac-water-2026.11.08/pack.json --sources runs/hk-regulation-sources --out runs/new-circulation-rules`

This adapter reruns pinned WNTR/EPANET and binds every pipe's actual speed and distributed friction to the existing jurisdiction rule evaluator. The basis requires `density` (positive finite kg/m3 with source), `fluid_applicability` (evidence for compatibility with hydraulic viscosity/specific gravity), and `pipes` with exact per-pipe regulatory bases. All pipes, including pressure-reference connections, need an explicit applicability decision. Unknown density or code-diameter classification is not inferred. Supplied velocity/friction overrides are rejected.

Distributed pressure gradient uses SI Darcy f rho v²/(2D), with the independently audited engine friction factor and actual Q/A speed. Minor losses and elevation are excluded. This preserves the engine's friction-factor/viscosity convention while avoiding rounding from legacy head-unit conversion. Zero flow has zero gradient; near-zero native residuals remain visible. Fluid-temperature consistency remains an explicit engineering review, not automatically proved by an evidence string.

The synthetic 50 mm example retains passing hydraulic checks but exceeds the small-pipe velocity rule. The separately declared 65 mm bore/classification example passes the scoped pipe rules. Neither is a product selection or full HVAC compliance claim. Positive and negative native runs using the hash-pinned official BEC PDF are retained in `docs/evidence/circulation-pipe-rules`; no official PDF is redistributed.

Supported rule success requires coverage of every pipe and verified official source bytes. Hydraulic failures remain overall failures; rule reviews or missing sources remain pending. Native engine failures cannot pass via an empty set of checks. Reports retain source/input hashes and the fresh hydraulic report hash.

Workflow task kind `epanet_pipe_regulations` accepts project, basis, pack and sources. It inventories official source bytes and supports requires_pass gates. Chained circulation_duty, epanet_pipe_regulations and water_network tasks must consume identical hydraulic project bytes, including transitive gates. Each executes fresh hydraulics. Connected thermal/regulatory tasks now require exactly equal finite density values in kg/m3 for the same hydraulic input bytes. This includes reverse task order and sibling prerequisites converging on a consumer. Each thermal task must also use a single density across its targets. Conflicts fail workflow validation before native execution; records include declarations, source references and basis hashes. Equality is only numeric consistency: evidence validity, operating temperature, viscosity/specific-gravity compatibility and constant-property applicability still require engineering review. Different thermodynamic conditions need explicitly separate scenarios or a supported variable-property model, not an arbitrary matching tolerance. Saved IFC correspondence and complete regulatory coverage remain pending. The coverage planner recognizes this adapter as a scheduled pack consumer; scheduling is not execution or complete compliance.

Sources: [EMSD BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/BEC_2024_ENG.pdf), clauses 6.9.1–6.9.3; [EPA network model](https://usepa.github.io/EPANET2.2/3_network_model.html). Existing pinned WNTR/EPANET attribution and licenses remain applicable; no new dependency is added.

## Reproduce the combined demonstration

Download or verify the pinned official source once:

```powershell
.venv/Scripts/python scripts/fetch_regulation_sources.py regulations/hk/hvac-water-2026.11.08/pack.json --out runs/hk-regulation-sources
.venv/Scripts/python scripts/run_hk_circulation_demo.py --out runs/my-circulation-suite --official runs/hk-regulation-sources/emsd-bec-2024.pdf
```

Choose a new output directory. The runner refuses existing output and changed official bytes. It stages source-hashed inputs and source-linked briefs for three independent cases: 65 mm scoped pass, 50 mm pipe-rule review and insufficient thermal flow. Each retains native outputs, workflow integrity and blocker diagnosis. Summary success means expected demonstration behavior, including negative cases; manual engineering review remains pending in every case. No official PDF is committed. These synthetic inputs are not an actual coursework brief or product design.
