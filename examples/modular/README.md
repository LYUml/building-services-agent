# Public modular pipeline

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
