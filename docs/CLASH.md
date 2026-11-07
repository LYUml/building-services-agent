# Saved IFC geometry coordination

`ifc_clash` reads a saved IFC plus a sourced checking policy. It combines IfcOpenShell geometry/clearance queries with pinned Manifold3D closed-mesh Boolean intersections. It never edits the source file or calls a bounding-box overlap a material clash by itself.

```powershell
python -m pip install -e ".[clash,network]"
python -m bsa.workflow execute examples/clash-plan.json --out runs/coordinated-clash
python -m bsa.workflow verify runs/coordinated-clash
# Standalone source IFC:
python -m bsa.clash source.ifc --policy reviewed-policy.json --out runs/clash-only
```

The workflow adapter takes `policy` and exactly one of `ifc` or `depends_on`. A dependency must be an earlier supported IFC producer: bim, network_coordination, network_model_design, electrical_coordination or electrical_lighting. The runner resolves the known output path, not a caller-supplied arbitrary artifact path. Failed/pending producers leave QA pending. Input IFC/policy hashes and generated artifact hashes are retained; detected clashes fail the task while preserving reports.

The fixed policy scope is `all represented non-feature non-virtual IfcElements`. Spaces and annotations are not physical obstacles; feature/virtual elements are excluded explicitly. Unrepresented physical elements, missing conversions, empty/nonfinite/open or inconsistently oriented meshes and rejected Manifold operands make geometry coverage fail. One project and one explicit length unit resolving to SI metres are required; recognised conversion units and millimetres are normalised. Duplicate/invalid GlobalIds block reliable contact identity. Supplied geometry declarations are shown as metadata, not trusted as proof of shape.

Policy fields supply provenance, positive minimum clearance, intersection/contact tolerances, overlap-volume tolerance and a Boolean candidate budget. Twice the 1e-5 m QA mesh deflection must not exceed contact tolerance; contact <= intersection <= clearance. Source thresholds are not regulation clauses or universal service clearances. The geometry mesh also uses 0.02 angular deflection and welded vertices.

IfcOpenShell triangle queries retain protrusion/piercing/collision and clearance findings, native witness points and their reported distances. These distances are engine-specific metrics, not a minimum translation vector. The installed 0.8.5 triangle intersection interface missed an independently verified coplanar/aligned box overlap, so it cannot establish solid separation alone.

The additional Manifold3D 3.5.4 backend accepts float64/uint64 Mesh64 data, checks accepted positive-volume solid status, and intersects every pair whose mesh bounding boxes overlap on all axes beyond the intersection tolerance. Bounds only screen candidates; the material intersection is a Boolean result. An explicit candidate budget causes failure rather than silent truncation. Positive common mesh volume beyond the supplied threshold is an intersection; conversion/kernel errors remain unverified and prevent a pass. Mesh volume is not an exact analytic product quantity. Independent fixtures check 0.2 m3 aligned overlap, 0.008 m3 full containment, rotated tessellated bodies and an object inside a tube's empty bore.

Contact rules must provide actual SOURCE/SINK port GUIDs, a source reference and a positive `region_radius_m`. They must belong to an actual IFC connection, have explicit coincident world placements within tolerance, and belong to the checked scope. A clearance finding can be excepted only when its minimum-distance witnesses lie in the supplied contact region, separation is within contact tolerance, and neither intersection nor unverified solid coverage exists for the pair. Solid overlap cannot be waived.

This is a **pair minimum-clearance exception**, not exhaustive clearance measurement outside the joint: a pair's closest point at an intended connection may hide another close zone. Accepted exceptions remain in JSON/HTML with their scope, and other-zone clearance stays pending. The rule does not certify connector compatibility, port normal alignment across unrelated equipment or fitting geometry. Use independent product/interface review before full acceptance.

The synthetic example authors the circular network, then checks its saved selected IFC. Three represented objects have no detected solid overlaps; two intended end-face contacts receive explicit 0.15 m witness-region exceptions under a 50 mm clearance policy. This is a policy-scoped result for synthetic envelopes/walls, not an installed-system certificate. BIM-viewer review, source/product/insulation fidelity and full engineering acceptance remain pending; design_accepted stays false.

Outputs include runtime versions, element identities/declarations, coverage, all findings, Boolean volumes, accepted exceptions, policy and source/artifact hashes in clash.json and a readable report.html. Primary references: [IfcOpenShell geometry-tree methods](https://docs.ifcopenshell.org/ifcopenshell-python/geometry_tree.html), [Manifold project](https://github.com/elalish/manifold/tree/v3.5.4) and [pinned package release](https://pypi.org/project/manifold3d/3.5.4/). The documented IfcOpenShell site may show newer APIs; this adapter exercises the installed 0.8.5 interface and does not pass newer backend arguments.
