# Source-bound compound rectangular junction

The existing separate maximum-section tee/cross cores do not fit on the short
shared source segment. `bsa.compound_junction` provides a deliberately different
construction: one centred piecewise-linear rectangular trunk and separated
side takeoffs. It creates a new candidate without changing source originals.
It is not a manufacturer fitting, plenum rating or pressure-loss model.

`bsa.source_compound_junction` binds a candidate to an original adjacent
three-arm/four-arm pair and the independently verified native parent network.

```
python -m bsa.source_compound_junction run CROSS_NETWORK_RUN POLICY --out FRESH_RUN
python -m bsa.source_compound_junction verify FRESH_RUN
```

Host `BSA_PROJECT_ROOT` selects external coursework; documents cannot select a
workspace. Sources and previous failed scenarios remain immutable. Outputs must
be fresh. Exit 2 preserves incomplete engineering/network acceptance.

## Reuse decision

The installed/pinned IfcOpenShell 0.8.5 `ShapeBuilder.faceted_brep`, `extrude`,
Boolean and port APIs supply the native engine. Existing Manifold3D 3.5.4 and
IFC mesh/mass checks provide the independent material checks. Current official
[BRep documentation](https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/shape_builder/index.html)
and the [upstream authoring discussion](https://github.com/IfcOpenShell/IfcOpenShell/issues/2181)
were checked. Neither establishes an executed ready-made compound fitting
integration; no runtime upgrade/new dependency is inferred. This adapter adds
source station/branch construction and analytic QA, not a replacement kernel.

## Explicit geometry and analytic bounds

Native input fields are project_uuid, source, classification, placement,
wall_thickness_m, stations, branches, port_directions. A station declares
y_m, width_m, height_m; ordered stations define centred straight/tapered spans.
A branch declares id, y_m, side (-1/+1), width_m, height_m and reach_m. External
branch caps lie beyond the trunk; branch outer Y extents stay inside trunk
caps; same-side takeoffs must be disjoint including wall offsets. Branch height
cannot exceed the minimum trunk height. Unsupported geometry rejects instead
of approximating it. One explicit SINK and all remaining SOURCE ports describe
the bounded split construction.

The native body is outer union minus inner union. Trunk operands are literal
station BReps; side operands are native rectangular extrusions. The offset is
in section planes, not constant normal sheet gauge on tapered faces.
Every operand, source station, branch dimension/frame and owned port is checked
in the saved IFC, along with schema/EXPRESS and rigid placement.

Independent volume and first moments integrate the piecewise trunk area and
side boxes, subtracting each trunk/side intersection. Opposite half-space side
prisms have zero common volume; same-side Y intervals are disjoint. Validation
guarantees the complete side height lies inside the trunk and its reach exceeds
the trunk half-width. The integrands have degree at most three, so piecewise
Simpson integration is exact for the declared construction, not an approximate
sampling substitute. Native material volume and centroid must agree. Closed
mesh edges, one connected material, Euler characteristic 2-2(Nports-1), and
independent complete trunk/side centre-air probes must also pass.

## Source handoff and retained limitations

The source adapter currently requires an aligned vertical-plan trunk, original
three/four-arm node pair, exact shared profile, every original side outlet and
a verified existing inlet elbow cap. It explicitly absorbs the residual inlet
straight and the complete shared straight into the new fitting. This replaces
the short inlet straight profile with a declared taper, retains the shared
profile internally, and preserves all external nominal sections/rays. It is a
construction revision, not a claim that every original straight body survives.
The minimum remainder continues to apply to every retained branch/outlet
straight. A declared trunk angle limit must pass; it is not inferred from a code.

All original requirement identities, source scale/elevation/gauge assumptions
and previous failures survive. The candidate has no merged-network connections
until a separate verified integration. Whole-network raw coordination, complete
pressure/loss/fan work, physical joints, construction, products, architecture/
equipment and full regulatory/engineering acceptance remain pending.

## Verified network integration

After the source candidate, use the separate integration adapter:

```
python -m bsa.source_compound_network run COMPOUND_CANDIDATE_RUN --out FRESH_NETWORK_RUN
python -m bsa.source_compound_network verify FRESH_NETWORK_RUN
```

It reconstructs the complete original source ancestry and deliberately removes
only the two declared absorbed straight bodies and their single replaced inlet
link. Other native fitting/source records survive. The remaining branch/outlet
straights are trimmed from their existing source endpoints, preserving previous
tee/cross consumption separately from compound consumption. Every retained
straight must meet the unchanged minimum remainder.

The pinned official asset and port APIs append the existing verified fittings
and the compound body. Saved geometry/property fingerprints, world frames,
owned ports, cap positions/normals, retained straight roll, exact links, supply
system, reference containment and schema/EXPRESS are checked. The compound inlet
uses the original verified horizontal-plan elbow cap and matched source section.
The saved product graph must be a single connected directed tree with complete
represented source body coverage. This does not imply a complete building model.

## Executed real source construction revision

ROOT/J2 now have a five-port source-bound compound candidate. It absorbs the
residual A-03 straight up to the existing elbow cap and the full D-01 shared
straight, explicitly replacing the former inlet straight by a short taper.
D-01's nominal clear profile remains inside the trunk and every external source
section/ray is retained. The three side reaches of 0.9 m, outlet reach of 1.0 m
and 30-degree maximum included trunk angle are classified study assumptions,
not code/product recommendations. The original separate-core failure remains.

Actual native material is one connected closed five-ended wall, Euler -6. Native
volume and centroid match independent polynomial integration and all trunk/side
centre probes remain open. The new saved network has 102 bodies, 223 owned ports,
101 directed links and 21 boundary ports (20 SOURCE, one SINK), in one connected
represented product tree. All 33 requirement identities remain.

The exact preceding raw policy with zero contact waivers now reports zero
intersections, down from six unique pairs. Geometry coverage passes, with no
missing/invalid/unrepresented geometry or unverified solid pairs. Clearance still
fails: 101 raw records represent 101 unique pairs. All remain visible. Neither
zero intersections nor a connected graph clears joints, loss/pressure, products,
installation, architecture/equipment or complete engineering/code acceptance.

Nine source/native regression tests pass. Separate saved-model controls reject
deletion of a compound link and alteration of a native trunk station. The actual
saved compound body in the combined IFC was previewed and inspected; some port
labels overlap. Only that body is displayed, not whole-network visual acceptance
or a drawing ready for delivery. Existing DWG/PDF deliverables are unchanged.

The separate actual integration verify CLI also independently replays the complete
original source ancestry, new source trim/absorption model and saved native
fingerprints/frames/links. Integrity passes while complete_network and
design_accepted remain false. See [safe aggregate evidence](evidence/source-compound-network.json).
