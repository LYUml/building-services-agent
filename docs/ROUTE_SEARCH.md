# Candidate pipe route search

`python -m bsa.route_search examples/route-search/route-input.json --out runs/new-route`

This tool searches a finite planar cardinal grid from declared start to end. Inputs specify metre units, grid origin/count/step, outside diameter, bend centreline radius, clearance, and individually sourced rectangular obstacle footprints. Start and end must be grid nodes. The grid limits centreline search, not physical room containment. All obstacles affecting the routing plane must be represented; no drawing or IFC obstacle extraction is yet performed.

The directed search state includes travel heading. Every turn becomes an explicit quarter-circle; step must exceed twice the bend radius so adjacent turns leave positive straight lengths. Edge cost is actual centreline length after trimming corners. Dijkstra search finds the shortest route among the conservative accepted finite-grid paths, not a globally optimal continuous-space route. Search size is bounded at 50,000 grid nodes.

Straight corridors and quarter-circle bounding rectangles include pipe outside radius and the declared clearance. This can reject a feasible route near corners; a no-path result does not prove the real building has no route. The compiled straight/elbow lengths are reconciled against search cost, and compiled piece bounds are checked again. The search does not enforce endpoint tangent directions, multiple-service coordination, route self-clearance, supports, access, gravity drainage or product bend limits. These remain required before installation acceptance.

The output preserves input SHA256 and separate `route_found`/`design_accepted` fields. A valid but blocked grid writes an explicit failed search and exits 2. Invalid input raises an error. Original source files and existing output directories are preserved.

The synthetic example routes around one column. Five tests cover direct length, finite-bend detour length, independent sampling of actual curved centreline clearance, a spanning barrier, invalid dimensions/grid/provenance and blocked endpoints. `docs/evidence/route-search` retains the actual example and test log. This is candidate geometry; conversion to the existing source-bound IFC/pressure/native drawing pipeline remains the next integration step. No IFC, DWG, hydraulic or engineering acceptance is claimed by this module.
