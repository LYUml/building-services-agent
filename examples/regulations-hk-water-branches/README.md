# Unequal-branch regulatory sizing example

All geometry, demands, pressures, material scores and applicability decisions are synthetic. This independent tree has an 8 m trunk and 6/9 m branches, prescribed 0.4/0.8 L/s terminal flows and separately supplied diameter classifications. It is not an actual closed-loop hydronic system or product schedule.

Run `python -m bsa.water_pipe_design examples/regulations-hk-water-branches/network.json --catalogue examples/regulations-hk-water-branches/catalogue.json --basis examples/regulations-hk-water-branches/bases.json --classifications examples/regulations-hk-water-branches/classifications.json --pack regulations/hk/hvac-water-2026.11.08/pack.json --sources runs/hk-regulation-sources --out runs/new-branch-search`.

The actual 27-combination run selects D40 trunk, D25 branch A and D32 branch B with abstract weighted material score 758. The trunk flow is 1.2 L/s. Independent Q/A lower-bound tests reproduce the selected options and verify invariance when node/segment input order is reversed. Complete candidate calculations and rejected rule/pressure results are retained, followed by a fresh selected rerun. This example has no authored branch IFC or native drawings; those remain separate work.


## Planar IFC adaptation

`model.json`, `skeleton.json`, `binding.json` and `geometry.json` define a separate planar adaptation at z=2 m, with the same 8/6/9 m lengths and demands. The skeleton omits elevations, lengths and bores so they come from model ports and saved circular-wall geometry. It intentionally differs from the numerical example's rising elevations. The system is explicitly CHILLEDWATER. The three-port junction is a coincident-port placeholder box, not a physical tee/reducer. Its declared K remains an unverified synthetic network input; do not treat this as an installation layout or complete chilled-water circuit.

Use `bsa.regulated_water_model` with these files plus the catalogue/bases/classifications and the source-pinned water pack. The actual 27-candidate run selected D40/D25/D32, preserved endpoint/object/port identities and passed saved geometry, connection, hydraulic and selected-rule rechecks. Evidence is in `docs/evidence/regulated-branches-model`. Clash/clearance, real fittings, return circuit, native drawings and whole-project acceptance remain pending.
