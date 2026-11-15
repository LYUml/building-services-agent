# Native plenum air domains

The current BSE3227 lined-plenum candidate now has two actual closed air-volume
BREPs for subsequent analysis. Seven plenums share the smaller construction
dimensions and thirteen share the larger dimensions. Current saved material
representations and port frames match the previously verified construction.

Existing `bsa.cfd_air_domain.serialized_brep` clips the source void union against
the source outside union in scratch memory. IfcOpenShell 0.8.5 provides native
CSG evaluation; Gmsh 4.15.2 OpenCascade independently imports each result. Each
representative has one connected volume, matches independent chamber/collar
volume integration, reconciles all five candidate port areas, and has zero
volumetric intersection with its native material. The source IFC remains intact.
Retaining the parent IfcOpenShell shape during material serialization corrected
an initial empty export; those failed files are excluded from delivery.

The two native air volumes are approximately 0.1403598940 and 0.2002786629 m3.
Existing flow records give different outlet fractions for individual plenums;
they cannot all be assigned four equal flows or a common coefficient. Reusing
geometry can reduce mesh preparation, but Reynolds number, inlet profile,
individual branch fractions and pressure-reference correspondence still require
verification. Componentwise fraction bounds are not one simultaneous flow case.

Course analysis assets are under `03_Design_Drawings/Network_Study/Plenum_Air_Domains`.
Byte hashes and scoped geometry evidence are in
[plenum-air-domain.json](evidence/plenum-air-domain.json). No mesh, numerical
pressure value, manufacturer K or new native DWG acceptance is claimed.
The existing 80 plenum pressure gaps remain open.

Construction assumptions remain: 0.8 mm metal, selected 12.7 mm lining,
catalogue W/H interpreted as outside dimensions, nominal unlined collars and
omitted manual damper blades. These are candidate airways, not a manufacturer's
verified internal model. The earlier [open-plenum study](OPEN_LINED_PLENUM.md)
records catalogue provenance and material/blocked-inlet checks.

Reuse keeps the existing pinned runtimes and licenses: IfcOpenShell 0.8.5
(LGPL-3.0-or-later), Gmsh 4.15.2 (GPL-2.0-or-later), and the existing native air
adapter. No geometry kernel, flow solver, dependency or MCP interface is added.
