# Source-native CFD air domain

The actual compound junction follows two corridor bends with short straights.
Isolated tee/cross coefficients therefore remain unsupported. A separate fluid
domain now includes four upstream products, the junction, six transitions and
four downstream straights. Original course geometry and drawings are preserved.

`bsa.cfd_air_domain` exports clear-air OpenCASCADE BREP through IfcOpenShell
0.8.5 from a scratch in-memory IFC4 model. Hollow rectangular sweeps retain
saved placements/directions. Difference solids intersect void and outer envelope
to trim wall-construction overshoot. Explicit metres and unscaled revolution
radians are required. Unsupported representations fail. The helper replaces the
scratch product representation: never save that model over the source.
Four unit tests and six actual-source rejection controls pass. Fifteen real air
solids replay unchanged after newline normalization.

Gmsh fuses all fifteen into one 16.4627295912 m3 volume, matching their sum.
Five saved port planes, centroids and clear areas identify inlet/outlets.
Independent exported-mesh face checks confirm cap areas, planes and outward
orientation, with no missing exterior, duplicate boundary or nonmanifold face.
The layered SU2 export has 90,372 used nodes, 31,319 tetrahedra and 164,580
prisms. All volumes are positive; volume differs from OCC by 0.002456%.
The raw Gmsh node count includes unused nodes. These checks do not prove adequate
flow resolution, mesh independence or turbulence-model applicability.

Actual SU2 SST startup and finite-iteration runs execute. Standard wall functions
reject roughness; the separate smooth diagnostic stopped before iterations.
Wall-resolved rough runs execute but are not converged; no pressure is adopted.
Mesh integration identified reduced inlet flux at shared no-slip edge nodes.
A separately normalized trial preserves prescribed total flow with an assumed
inlet profile, not a measured one. Outlet control remains unresolved.

Public coursework artifacts under Network_Study/CFD_Air_Domain contain the actual
closed analysis BREP, scope notice and check JSON. This is analysis geometry,
not duct material, an accepted pressure design or new native DWG delivery.
See [executed geometry evidence](evidence/cfd-air-domain.json).
Remaining work includes turbulent reference verification, all outlet flows/global
continuity, y-plus, refinement, roughness equivalence and pressure accounting
without double-counting included bends and straight friction. Existing pressure
ledger gaps remain open.

Upstream reuse and attribution:

- [IfcOpenShell 0.8.5](https://github.com/IfcOpenShell/IfcOpenShell/tree/v0.8.5),
  LGPL-3.0-or-later: existing native geometry engine.
- [Gmsh 4.15.2](https://gmsh.info/), GPL-2.0-or-later: isolated meshing runtime;
  wheel SHA-256 is pinned in the evidence. Layer extrusion follows the official
  [tagged 3D example](https://github.com/live-clones/gmsh/blob/gmsh_4_15_2/examples/api/naca_boundary_layer_3d.py).
  Runtime and example source are not redistributed here.
- [SU2 8.6.0](https://github.com/su2code/SU2/releases/tag/v8.6.0), LGPL-2.1:
  official Windows OpenMP archive verified by published SHA-256, pinned commit
  7048fd35f56d4bf52e586429d6746a36a10255f8. Configuration and boundary behavior
  were checked in that source. Synthetic laminar runtime checks do not validate
  this turbulent multi-branch project. Binaries/environments stay private.

## Executed numerical-window assessment

`python -m bsa.cfd_convergence --history RELATIVE_HISTORY --targets RELATIVE_TARGETS --output NEW_REPORT` requires an explicit host `BSA_PROJECT_ROOT`. It reads saved SU2 history using Python CSV and the pinned SU2 output field meanings; it does not rebuild a flow solver. Paths stay within the host project, existing evidence is preserved, and observation changes fail for retry of the same run. Signed conservative targets are required. All flow and global mass checks must pass throughout 200 consecutive iterations; positive whole-domain pressure differences must also remain within the stated relative range. Default flow/mass targets are 0.1%, pressure range 0.5%; these are numerical design targets, not regulations. Common gauge drift cancels when forming total-pressure differences.

Six tests pass, including actual CLI execution, outside-project rejection, existing-evidence preservation and false-pass controls. The command executed on actual first-order, coarse second-order and fine second-order histories. All three recorded windows remain numerically pending; engineering acceptance is always false, including for a passing numerical window. Evidence: [cfd-convergence.json](evidence/cfd-convergence.json). Raw histories and fields stay private. The coursework target file records inherited design mass flows and assumed density, not measured operation. No complete fan duty, junction-only loss or ADPI acceptance follows.
