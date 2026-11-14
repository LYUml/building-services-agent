# Open lined plenum construction candidate

Twenty source-positioned J-plenum solid envelopes are replaced in a separate
saved IFC by native CSG material surrounding an open chamber and four circular
outlet collars. Each has one rectangular entry and four outlet mouths. This is
an actual construction improvement over an occupied box, not a fabricated or
manufacturer-accepted terminal assembly. All644other element representations,
664element placements and1287port frames/directions remain unchanged. Source
files and earlier pressure studies are preserved.

The existing source-bound IFC class/system/port workflow and pinned official
IfcOpenShell0.8.5 ShapeBuilder extrusion/Boolean primitives are reused. The thin
lined_plenum_geometry adapter authors outside chamber/collars minus connected
air cores. It does not implement a geometry kernel or a pressure correlation.
Existing Manifold3.5.4 mesh checks, primitive bounds, trimesh sections and native
AutoCAD/ezdxf delivery are reused. No new dependency/runtime/MCP is introduced.

## Construction basis

The held LMHS2021MiniCatalog SHAba747af8d424da4e59b0d4d93c888bd9b5df299d303c0824fa89f9305870d766,
PDF8/9 printedA2-10/11, is actually viewed. It supplies12/14inch-unit W/H,
36inch chamber length, J4outlet pattern,9.875inch collar outside diameter,
3.375inch projection and6.375/14inch outlet placement dimensions. Standard
half-inch liner is selected for this candidate.

Metal thickness0.8mm is an explicit design assumption, not a verified conversion
of the catalogue's22gauge designation. W/H are interpreted as outside envelope
dimensions; actual clear-bore correspondence remains unverified. Collars are
assumed unlined. Combined metal and liner occupied volume is modelled as one
material solid, not separate material quantities. Balancing damper blades,
slip-drive overlap, seals, fabrication joints and liner-edge treatments are not
modelled. No density or mass is inferred for the combined volume.

Candidate100port areas are derived from the saved declared construction and
stored as candidate geometry properties, with manufacturer-clear-area and
physical-joint verification false. The200max/min port-flow rows use inherited
design demand and the existing assumed1.2kg/m3density. These values do not replace
the historical unknown manufacturer areas or provide product loss coefficients.

## Executed verification

All20saved native material meshes are read back. Each forms one positive closed
connected material solid, with Euler characteristic-6 for its five-mouth wall.
Volumes match independent box-minus-air-plus-collar integration within the
declared0.2%meshing budget;100native material caps match independent ring/border
areas within0.5%. These numerical meshing budgets are not fabrication tolerances.
An independent connected chamber/four-cylinder air probe has no material overlap
in each candidate. A blocked-inlet mutation produces a positive intersection and
is rejected by the same probe criterion. IFC schema/EXPRESS has0issues.

Replacing representations initially left20orphan ProductDefinitionShapes and
failed schema validation. The accepted run uses official unassign/remove APIs
before assignment and passes fresh geometry/schema checks; that failed model
is private and is not delivered.

The earlier604body collision proof is reused only for unchanged584bodies and
new material within the old20occupied boxes. Bounds independently reconcile
those20boxes. Eighty added external collar stub AABBs have no positive overlap
candidates against unchanged584body bounds, other old boxes or other collars.
There is no whole-network remesh or installation-clearance acceptance claim.

All80downstream reducer joints retain unresolved material-cap/sealing/insertion
correspondence. Saved reducer inlet bore0.254m differs from candidate collar
outside0.250825m and clear bore0.249225m. Coincident port centres do not make a
sealed butt or slip joint. No pressure loss is invented for these joints.

## Native delivery and remaining work

Two actual saved size-family representatives supply six material sections:
plan, longitudinal and outlet cross-section. The1:12.5DWG is actually saved,
reopened and exported;225entities and their geometry/text/XDATA reconcile.
The0.25mreference measures20.024mm on the actual PDF versus20mm expected. The
actual PDF is rendered/viewed after moving the upper plans clear of the subtitle.
No observed clipping remains. Numerical checks do not substitute for that review.

Course Open_Lined_Plenum_Candidate folder contains IFC,DWG,PDF and review scope.
The two calculation CSVs contain200candidate port rows and80joint-review rows;
Open_Lined_Plenum_Check.json matches docs/evidence/open-lined-plenum.json.
Pressure, manufacturer internals, damper/control behaviour, source-plane/joint
acceptance, ADPI and final unified delivery remain unfinished.
