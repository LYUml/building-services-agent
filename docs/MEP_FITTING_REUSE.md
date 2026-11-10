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
