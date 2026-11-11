# Partial finite-elbow backbone

This adapter reuses source-backbone compilation,existing rectangular straight/
90-degree elbow native authoring and official IfcOpenShell spatial/port APIs.
It retains every original equal-section elbow and known two-end length failure.
It does not infer a fabrication catalogue,loss coefficient or bend-radius rule.

```powershell
.venv/Scripts/python -m bsa.duct_elbow_backbone runs/project/plan.json runs/project/workflow native runs/project/backbone-basis.json runs/project/elbow-radii.json --out runs/project/elbow-backbone
```

The classified elevation/gauge/nominal-section basis from DUCT_BACKBONE_IFC.md
still applies. Radii maps every fresh elbow_required node to exactly radius_m,
classification and source. No source elbow may be silently omitted;no radius
default or automatic reduction exists. A native hollow bend needs radius greater
than its outside radial half-width. Unsupported geometry remains blocked;this
software constraint is not a manufacturer recommendation or code requirement.

Each source section's budget deducts both declared endpoint elbow reaches.
Nonpositive remaining length blocks every responsible corner. Full declared
budgets survive even when blocked corners are excluded from partial authoring.
Other fitting reaches remain unknown;positive remainder does not prove complete
assembly fit. Nonelbow nodes,including two-arm transitions and straight
continuations,remain in the source connection register.

Eligible bends inherit source rays and equal selected sections. Actual quarter
cap stations determine adjacent straight trims. Original IDs,nominal dimensions
and flows remain. Real same-file source-to-sink IFC links have coincident,
opposed native caps. Final bodies/profiles/curves/meshes,ports,system,flow and
actual links are checked after reference-storey export. No temporary IfcSpace
remains. These checks do not prove complete connected-material topology,physical
joints,products,pressure or installed geometry.

Outputs include Supply Backbone.ifc,model input,native verification and
elbow-backbone.json with source/fit budgets,original requirements and artifact
hashes. This standalone study does not replace the existing native single-line
coursework drawing/report package.

Four focused tests pass:real native export,link tampering,all-node coverage,
two-end overrun and retained transition obligations. Actual10-corner study uses
an explicitly chosen,unaccepted radius=1.5xwidth scenario. Eight are authored;
CORRIDOR-A/B remain blocked. A-02 has -1.05m and A-03 -0.725m after specified
known trims. These are failures of this radius scenario,not proof that the
original route has no feasible design.

The model has47 source straights plus8 bends,110 owned ports and16 actual links.
Existing raw clash checks cover all55 geometries without waivers or unverified
solid pairs. Intersection pairs decrease from48 to40;clearance remains failed,
including intended touching interfaces. Exact exported-mesh equivalence binds
the inspected whole-plan/curved-node preview. Two blocked elbows,15 unequal
tees,two multi-branch nodes,physical joints/trims and full installation/pressure
acceptance remain pending. See [evidence](evidence/duct-elbow-backbone.json).
