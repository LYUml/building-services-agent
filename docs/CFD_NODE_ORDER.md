# Pinned CFD node ordering

A thin stdlib-only adapter now handles SU2/VTK four-node tetrahedra (type10) and six-node prisms (type13) versus Gmsh types4 and6. It does not change node identifiers, ID base, coordinates, mesh topology or engineering acceptance.

The actual main mesh exposed an ordering failure: treating SU2 prism nodes directly as Gmsh nodes failed native positive-quality checks. Pinned Gmsh4.15.2 GModelIO_SU2.cpp defines SU2 output as VTK order, and MPrism.h::getVertexVTK gives the map [0,2,1,3,5,4]. This map is its own inverse. Tetrahedra retain their order. The new `bsa.cfd_node_order.su2_to_gmsh` and `gmsh_to_su2` implement that mathematical convention; they do not rebuild a geometry or flow engine. Unsupported types, wrong arity, repeated IDs, booleans, floats and negative IDs are rejected.

```python
from bsa.cfd_node_order import su2_to_gmsh, gmsh_to_su2
kind, nodes = su2_to_gmsh(13, [10,20,30,40,50,60])
assert (kind, nodes) == (6, (10,30,20,40,60,50))
assert gmsh_to_su2(kind, nodes) == (13, (10,20,30,40,50,60))
```

Three targeted tests verify the pinned map, ID preservation and inverse, reference prism handedness, and rejection controls. The new helper also executed on every actual main cell: 234212 prisms and31529 tetrahedra, 265741 total. The inverse of all native Gmsh cells matches the source canonical oriented connectivity; all126183 points correspond within7.106e-15m. Native Gmsh minimum signed volume and SICN remain positive. [Executed evidence](evidence/cfd-node-order.json) binds the helper SHA, verification method, source mesh and output mesh.

This is source-specific ordering replay, not a general format converter, mesh-quality guarantee or OpenFOAM integration. The source main mesh's independent boundary checks remain separate; node conversion cannot certify geometry, source applicability or pressure. No new native DWG acceptance or numerical pressure gap closure is claimed. Target solver import remains unexecuted; the proposed blueCFD installation awaits the user's separate decision.

Upstream: [GModelIO_SU2.cpp](https://raw.githubusercontent.com/live-clones/gmsh/gmsh_4_15_2/src/geo/GModelIO_SU2.cpp), SHA256467a66e6494dc255f74ae541ad7fbb6d263fd07df93518aaad5782f5b1c0085e; [MPrism.h](https://raw.githubusercontent.com/live-clones/gmsh/gmsh_4_15_2/src/geo/MPrism.h), SHA256cd1ba66bb32aa654f12ec155e0132da85fb7049c0af431e94487f8f2ca37e1fc. Gmsh4.15.2 is GPL-2.0-or-later. Existing isolated Gmsh is reused; no new dependency, solver or MCP is added. Raw mesh and private execution files remain in the coursework workspace.
