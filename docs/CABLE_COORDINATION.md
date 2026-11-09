# Saved electrical model coordination

The source-bound three_phase_coordination adapter now reuses the existing whole-model IFC triangle/Manifold clash engine after checking the same saved electrical cable geometry against its numerical project. It adds a release prerequisite, not a new geometry engine or automatic routing solver. The tested runtime remains pinned IfcOpenShell 0.8.5 and Manifold 3.5.4; existing LGPL-3.0-or-later/Apache-2.0 attribution applies.

## Check scope and retained failure

Cable Body/Axis/port/length correspondence remains mandatory. The existing clash engine then covers all represented non-feature/non-virtual IfcElements, including non-electrical obstacles. Missing or invalid geometry prevents coverage success. Solid material overlap and declared minimum-clearance failures remain distinct. Existing numerical tolerances, Boolean budgets, contact rules and unwaivable material overlaps are unchanged. A topology relationship or matching numerical bus is not an automatic contact waiver.

Actual execution on the earlier two-cable quarter-circle/straight fixture, with a sourced synthetic 30 mm clearance and no contact exceptions, failed clearance at its shared ideal-node endpoint. Geometry coverage passed and material overlap was absent. This failed case is retained; no joint or interface approval is invented to clear it. The positive obstacle tests deliberately isolate one cable with no inter-cable joint. They do not establish feasible multi-cable installation, physical board terminals or full project acceptance.

## Shared obstacle authoring

The previously executed route_obstacles append/save/reopen implementation now lives in obstacle_boxes. The original water-route wrapper keeps its routing/height contract, stable names and BSA_RoutingObstacle metadata; its existing native regressions pass. The new ifc_obstacles adapter accepts explicit box origins/sizes and source records without forcing electrical/architectural data through a water-route search contract.

Inventory version 1 has sources (relative path, SHA256, locator, kind) and a nonempty obstacles list of exact id/origin_m/size_m/source rows. Coordinates are SI metres; source kinds distinguish assumptions, measurements, course data, manufacturer data and design targets. Current native box validation requires dimensions at least 1 mm. Source applicability/completeness is not established merely by attaching a source record.

The shared native implementation requires a metre IFC4 with one project/storey/Body context, appends new proxy boxes to a new file, adds separate containment relationships, compares every original STEP entity record after saving, validates schema/EXPRESS and verifies native closed-box bounds/volume. Duplicate obstacle identities are rejected. Original IFC/input files remain unchanged. Generic boxes have stable COORDINATION_OBSTACLE IDs and BSA_CoordinationObstacle source/inventory hashes. These are declared obstacle envelopes, not surveyed or manufacturer shapes by default.

```powershell
.venv/Scripts/python -m bsa.ifc_obstacles runs/prepared-cable/cables.ifc --inventory examples/cable-coordination/obstacles.json --out runs/new-combined-model
```

The augmented IFC is a new model revision. Refresh the separate electrical geometry binding's ifc_sha256 deliberately, keep its source geometry file, and derive a fresh numerical project from the augmented model. The repeatable runner performs this staging explicitly; it never changes the original source model or silently reuses an earlier study.

## Workflow and scenarios

Workflow task three_phase_coordination requires depends_on on a passing three_phase or three_phase_ifc_project, plus explicit ifc/binding/policy paths. It inherits the project/study pair; replacement project options are forbidden. Exact model/cable-binding and direct/transitive numerical-producer checks apply. Put the task in drawing requires_pass. All nested clash artifacts are pinned; a changed clash.json blocks CAD before invocation.

Electrical IFC readers, including the derived producer, now also bind declared upstream inventory prerequisites to their explicit IFC input bytes. Their numerical depends_on is not misinterpreted as an IFC-export producer. Identical copies are permitted; different-model inventory borrowing fails. This does not add automatic inventory tasks to a plan.

```powershell
.venv/Scripts/python scripts/run_cable_coordination_demo.py --python tools/pandapower-runtime/Scripts/python.exe --graphviz tools/freecad-1.1.4/FreeCAD_1.1.4-Windows-x86_64-py311/bin/dot.exe --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe' --out runs/new-cable-coordination-suite
```

The synthetic one-cable source uses a 30 mm target, not a legal/product clearance. Moving the same box gives three actual outcomes: clear, insufficient clearance without overlap, and material overlap. Both failed scenarios block drawing and preserve the failed artifacts. Unrepresented additional physical elements also fail coverage. The example aggregates both numerical loads at the same terminal bus; it is deliberately not an alternative complete building design.

The actual positive workflow reaches native DWG reopening and an inspected A4 schematic PDF. Diagram positions remain schematic and do not depict the obstacle or physical route. The saved two-element model preview was separately inspected, with no IFC elements omitted; its projections are illustrative and are not full BIM-viewer, installation or engineering acceptance. The [retained evidence](evidence/pandapower/cable-coordination-workflow.json) includes all three outcomes and the unwaived earlier joint failure.

Six new geometry/obstacle tests, six new workflow/inventory-identity tests and 49 related regressions pass (61 distinct tests; the earlier eight-test run also included two legacy route tests counted in the 49). Scope remains source/model checks against declared targets. Source obstacle completeness, actual products/insulation, legitimate physical joint/interface design, manufacturer constraints, full regulations and independent real assignment delivery remain pending.
