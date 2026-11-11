# Source-native straight-wall backbone

This adapter transforms a passing native-sheet/schedule source into the existing
IFC authorer's rectangular-wall input. It reuses IfcOpenShell0.8.5 API/native
geometry,existing bim/rectangular_geometry and whole-source topology/friction
checks. It introduces no geometry engine or inferred fitting/product catalogue.

```powershell
.venv/Scripts/python -m bsa.duct_backbone_ifc runs/project/plan.json runs/project/workflow native runs/project/backbone-basis.json --out runs/project/backbone
```

The basis JSON contains exactly project_uuid,elevation_m,wall_thickness_m and
profile_interpretation. Every input except the namespace is an object with value,
classification and source. Classifications are given,measured,assumed or
design_target. Elevation is finite,wall thickness positive,and the only supported
profile interpretation is scheduled_nominal_as_clear_internal. There are no
construction defaults. An assumed gauge or datum does not become a manufacturer
specification,actual installed elevation or regulatory design input.

The exact saved native XY nodes,section IDs,LINE handles,selected dimensions and
flows are inherited. Existing source-tree checks reject changed source sizes,
flows,missing edges or broken topology. This scope supports horizontal
axis-aligned straight sections only. Width is horizontal transverse to each
section,height vertical. Directed source-node endpoints determine inlet SINK
and outlet SOURCE ports,including negative world-axis flow.

Every source section becomes an untrimmed hollow straight wall of its original
centreline length. End planes have not been cut back for fittings. The model
therefore deliberately retains overlapping/disconnected junction interfaces.
Ports remain unlinked:adding logical links would not supply the missing physical
tees,elbows,transitions or multi-branch connections. No VAV,flex,air-terminal,
architectural-room or complete pressure model is inferred.

The existing authorer uses a labelled coordination envelope internally. Official
IfcOpenShell spatial APIs recontain the final ducts under a storey named
COORDINATION-REFERENCE-PLANE and remove that temporary IfcSpace. The final
Supply Backbone.ifc contains no artificial architectural space or room-area
source. This reference container is not an actual building level. Saved native
wall profiles,meshes,mass,ports,global source coordinates,flow/dimension metadata
and schema are checked again after export. GUIDs use the explicit namespace.

Outputs also retain model-input.json,source junction review,internal authoring
verification and backbone.json. Source and generated-artifact inventories are
hashed. All original workflow requirements remain in the record. Pending trim,
connection,installation,product and full design acceptance are explicit.

Use the existing `bsa.clash` with an explicitly sourced numerical policy to expose
the junction problems. Do not waive intersections merely because source sections
share a node. Numerical mesh thresholds are not installation clearances. A
geometry pass for individual walls does not mean the overall assembly passes
clash or physical-connectivity checks.

Ten focused tests cover source coverage,missing basis,flow drift,real saved
native walls,stable identities,metadata tampering,container export and late
source mutation. Full native/CAD source execution is recorded separately in
[executed evidence](evidence/duct-backbone-ifc.json). Full regression remains
the separately documented non-green2026-11-11 result.

Actual execution authors all47 selected source sections and94 owned ports,with
native profiles/mesh/mass and exact source dimensions/flows/endpoints verified
after final schema-valid export. There are no logical port links or artificial
IfcSpaces in the exported file. The actual scenario explicitly assumes a0m
reference datum,0.8mm wall and nominal-as-clear-internal dimensions;these are not
validated installed values or a fabrication specification.

The existing clash engine covers all47 wall geometries and detects48 intersection
pairs,all sharing original source nodes. No nonadjacent pair intersects in this
scenario and no solid pair remains unverified. No contact waiver was added:
clash_calculated_checks_pass remains false and physical trim/connections remain
incomplete. A separate actual exported-mesh preview was inspected;independent
BIM-viewer review and full engineering acceptance remain pending. This provides
the complete source straight-wall study needed for subsequent junction design,
not an accepted connected BIM network or installation model.
