# Independent synthetic HVAC package

This example builds its own brief, geometry, assumed loads, fictional throw table,
candidate duct dimensions and node-bound drawing. It reads no coursework files.
It demonstrates reusable tool execution, not a completed engineering design.

From the repository root:

```powershell
.venv/Scripts/python -m pip install -e '.[reports,network,gis]'
.venv/Scripts/python examples/hvac-package/build_inputs.py --out runs/demo-hvac-inputs
.venv/Scripts/python -m bsa.hvac_package runs/demo-hvac-inputs/plan.json --out runs/demo-hvac-package --font C:/Windows/Fonts/arial.ttf --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe' --terminal-review runs/demo-hvac-inputs/review.json
```

Use installed font/AutoCAD paths appropriate to the host. Output directories must
be new. The package command exits 2 because full acceptance remains pending; inspect
package.json for actual stage failures. Without AutoCAD, native execution and the
requested terminal review cannot pass. Open the package index.html for artifacts.

The assumed 48 m2 rectangle uses negative and positive coordinates, four terminals,
two two-outlet groups, three rigid sections and 50% minimum flow. Trial cooling is
80 W/m2 with sensible fraction 0.85 and 10 K supply difference; all are labelled
assumed, not regulatory values. The catalogue is fictional interpolation data and
must never be used for hardware selection. Each group has two outlets specifically
to demonstrate that another assignment's four-outlet rule is not hard-coded.

Actual host execution on 2026-11-10 passed allocation, bounded lookup, candidate
sizing, source-bound DXF update, AutoCAD save/reopen/A4 plotting and inherited terminal
review. Independent arithmetic gives 270.3777335984 L/s total, four equal 12 m2 load
allocations and four 2 m planar flexible connections. The 4-page PDF retained 14
numerical rows and six requirement records. The actual drawing and all report pages
were rendered and inspected; workflow and artifact integrity passed. The manual
engineering task and all full-requirement acceptance states remain pending.

This source generator composes existing pinned ezdxf, Shapely, fluids, AutoCAD and
ReportLab adapters; it introduces no new engine. Upstream notices and versions are
maintained at repository level. Adapt real projects from their own brief, source
geometry, manufacturer data and jurisdiction evidence, not these synthetic numbers.
