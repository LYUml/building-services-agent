# Finite VAV inlet connections

Twenty actual local rectangle-to-circle transition and3D round-lead assemblies
now exist as saved IFC:40hollow bodies,80owned ports and20real local connections.
They use the actual recentered branch profiles and revised12/14in candidates.
The original89body network and equipment-space study are preserved separately;
its rectangular duct ends have not yet been cut and connected to these assemblies.

## Executed upstream reuse

The pinned existing IfcOpenShell0.8.5 MEP transition helper was actually tried on
all20profile cases. Its fixed16vertex circles exceed the existing20micrometre
cap budget; none is adopted and no package code/tolerance is patched.

CadQuery2.6.1 and cadquery-ocp7.8.1.1.post1 execute in a separate environment.
The common `bsa.cadquery_rect_round` worker adds validated input/output and
provenance glue around upstream ruled loft, union, difference and STEP export.
All20actual cases give valid single CAD walls; each exported STEP is reimported
to verify metre/mm consistency. Four input controls pass, including nonfinite,
path traversal, duplicate/reserved Windows IDs and undeclared fields. The
executed20common-worker BRep hashes match the project prototype exactly.

Direct advanced wall serialisation and large face-based trials remain rejected
private history. The successful compact path serialises positive outer/inner
loft operands and reuses native IFC Boolean difference. Exact coincident vertex
records share entity identity without changing coordinates. Five shared analytic
profiles serve20world placements; saved IFC is411910bytes. No mesh simplification,
face filling, normal repair or tolerance widening is used for the delivered IFC.
The IFC composer remains project-executed glue, not a registered general MCP.

## Engineering and verification

Independent native reopening checks all20transition walls/cap annuli, inner and
outer radii/corners, source frames and owned ports. Maximum circular cap chord
error is2.217683micrometres. All20round leads have native circular hollow profiles
and source-backed3D lengths. All20connected cap frames coincide with opposed
normals; nominal analytic material radii match. Product collar/seal fit is pending.

Raw unchanged numerical clash policy finds40valid bodies, zero intersections and
20unwaived connection clearance findings. Installed clearances are not verified.
Existing fluids1.3.1 Darcy calculations use inherited density1.2kg/m3,
viscosity1.81e-5Pa.s and roughness0.09mm. Maximum round straight friction ranges
1.141741–2.067883Pa. Transition/joint losses and complete local/system pressure
remain null. The original rigid31conditional/32unknown result is not a fresh
pressure result for an integrated inlet scenario.

The0.3m taper, two50mm collars,0.8mm section-plane wall offset and80mm retained
rectangle are declared geometric design assumptions. This wall model is not a
constant sheet-normal fabrication thickness. Source length budgets require five
proposed VAV inlet shifts:03/04approximately0.1133m,15approximately0.1311m,
16approximately0.4268m and17approximately0.3085m. These positions are not adopted
equipment/architecture acceptance; source terminal positions/flows remain fixed.

Actual saved-native longitudinal material sections provide five representative
families covering20cases. The section method reuses pinned trimesh5.2.0 mesh-plane
intersection after the raw silhouette union trial rejects numerical slivers.
Native AutoCAD saves/reopens1266entities with1251GUID-linked entities;10native
representative GUIDs appear, not all40bodies in a whole-network plan. Actual A4
PDF inspection finds no observed label/note/reference clipping or overlap. At1:10,
the0.5m reference measures49.995667mm against50mm.

Course outputs:Connection_Layout/VAV_Inlet_Connections contains IFC, DWG, PDF and
20editable local-coordinate STEP sources. STEP declares mm; IFC uses metres and
proposed world placements. Derived20row/180cell HTML preserves unknown complete
pressure. Safe evidence is [here](evidence/vav-inlet-connections.json); detailed
private source/runtime/rejected trials are under07_Agent_Work/runs/rect-round-cadquery.

Next: trim and bind20source rectangular duct ends, integrate these actual local
assemblies into one network, refresh source geometry/flow/pressure evidence, then
resolve equipment collar/discharge/plenum/flex and remaining loss-data gaps.
Full goal, installation and engineering acceptance remain incomplete.
