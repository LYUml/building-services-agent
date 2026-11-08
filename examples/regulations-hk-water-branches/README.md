# Unequal-branch regulatory sizing example

All geometry, demands, pressures, material scores and applicability decisions are synthetic. This independent tree has an 8 m trunk and 6/9 m branches, prescribed 0.4/0.8 L/s terminal flows and separately supplied diameter classifications. It is not an actual closed-loop hydronic system or product schedule.

Run `python -m bsa.water_pipe_design examples/regulations-hk-water-branches/network.json --catalogue examples/regulations-hk-water-branches/catalogue.json --basis examples/regulations-hk-water-branches/bases.json --classifications examples/regulations-hk-water-branches/classifications.json --pack regulations/hk/hvac-water-2026.11.08/pack.json --sources runs/hk-regulation-sources --out runs/new-branch-search`.

The actual 27-combination run selects D40 trunk, D25 branch A and D32 branch B with abstract weighted material score 758. The trunk flow is 1.2 L/s. Independent Q/A lower-bound tests reproduce the selected options and verify invariance when node/segment input order is reversed. Complete candidate calculations and rejected rule/pressure results are retained, followed by a fresh selected rerun. This example has no authored branch IFC or native drawings; those remain separate work.
