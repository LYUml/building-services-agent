# Saved continuous cable route drawing

`bsa.cable_route_drawing` is a thin saved-geometry-to-ezdxf adapter for exactly one checked quarter-circle plus tangent-straight cable. It uses the existing electrical IFC reader's mandatory native connected-solid, independent volume/bounds/centroid, ports, anchors and actual length checks before drafting. It does not take schematic Graphviz positions as physical route geometry.

Supply a prepared electrical project, the exact saved IFC and binding, and drawing settings with `projection_axes`, `annotation_height_m` and `source` (the existing drawing-settings contract). Example:

```powershell
.venv/Scripts/python -m bsa.cable_route_drawing runs/continuous-cable-native-workflow-v1/workflow/study/project.json --ifc runs/continuous-cable-native-workflow-v1/combined/model.ifc --binding runs/continuous-cable-native-workflow-v1/combined/binding.json --settings runs/cable-route-settings-v1.json --out runs/new-cable-route
```

The settings used in the executed trial were `{"projection_axes":["X","Z"],"annotation_height_m":0.04,"source":"Synthetic drafting settings; no installation acceptance"}`. Text height and drawing scale are drafting assumptions, not service dimensions or regulatory requirements.

The DXF contains actual circular ARC and straight LINE axes, circular envelope OD outlines, a radial graphic, straight-length LINE/TEXT dimension graphics, true total/arc lengths, bend radius, plane coordinate and full cable IFC GUID. All 16 generated entities carry the actual same cable GUID, rather than inventing separate IFC objects for its pieces. Dimension graphics are not associative CAD DIMENSION entities; regenerate after source changes. The curved piece is never replaced by an endpoint chord. End-on/oblique projections, nonplanar routes and unsupported geometry fail. The selected cable is included; other physical model GUIDs are explicitly listed as omitted and the printed scope note says so. This is not a coordination or installation drawing.

## Reuse and native delivery

The existing hollow-pipe route reader/drawer was inspected before implementation. Its wall/bore labels and per-piece GUID annotation layout are incompatible with a single solid continuous cable, so they are not fabricated. Reused engines/tools: pinned IfcOpenShell 0.8.5 and Manifold 3.5.4 through the existing inspector, ezdxf 1.4.5, existing snapshot/reconcile and IFC identity readers, and `bsa.ifc_native` for guarded copy-only AutoCAD SAVEAS, independent reopen/export, geometry/annotation/XDATA reconciliation and fixed-scale PDF measurement. Existing upstream attribution/licenses apply; no new dependency or geometry kernel was added.

Native settings add only the supported `BSA_CABLE_AXIS` reference layer and `cable-route` drawing name. A selected nonzero saved straight axis is the reference; a chord is not substituted. The executed settings used source text identifying the synthetic X/Z view, `window_drawing_units=[-2.3,1.1,2.7,2.9]`, `scale_denominator=20`, the actual `reference_ifc_guid`, `reference_layer="BSA_CABLE_AXIS"`, `drawing_name="cable-route"`, and `pdf_tolerance_mm=0.2`. Invoke `.venv/Scripts/python -m bsa.ifc_native <route.dxf> --settings <native-settings.json> --out <new-native-directory>` with the installed AutoCAD runtime.

Actual final outputs are in `runs/cable-route-drawing-v2` and `runs/cable-route-native-v2`. The first printed trial exposed insufficient dimension text spacing; it is retained, and v2 separates the text from the line. Saved/reopened geometry, all 16 entity identities/annotations and metre units pass. The 2 m source straight printed at 1:20 measures 99.991333 mm versus 100 mm expected. The final PDF was rendered and visually inspected: the arc/straight/OD geometry is continuous, dimension text is separated, and the source length/radius/scope notes are readable. Duplicate PDF PageMode warning remains; no PDF-conformance assertion is made.

Four projection tests pass (multiple rotations and swapped axes, end-on rejection, wrong midpoint rejection and nonplanar straight rejection). Existing native tests: four pass and one local-runtime-dependent test skips; the separate actual new native trial above executed successfully. An upstream IFC destructor warning occurred while the existing test suite completed. Evidence is in `evidence/pandapower/cable-route-drawing.json`.

Pending: workflow registration with same-model study/bend/coordination gates, obstacle-inclusive drawings and collision-free dimension/label layout for arbitrary rotations, associative/formal dimensions, additional route pieces, manufacturer/support/joint details, actual drawing conventions and complete installation/regulatory/engineering acceptance. Standalone output is not release authorization and does not clear the old missing distribution hardware.
