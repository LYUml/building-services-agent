# Finite VAV equipment space study

The actual coordinated Connection_Layout now has20finite candidate casing
envelopes and60reserved spaces in a separate saved IFC, native DWG and inspected
PDF. Existing89network bodies and all original STEP records remain unchanged.
These are source-dimensioned proxy envelopes, not connected equipment products.

Applying the existing course8m/s branch target to proposed nominal round inlet
ducts changes the smallest capacity/control/velocity candidates to7size12 and
13size14. Maximum nominal inlet-duct velocities are5.8848–7.9496m/s. The earlier
capacity-only9/10/12study remains preserved. Undersized actual collars give
over8m/s at VAV01/12; this is retained separately, not declared a manufacturer
internal-collar limit failure. All40new candidate static estimates reuse the
prior bounded source queries; none is substituted for total-pressure loss.

Krueger MiniCatalog printed A2-7 provides casing dimensions. Its single-duct IOM
PDF6 Step2A recommends3D upstream straight and PDF3 recommends18in controls
access. Actual source pages were rendered and inspected. A new stated datum
assumes each original abstract VAV point is the inlet collar entrance centre.
Study elevation remains z=0. Both-side control/access reservations conservatively
cover casing length and height; actual handedness/control enclosure is unselected.

All80saved box meshes independently reconcile. Existing Manifold checks find
20overlaps, all between an inlet reservation and existing rectangular duct;
no casing/network overlaps. These20locations need actual duct replacements,
not contact waivers. This does not verify architecture, installed clearances,
insulation, supports, distribution plenums, flex routes or acoustic acceptance.

Existing GUID-linked native projection/AutoCAD adapters save and reopen193drawing
entities and represent169native product GUIDs. The actual final monochrome A4
PDF was inspected: bold casing outlines and dashed reservations are distinct,
and titles/legend/notes/reference show no observed clipping or overlap. At1:200,
the10m reference measures49.995667mm against50mm. Earlier failed reference-layer
and color-dependent trials remain private history, not delivered.

Agent reuse improvement: obstacle_boxes now accepts output only in the repository
or an explicitly host-selected BSA_PROJECT_ROOT, and supports an optional explicit
native body-context ID. Ambiguous/missing contexts remain rejected. This actual
source model contains17Body contexts, so source context10 is explicitly chosen;
none is deleted or merged. Four obstacle tests and six projection tests pass,
including external-output rejection/authorization and multi-context selection.
No new geometry engine, dependency, solver or old-receipt rehashing is introduced.

Course artifacts are under03_Design_Drawings/Connection_Layout/VAV_Equipment_Space;
the revised20group calculations are in05_Calculations/Connection_Layout/
VAV_Equipment_Space_Check.json. Detailed private evidence is under07_Agent_Work/
runs/vav-finite-placement. See [safe evidence](evidence/vav-equipment-space.json).

Remaining engineering: replace20inlet duct portions with source-backed finite
interfaces, author discharge distribution and flex connections, select controls/
acoustics, reconcile pressure stations and close the32rigid fitting numerical gaps.
Full project/design acceptance remains false.
