# Candidate pipe route search

`python -m bsa.route_search examples/route-search/route-input.json --out runs/new-route`

This tool searches a finite planar cardinal grid from declared start to end. Inputs specify metre units, grid origin/count/step, outside diameter, bend centreline radius, clearance, and individually sourced rectangular obstacle footprints. Start and end must be grid nodes. The grid limits centreline search, not physical room containment. All obstacles affecting the routing plane must be represented; no drawing or IFC obstacle extraction is yet performed.

The directed search state includes travel heading. Every turn becomes an explicit quarter-circle; step must exceed twice the bend radius so adjacent turns leave positive straight lengths. Edge cost is actual centreline length after trimming corners, plus an optional nonnegative `bend_penalty_m` with explicit `objective_source`. With no penalty, Dijkstra search finds the shortest route among the conservative accepted finite-grid paths, not a globally optimal continuous-space route. With a penalty it minimises that declared equivalent-length objective. Search size is bounded at 50,000 grid nodes.

Straight corridors and quarter-circle bounding rectangles include pipe outside radius and the declared clearance. This can reject a feasible route near corners; a no-path result does not prove the real building has no route. The compiled straight/elbow lengths are reconciled against search cost, and compiled piece bounds are checked again. The search does not enforce endpoint tangent directions, multiple-service coordination, route self-clearance, supports, access, gravity drainage or product bend limits. These remain required before installation acceptance.

The output preserves input SHA256 and separate `route_found`/`design_accepted` fields. A valid but blocked grid writes an explicit failed search and exits 2. Invalid input raises an error. Original source files and existing output directories are preserved.

The synthetic example routes around one column. Five tests cover direct length, finite-bend detour length, independent sampling of actual curved centreline clearance, a spanning barrier, invalid dimensions/grid/provenance and blocked endpoints. `docs/evidence/route-search` retains the actual example and test log. The search module produces candidate geometry; use the separate compiler below for IFC and pressure calculations. No IFC, DWG, hydraulic or engineering acceptance is claimed by search alone.

## Model and pressure handoff

`python -m bsa.route_model examples/route-search/route-input.json --settings examples/route-search/model-settings.json --network examples/route-search/network.json --out runs/new-route-model`

The separate compiler reruns the search from original input, then creates an explicit XY-plane route at the sourced elevation. Settings supply project namespace, containing space, distribution system, internal diameter and separate straight/elbow excess K values. The existing BIM validator checks every finite bend, straight wall, port and space containment. The pressure skeleton supplies fluid properties, demand, supply/terminal pressures, roughness and velocity target; it must not repeat generated length, bore or aggregate K.

Generated model, binding and network inputs feed the existing native IFC author/reopen and saved-geometry pressure reconciliation. Model input can be revised and the IFC is retained. All original inputs are hash-checked. The searched route minimises physical centreline length only: more bends can shorten its rounded path while increasing local pressure loss. This compiler reports that loss; it does not optimise hydraulics or installation cost. Obstacle rectangles are not yet authored into IFC, and independent saved-model clash/self-clearance plus native drawings/visual review remain pending. A successful calculation does not approve the route.

## Pressure-based route selection

`python -m bsa.route_optimize examples/route-search/route-input.json --settings examples/route-search/model-settings.json --network examples/route-search/network.json --out runs/new-pressure-route`

This wrapper retains the unpenalised baseline and derives a bend penalty from the fixed-bore, prescribed-flow calculation. Friction per metre is constant under this model. Each additional bend adds its excess K and one additional straight piece's excess K. The equivalent-length penalty is `(K_bend + K_straight) * dynamic_pressure / friction_gradient`. The first straight piece contributes a constant loss, included in the reconciliation but not the search ordering. The resulting objective therefore minimises dissipative pressure across accepted grid paths under these assumptions. Endpoints have fixed elevation; this is not a pump/system operating-point or variable-bore optimisation.

The selected path is recalculated, its pressure is reconciled to the search objective, and its native IFC is generated/reopened through the compiler. `selection.json` survives downstream authoring failure. A reduced loss does not override a failed pressure/velocity target. The synthetic example changes from eight to two bends and increases physical length while lowering loss; independently calculated laminar and local-loss checks cover the tradeoff. Actual saved-model evidence is in `docs/evidence/route-pressure`. Route self-clearance, IFC obstacles, installation costs, product applicability, native drawings and visual acceptance remain pending.
