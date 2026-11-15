# CFD mesh boundary verification

The two actual BSE3227 plenum air domains now have layered tetrahedron/prism meshes: 340380 points / 823552 cells and 359493 points / 869970 cells. This extends the earlier geometry-only air-domain milestone; it does not accept pressure.

Existing pinned Gmsh 4.15.2 generated wall-only layers (10 micrometre first layer, 22 layers, growth 1.3). Discrete cap nodes drifted approximately 42 micrometres; the private export explicitly projected them to original source port planes within a 100 micrometre preparation budget, then rechecked positive cell quality and volumes. Original meshes are preserved. Final five-port plane errors are zero; circular tessellation area error is approximately 0.04015 percent. These are numerical preparation checks, not product tolerances.

Closed-cylinder layer seams also exported 1496 internal wall faces per family. The new stdlib-only `bsa.cfd_mesh_boundary` counts volume-face incidence and, only with explicit opt-in, removes wall marker faces shared by two cells. Volume connectivity and coordinates remain byte-identical. Duplicate cells, nonmanifold faces, duplicate or missing exterior faces, foreign faces, inward/degenerate orientation and internal inlet/outlet faces fail closed. Correct meshes pass unchanged.

Both actual final CLI outputs match the independently checked meshes in exact ordered line content and byte-identical volume/point prefixes. Whole-file bytes differ only in marker header line endings; full byte identity is not claimed. Four targeted tests cover repair preservation, opt-in, malformed topology/orientation and host/output controls. [Executed evidence](evidence/cfd-mesh-boundary.json) binds the final method and actual mesh hashes. Raw large meshes and private run records stay in the selected coursework workspace.

Run with explicit host `BSA_PROJECT_ROOT` and project-relative paths:

```text
python -m bsa.cfd_mesh_boundary --mesh input.su2 --report new-check.json
python -m bsa.cfd_mesh_boundary --mesh input.su2 --report new-check.json --output-mesh new-mesh.su2 --remove-internal-walls
```

Inputs and existing outputs are never overwritten. Supported scope is serial single-zone 3D linear tetrahedron/prism volumes and triangle/quad markers. This adapter adds no mesher, solver, dependency or MCP. Gmsh 4.15.2 (GPL-2.0-or-later) remains the upstream mesh engine; IfcOpenShell 0.8.5 (LGPL-3.0-or-later) supplies native source geometry. See [air-domain provenance](PLENUM_AIR_DOMAIN.md).

Boundary verification does not check cell Jacobians, source geometry, port identity, grid independence, turbulence, convergence or physical applicability by itself. Separate actual geometry checks are recorded in the evidence. Manufacturer internals, lining/roughness and inlet conditions remain uncertain. All 80 plenum losses and four compound-main losses remain missing per flow case; no fan pressure or engineering acceptance is claimed.
