# Explicit straight circular wall solids

IFC authoring now supports an opt-in hollow round pipe/duct body alongside existing envelopes. This is an actual swept wall solid with a through bore, not a box with diameter labels. It uses the IFC4 [IfcCircleHollowProfileDef](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcprofileresource/lexical/ifccirclehollowprofiledef.htm) in an IfcExtrudedAreaSolid. The wall parameter is calculated from independently supplied outside and inside diameters.

```powershell
python -m pip install -e ".[bim,network]"
python -m bsa.bim examples/circular-network/model.json --out runs/circular-baseline
python -m bsa.workflow execute examples/circular-network/plan.json --out runs/circular-design
python -m bsa.workflow verify runs/circular-design
```

The project explicitly declares `geometry_scope: axis-aligned envelopes and explicit straight circular walls`. A circular device declares `body_shape: straight circular wall`, is an IfcPipeSegment or IfcDuctSegment, and supplies source-backed `properties.InternalDiameter_m` and `properties.OutsideDiameter_m`. Both must be finite and `0 < internal < outside`. Its transverse envelope dimensions must equal outside diameter; its two SOURCE/SINK ports must occupy opposite end-face centres along one world axis. Unknown shape types, ambiguous dimensions, non-axis-aligned routes, off-centre ports and zero-thickness/closed-bore dimensions are rejected. Unmarked devices remain boxes; no shape is inferred from a rating or class name alone.

Input origins still denote minimum envelope corners. A circular body's native placement uses the lower end-face centre and a right-handed frame whose local Z follows the geometric axis. Profile extrusion follows that axis independently of flow direction. Circular port placements use outward end-face axes; a reversed flow does not reverse a wall's geometric interpretation or make both ports face the same way. Original world port positions and stable object/port IDs remain part of the existing checks.

Reopened IFC must retain its actual swept-solid/hollow-profile type, radius, wall parameter and length. The geometry engine independently tessellates the wall. Verification checks inner/outer radial surfaces, bounding extents, consistently oriented edges, connected vertex links and one connected closed material surface with Euler characteristic zero. Closed refers to the material boundary, including annular end faces; it does not cap the fluid bore. Mesh signed volume is compared with `pi*(D_out^2-D_in^2)*L/4` from source dimensions.

The QA mesh uses 1e-5 m linear and 0.02 angular deflection with welded vertices; bounding comparison tolerance is 2e-5 m and relative wall-volume tolerance is 0.001. These are verification tolerances, not fabrication tolerances or a claim of exact mesh circles. Very small/thin or poorly conditioned shapes may fail verification instead of being silently accepted. The stored IFC profile remains analytic. Settings, saved profile dimensions, volumes, topology and outward-port checks are recorded in bim-verification.json. [IfcOpenShell's settings documentation](https://docs.ifcopenshell.org/ifcopenshell/geometry_settings) describes mesher parameters; this project's pinned 0.8.5 runtime was exercised directly rather than upgraded to the documentation site's newer version.

The existing model-aware design bridge preserves the explicit wall flag when resizing from separately sourced inner/outside catalogue dimensions. Source and selected walls therefore both undergo schema, mesh/profile, identity, port and pressure reconciliation. The synthetic 3 m baseline (0.50/0.40 m diameters) has nominal material volume 0.212057504 m3; the selected 0.22/0.20 m wall has nominal volume 0.019792034 m3. No mass, material strength, insulation or thermal property is inferred.

This supports only straight homogeneous circular walls. Bends, junctions, reducers, connected equipment product shapes, material certification and clearance/clash checks remain pending. A numeric geometry pass does not clear the separate BIM-viewer visual gate or complete engineering acceptance. Existing envelope-only inputs retain their contract.
