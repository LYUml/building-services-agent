# Replaceable saved IFC polygon-space providers

The same `spatial.ifc-room-recognition` request with exact `ifc` and `settings`
sources now supports two trusted implementations:

| Provider | Geometry path | Additional runtime |
|---|---|---|
| moosas.ifc-room-recognition | Native IFC prism extraction → pinned MOOSAS surface transform → source correspondence | Explicit clean MOOSAS checkout/dependencies |
| ifcopenshell.polygon-spaces | Native saved IFC prism extraction and closed-solid checks | Installed pinned native IFC/Manifold/Shapely stack |

Both retain complete source GUIDs,planar boundaries,areas,heights,elevations and
source replay through `bsa.spatial-polygons/1`. Native/generated IDs remain
provider-specific. `point_grid_m` is1e-9for the explicit MOOSAS grid and null for
no additional native-adapter snapping. Null does not mean native kernels have
zero error or no internal tolerances. Existing source/method/schema pins require
fresh runs after this compatible schema expansion;do not edit old receipts.

Select the native provider on the existing public IFC workflow without changing
the source plan or passing MOOSAS directories:

```powershell
.venv/Scripts/python -m bsa.workflow execute runs/ifc-inputs/plan.json --out runs/native-polygon-workflow --module-provider recognition=ifcopenshell.polygon-spaces
```

Use `--disable-module-provider ifcopenshell.polygon-spaces` to keep the selected
task and its dependent work pending. Unsupported cross-capability replacements
reject before output. Both providers support the explicitly host-selected
project workspace;verification requires the same selection.

Actual same-request trials on the saved synthetic concave/box IFC preserve all
three GUIDs and14/24/30m2areas. Height/elevation and polygon-boundary comparisons
pass;the downstream bound HK lighting projects are byte-identical. The selected
office LPD checks pass against pinned official source bytes while full acceptance
remains pending. Native disabled and external-project trials also execute.
Twenty-five distinct related tests pass. See evidence/polygon-provider-replacement.json.

This demonstrates a replaceable geometry-intake interface. Both implementations
share ifc_space_surfaces and its native prism checks;the comparison is not an
independent geometry-kernel or architectural-recognition validation. It does not
establish arbitrary wall-to-room recognition,thermal readiness,MEP routing,
photometry or whole-project conformity. All source restrictions in
IFC_SPACE_SURFACES.md remain,including rejection of holes,curves/slopes and
unsupported bodies. The native adapter directly reads declared IfcSpace bodies;
it does not run MOOSAS recognition algorithms or substitute a simulation result.

No new engine/dependency is added. Native operations reuse pinned IfcOpenShell
0.8.5,Manifold3D3.5.4,Shapely2.2.0and NumPy2.5.4. Existing third-party attribution
and licences remain in THIRD_PARTY.md. The shared settings parser now lives with
the neutral IFC intake rather than inside the MOOSAS-specific provider.
