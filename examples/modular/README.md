# Public modular pipeline

For common native IFC authoring followed by water analysis without repeated
pipe dimensions or node elevations:

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/modular-bound-water-plan.json --out runs/public-modular-bound-water
.venv/Scripts/python -m bsa.workflow verify runs/public-modular-bound-water
```

This creates the saved model and materializes its exact IFC request automatically.
The synthetic source/geometry and numerical checks execute;manual review remains
pending,so execute exits1. Static head is metres of water. No products,HK compliance,
physical fitting acceptance or complete installation drawing set is inferred.

The independent steady-water example uses the existing WNTR1.5.0/EPANET2.2
engine through a typed analysis provider:

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/modular-water-plan.json --out runs/public-modular-water
.venv/Scripts/python -m bsa.workflow verify runs/public-modular-water
```

Use a new output directory. The synthetic graph is declared,not native-bound.
The execute command exits1 while the manual review remains pending;inspect
actual task results. Completed numerical failures and absent solver results stay
distinct. Static pressure head in metres of water is neither Pa nor total source
pressure. No electrical pump power or Hong Kong compliance is inferred.

This independent synthetic example executes native IFC authoring,selected
spatial exchange and annual thermal input preparation from checked-in sources.
It needs no previous runs or manually generated module request. It reuses the
existing thermal-ifc BIM/template/mapping and attributed Chicago weather example.
Those inputs are synthetic and are not Hong Kong project/regulation facts.

From the repository root,install the pinned optional dependencies in your chosen
environment,then use a new output directory:

```powershell
.venv/Scripts/python -m pip install -e ".[bim,modules]"
.venv/Scripts/python -m bsa.workflow execute examples/modular-plan.json --out runs/public-modular
.venv/Scripts/python -m bsa.workflow_status examples/modular-plan.json runs/public-modular
.venv/Scripts/python -m bsa.delivery template examples/modular-plan.json runs/public-modular --out runs/public-modular-review.json
```

Expected execution: model/spaces/thermal pass,annual/review pending. Exit2 retains
that unfinished work;inspect workflow.json and index.html. Native IFC schema/body/
port checks and source-linked preparation are not a complete engineering design.
Actual model visual review,thermal applicability,performance,MEP routing and
drawings remain required. No native DWG/RVT acceptance is claimed.

To use the pinned MOOSAS runtime already configured per docs/MODULES.md:

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/modular-plan.json --out runs/public-modular-moosas --module-provider spaces=moosas.box-space-exchange --moosas-upstream tools/moosas-review --moosas-deps tools/moosas-exchange-deps
```

MOOSAS is Apache-2.0 at dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c;
IfcOpenShell0.8.5 is LGPL-3.0-or-later. Existing source/attribution remain intact.
Both actual routes produce equal bound thermal projects. Disabled or missing
spatial runtime blocks thermal/annual tasks while the independent manual review
remains visible. Supplying --energyplus routes to the existing engine adapter;
that inherited simulation is unexecuted on this restricted host. Do not bypass
host controls or interpret prepared inputs as simulated results.

The binding-only request.json is an inherited request template. The workflow
materializes spaces/request.json from the exact newly authored model,then runs
the provider in spaces/exchange. A replacement IFC in the template is forbidden.
All dimensions and IDs come from saved solids and explicit mapping. See
docs/MODULES.md and docs/evidence/public-modular-pipeline.json.

For a separate scoped office LPD check,lighting-basis.json provides an explicitly
synthetic inventory/applicability basis for the same saved-space GUIDs. The
spatial_lighting_rules consumer derives area from the neutral result and reuses
the pinned HK pack/official source;see docs/MODULES.md for commands. Those
assertions and watts are test data,not product ratings or statutory decisions.

To put native authoring itself behind the module boundary,use the second public
plan (same original synthetic inputs):

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/modular-authoring-plan.json --out runs/modular-authoring
```

model uses ifcopenshell.bim-authoring and returns a verified model-artifact/1
payload. Downstream spaces inherit that actual IFC and require the same frame.
Use --disable-module-provider ifcopenshell.bim-authoring to retain unavailable
authoring and blocked consumers,or override spaces with the MOOSAS host options
above. There is one verified authoring implementation;this does not prove
Revit/AutoCAD authoring substitution or full design acceptance.

For native centreline drawings from a common model artifact:

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/modular-drawing-plan.json --out runs/modular-drawings --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe'
```

This independently declared synthetic ring reuses the existing6-pipe source,
not the thermal example. It saves3DWGs,independently reopens them and plots an
A4 plan/front/side set at1:50. Source profile/port/GUID checks and per-sheet100mm
references remain mandatory. Omit --autocad to retain native work as pending.
Actual execution and all3merged rendered pages were checked;review still stays
pending for hydraulic/product/hidden-line/fitting/equipment/installation and full
engineering acceptance. See docs/evidence/modular-native-drawings.json.

For a separate declared rectangular air-tree budget:

```powershell
.venv/Scripts/python -m pip install -e ".[modules,network]"
.venv/Scripts/python -m bsa.workflow execute examples/modular-analysis-plan.json --out runs/modular-air-budget
```

This reuses rectangular-air/project.json through fluids.rectangular-air-budget.
The real existing calculation runs without native CAD/energy engines. Numerical
pressure/velocity/continuity results remain distinct from execution completion;
failed criteria block required downstream tasks. Raw branch/node JSON,CSV and
HTML are retained. The geometry,flows,K and targets are explicit synthetic test
inputs;geometry_bound=false. Operating fan selection,physical routes,acoustics,
code and full design acceptance remain pending. See docs/MODULES.md.

To bind a rectangular budget to newly authored native geometry:

```powershell
.venv/Scripts/python -m pip install -e ".[modules,bim,network]"
.venv/Scripts/python -m bsa.workflow execute examples/modular-bound-analysis-plan.json --out runs/modular-bound-air
```

This reuses the synthetic hollow duct and geometry-free network template.
Saved solid/profile/port/connection checks must match the canonical source before
geometry is analysed. Flows,roughness,K and targets remain explicit. See
docs/MODULES.md for the distinct bound contract and actual bend/failure controls.
Junction/fan/product/installation/code acceptance remains pending.

For a fixed-speed fan intersection on that exact verified path:

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/modular-fan-plan.json --out runs/modular-fan
```

The existing synthetic total-pressure curve feeds the existing single fixed-
terminal free-flow solver. Geometry and the baseline analysis are inherited
through explicit artifact references. No flow/pressure values are copied by
hand. A converged point can still fail capacity;no root stays failed with no
extrapolation. Air power is not electrical motor input. Source/result replay
and original-target checks retain pending product/installation/code acceptance.
