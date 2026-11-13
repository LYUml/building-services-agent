# Four-arm source junction candidates

`bsa.rectangular_cross` authors a sourced ideal equal-section planar cross with
four owned ports. `bsa.rectangular_cross_transitions` composes zero to four
existing centred transitions. `bsa.source_cross_candidates` binds that construction
to every original four-arm node after a verified partial source tee network.

```
python -m bsa.source_cross_candidates run TEE_NETWORK_RUN POLICY --out FRESH_RUN
python -m bsa.source_cross_candidates verify FRESH_RUN
```

Use explicit host `BSA_PROJECT_ROOT` for external projects; documents cannot
select a workspace. Output must be fresh and outside sources. Exit 2 retains
incomplete engineering scope even when native/integrity checks pass.

## Reuse and construction

Pinned IfcOpenShell 0.8.5 ShapeBuilder/Boolean APIs create the outer-minus-inner
unions of two full perpendicular rectangular extrusions. Manifold3D 3.5.4 and
existing native tests independently check material. Tee source/dimension/frame
guards and centred transition authoring are reused. No new engine is added.
The existing tee adapter cannot represent the missing fourth source arm.

The upstream distinguishes X junctions in its
[authoring discussion](https://github.com/IfcOpenShell/IfcOpenShell/issues/2181).
Its [geometry documentation](https://docs.ifcopenshell.org/ifcopenshell-python/geometry_creation.html)
was checked for reuse; current online docs are not proof of a local runtime
upgrade or a verified ready-made cross-fitting integration.

The core has the same exact fields as rectangular_tee, except port_directions
contains main-a, main-b, branch-a, branch-b. main_half_length_m is each local Z
reach; branch_length_m is each local X reach. Endpoints exceed outside half-width.
Four directions are all bidirectional or explicit SOURCE/SINK splitting/mixing.
Source compilation supports one incoming/three outgoing arms and two opposed,
perpendicular horizontal pairs.

Policy fields are exactly source and nodes; every original multi-branch node
must be covered. Each node declares core_section_m, main_half_length_m,
branch_length_m, start_length_m, end_length_m, upstream_angle_degrees,
transition_method, classification, source, as in the tee study. Transition methods
stay explicit; no fallback changes a declared method. Core/child GUIDs are
independently namespaced. Source sizes/rays and classified construction/elevation
remain separate from product or measured installation facts.

## Checks and limits

Core inspection checks literal native prism sections, depth, orientation, CSG
operators, source/classification, placement and all four owned port GUIDs/frames.
Independent volume uses ((2L+2B)w-w²)h for each outer/inner union. Closed mesh,
one connected material, Euler characteristic -4, exact bounds and both full
centre-bore probes must pass. Composition checks each native component, exact
body/port/system/link inventory, coincident opposing cap planes, no material
interpenetration, connected material union, independent summed volume, four-ended
topology and through-bore probes including tapered arms. Source-size and saved
port-direction tampering reject.

Both ends of every source section consume declared reaches against the freshly
verified parent's remaining straight budgets. The minimum remainder, blocked
tees and original requirement identities remain. Blocked nodes have no model.
Verification rebuilds source mapping, geometry, budgets and native inspections.

These isolated candidates do not change the parent network or clear its clashes.
Product joints/losses, radiused fabrication, constant sheet-normal taper walls,
architecture/equipment, installation and full regulatory acceptance remain open.

## Executed real source study

Both original four-arm nodes are covered. J1 authors as one cross plus three
centred transitions: four native bodies, ten owned ports, three actual internal
links and four boundary arms. Saved native material, volume, topology and bore
checks pass. J2 stays blocked on D-01: its declared 0.725 m incoming core reach
exceeds the parent's 0.619416 m available straight before the unchanged 0.05 m
minimum remainder. No J2 native model is emitted. ROOT remains blocked through
the inherited tee obligations. These results apply to the explicit study
construction, not every possible redesign.

Core size is the maximum incident width/height; half-reaches are half core width
plus 0.1 m; transition ends are each 0.05 m with 30 degree included wall-plane
angle. All are declared study assumptions, not code or product recommendations.
Source routes, sizes, elevation/gauge classifications and minimum remainder are
unchanged. All 33 requirement IDs remain.

The actual saved J1 IFC preview was inspected. It shows the cross and three
transitions; some port labels overlap. It is not a delivery/installation drawing.
The parent 99-body/90-link network and its raw 10 intersection pairs remain
unchanged because this local cross has not been merged. Ten source/native tests
pass, including source mapping, missing-node/invalid-ray rejection, inherited
budget blocking, real native assembly and changed dimensions/port directions.
