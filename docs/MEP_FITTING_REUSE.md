# Finite MEP fitting reuse investigation

The physical-fitting gap remains separate from single-line correspondence and
nominal plan projection. Before adding a rectangular junction/transition adapter,
the installed upstream library and an existing Revit package were inspected.

Installed IfcOpenShell0.8.5 exposes ShapeBuilder.mep_transition_shape and
mep_bend_shape. Its inspected ShapeBuilder method inventory has no tee/junction
helper; this does not establish absence across the entire upstream ecosystem.
Current online documentation describes0.9.0post1, so its API claims were checked
against the actual0.8.5 source rather than assuming an upgrade. Existing library
licensing/attribution in THIRD_PARTY.md remains applicable; no source bodies or
binaries were copied.

`scripts/probe_ifc_transition.py --out runs/new-transition-probe` exercises the
actual installed helper, saves IFC, reopens through its native geometry kernel,
and independently checks mesh edges/bounds/volume. Optional --hollow-profile
supplies synthetic5mm IfcRectangleHollowProfileDef inputs. Both actual probes use
synthetic0.6x0.3m to0.4x0.2m profiles,0.1m straight ends and30-degree helper input.
The helper produces0.3732050808m transition length and28 mesh triangles. Both
saved geometries have closed mesh edges and0.07327264356m3 volume, exactly matching
the independently integrated filled outer envelope. The hollow-profile input does
not make this generated representation a wall-material solid. Neither call creates
ports; it is a shape helper, while separate upstream system APIs support ports.
Executed public evidence is in evidence/ifc-transition. No manufacturer dimensions,
loss coefficient, accepted wall construction or production integration is implied.

Follow-up `scripts/probe_ifc_transition_wall.py --out runs/new-wall-probe` reuses
that exact upstream envelope probe, generates a smaller inner transition through
the same helper, converts both through upstream faceted_brep and applies native
IFC Boolean DIFFERENCE. The original outer IFC stays unchanged. Synthetic inner
straight ends extend0.1mm beyond the outer caps to form an open bore; this is a
Boolean construction parameter, not a fabrication allowance or changed tolerance.
The resulting saved model has zero schema/EXPRESS issues, a single connected
closed material mesh with Euler characteristic0, and0.00424171760m3 material volume
matching an independent rectangle-prismoid integration. Existing Manifold checks
find zero overlap with a centre through-bore probe. The filled original envelope
is rejected by the same wall-topology checker as a negative control.

This is a centred synthetic **section-plane offset** model:5mm is subtracted from
each side in the section plane, and is explicitly not constant sheet-normal
thickness on sloping faces. It has no ports, pressure coefficient, manufacturer
construction or assembly acceptance. The executed report in
evidence/ifc-transition/section-offset-wall-probe.json records those limitations.
Reuse of a valid solid/Boolean/topology engine has now been exercised; promoting
this research into a production duct-wall or project fitting is still pending.

`scripts/probe_ifc_transition_assembly.py --out runs/new-assembly-probe` now
composes that source-preserved transition with two0.3m straight hollow rectangular
segments using existing rectangular_geometry author/verify and upstream system
port APIs. Unrepresented helper placeholders are removed from the new assembly
copy. The saved three-component model has six owned ports, two directed
connections, opposed/coincident interface frames and exact ventilation-system
membership. Source transition placement/bounds and saved straight profile/body
geometry are checked separately from logical port connections.

Actual native schema/EXPRESS checks return zero issues. The three material meshes
form one connected Manifold union with Euler characteristic0, zero centre-bore
probe overlap, and0.00868171760m3 volume matching independent section/prismoid
integration and the sum of component volumes. Separate saved negative controls
shift a port, a straight solid without its ports, and the transition placement;
all reject. Public evidence is in
evidence/ifc-transition/three-piece-assembly-probe.json.

This remains synthetic centred section-plane-offset transition research, not a
general fitting constructor, constant sheet-normal fabrication model, airflow-loss
solver, product selection or actual coursework assembly. The two end ports remain
external boundaries; a connected local example cannot accept an entire network.

This supports reusing the upstream representation/length machinery in a thin
future adapter, with explicit wall/bore construction, saved material-volume and
through-bore checks, source-backed endpoints/ports and assembly correspondence.
It does not justify labeling a closed outer-envelope mesh as a hollow duct, nor
does it solve rectangular tee geometry or fitting pressure losses.

OpenMEP was inspected at commitb172d526b91bdf818f602dfecbc92a3d77be9645;
adapters/openmep/research.json pins reviewed file blobs. Its Revit Fitting methods
delegate tee/transition creation to Autodesk document APIs and depend on Dynamo's
DocumentManager/TransactionManager and actual Revit Connector objects. The root
license is MIT, but its README separately identifies AGPL-3.0 Miscellany display and
LGPL-3.0 LunchBox dependencies. Review the selected dependency closure before reuse.
No install, build or native execution was performed. It remains a candidate for an
approved Revit/Dynamo host, not a verified independent CLI or a substitute loader
for the currently blocked deployment.

Primary references: [upstream ShapeBuilder API](https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/shape_builder/index.html),
[upstream flow/fitting authoring discussion](https://github.com/IfcOpenShell/IfcOpenShell/issues/2181),
[pinned OpenMEP fitting source](https://github.com/chuongmep/OpenMEP/blob/b172d526b91bdf818f602dfecbc92a3d77be9645/OpenMEPRevit/Element/Fitting.cs),
[pinned OpenMEP README](https://github.com/chuongmep/OpenMEP/blob/b172d526b91bdf818f602dfecbc92a3d77be9645/README.md),
[pinned license](https://github.com/chuongmep/OpenMEP/blob/b172d526b91bdf818f602dfecbc92a3d77be9645/LICENSE.md).
