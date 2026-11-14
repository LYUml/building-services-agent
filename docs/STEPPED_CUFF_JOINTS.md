# Proposed stepped outer sleeve joints

The saved open-plenum candidate has collar outside250.825mm and reducer
inside254mm/outside255.6mm. Instead of moving the existing branches, a separate
model adds a proposed stepped-bore external sleeve and two bondline geometry
proxies around each of80junctions. Original664element representations/placements,
1287port frames/directions and603flow connections are unchanged. Eighty
IfcRelConnectsWithRealizingElements relations identify the160new nonflow
IfcDiscreteAccessory objects and their source plenum/reducer. No manufactured
connector is selected or its performance invented.

This is a custom geometry proposal, not a verified standard joint. Half-length
25.4mm, nominal bondline0.8mm and minimum sleeve wall0.8mm are design assumptions.
The derived outer diameter is258.8mm; upstream sleeve wall is3.1875mm. It must not
be described as a uniform0.8mm sheet-metal sleeve. Both overlaps remain within
the saved exposed collar and reducer straight inlet, avoiding the taper. Mechanical
fasteners, manufacturing tolerances, cure/shrinkage, adhesion, product approval,
structural pressure class and leakage testing remain unresolved.

The current official Foster32-19PDS R0519NP was downloaded from its product-page
link, pinned SHAfd9011c4b1c47891bc675371b94f6bfad3e4bc693b6be66ab4f9019118df87eb,
and its metal-application page2 was rendered/viewed. It describes coating mating
metal surfaces and treating the external seam and screw holes. That section is
separate from UL181flexible-duct closure. It does not approve this sleeve or specify
its assumed cured bondline thickness. The model0.8mm must not be inferred from
the product's wet-film guidance. No wet coverage or nonvolatile fraction is
converted into an installed quantity or purchasing allowance.

## Executed upstream reuse and verification

The thin stepped_cuff_geometry author uses the pinned official IfcOpenShell0.8.5
polyline-profile/full-revolution/placement APIs. Two new whole product shapes are
shared by80instances each; individual bare representations are not shared.
Existing Manifold3.5.4, native source reducer readers, primitive bounds,
trimesh/Shapely sections and AutoCAD/ezdxf adapters are reused. There is no new
geometry kernel, pressure solver, dependency or K-Select MCP.

Two canonical native product meshes give one sleeve solid and two disconnected
bondline solids. Positive volumes match independent annular integration within
the declared0.5%meshing budget, which is not a fabrication tolerance. All160saved
instances have the exact shared shapes and proper rigid source frames. All160
upstream/downstream radial sections reconcile source metal, nominal bondline and
sleeve intervals without a nominal gap. Native air probes, inset50micrometres
from the source bore radii, have zero accessory intersection. Omitting the bondline exposes an0.8mm
radial gap in the control. These are nominal occupancy checks, not a leak-rate test.

Added accessory bounds show no positive overlap candidates with unrelated source
bodies or other joints. Intended related contacts use explicit saved radial
profiles and overlap lengths, not a generic clash waiver. Existing pressure
contributions, missing joint losses and source-application gates are unchanged;
no zero joint coefficient follows from an external sleeve.

The new824element IFC passes schema/EXPRESS. Its flow distribution subset remains
604products; accessories are not new flow spans or terminals. The actual1:2DWG
is saved/reopened/exported with67entities and47GUID-linked entities matching the
source. Four actual product sections show collar,reducer,sleeve and bondlines.
The20mmreference measures9.991mm versus10mm expected on the saved PDF, which was
actually rendered/viewed. The final monochrome legend identifies nested contours
and the reference axis without relying on colours absent from the plotted sheet.

Course Stepped_Joint_Candidate folder contains IFC,DWG,PDF and review scope;
calculation files contain the80row joint schedule and Stepped_Cuff_Joint_Check.json.
The latter matches docs/evidence/stepped-cuff-joints.json. Manufacturer sources,
images and private execution records remain excluded. This candidate is available
for review; it is not adopted as an installation-ready standard connection.

Source: https://fosterproducts.com/wp-content/uploads/2017/01/Foster-PDS-32-19-R0519-NP.pdf
