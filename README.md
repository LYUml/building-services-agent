# Building Services Agent

需求文档 → 可追溯项目数据 → CAD/BIM → 工程分析 → 设计迭代 → 已核对交付。

A developing agent workspace for building services. The host AI interprets requirements and coordinates scoped tools; pinned engineering libraries and native applications perform calculations and authoring. The complete multi-discipline, document-to-accepted-design goal remains unfinished.

## Start with a real assignment

Open this repository and invoke `$building-services-design` with the brief and source drawings. The skill routes requirements intake, discipline tools, jurisdiction checks and delivery review. Originals and assumptions retain their sources. Private coursework and generated runs stay out of Git.

[Document intake](docs/DOCUMENT_INTAKE.md) extracts passages and creates a requirement matrix. A drafted plan still needs engineering interpretation: a raw brief is not a runnable design. Read [scope and acceptance](docs/ROADMAP.md) and the applicable skill before extending a capability. Check [upstream reuse decisions](docs/REUSE_SURVEY.md) first.

## Run an independent HVAC demonstration

```powershell
.venv/Scripts/python -m pip install -e '.[reports,network,gis]'
.venv/Scripts/python examples/hvac-package/build_inputs.py --out runs/demo-hvac-inputs
.venv/Scripts/python -m bsa.hvac_package runs/demo-hvac-inputs/plan.json --out runs/demo-hvac-package --font C:/Windows/Fonts/arial.ttf --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe' --terminal-review runs/demo-hvac-inputs/review.json
```

Use existing font/AutoCAD paths for the host and new output directories. Open the generated index.html. Exit 2 retains outstanding design acceptance; inspect package.json for actual stage failures. The [public synthetic example](examples/hvac-package/README.md) has executed native save/reopen, A4 plotting, terminal correspondence and reporting, with inspected pages. Its fictional catalogue and assumed inputs cannot select real hardware.

For a reviewed real plan, [package preparation](docs/HVAC_PACKAGE.md) also accepts `--adpi-settings` for source-pinned applicability screening. [ADPI guidance](docs/ADPI_BASIS.md) preserves unknown room loads, installation, product categories and characteristic lengths; an in-range ratio alone is not ADPI verification. [Scenario comparison](docs/AIR_ALLOCATION.md) compares executed alternatives and retains failed sizes without choosing a design automatically.

After saved native-sheet execution, [whole source-tree review](docs/DUCT_SYSTEM_PATHS.md) checks every original section and outlet path against the selected schedule. Include it in the same package command with `--system-paths-native-task <declared-native-task-id>`. Its untrimmed source-centreline friction baseline retains missing fitting trims,losses and boundary conditions;it does not determine complete fan duty.

## Current capabilities and limits

| Area | Executed scope | Remaining scope |
|---|---|---|
| Requirements and orchestration | Source-linked plans, dependencies, input/artifact hashes, retained failures and pending review | General semantic interpretation and complete automatic task planning |
| HVAC coursework | Allocation, bounded catalogue lookup, candidate duct sizes, bound single-line schedules, native DWG/PDF, connection review and report | Actual room loads, ADPI applicability, finite physical connections and installation acceptance |
| Electrical | Scoped circuit/three-phase studies, selected protection/rule checks, native schematics and supported cable geometry | Complete protection/product/installation design and full jurisdiction coverage |
| Water and drainage | Supported tree/EPANET adapters with historical executed evidence, pump scenarios, saved-IFC binding, source-bound fixture demand, declared drainage connections and SWMM input preparation | Current WNTR/EPANET import and SWMM native execution blocked; real survey/table applicability, saved sanitary topology and complete sanitary/fire design pending |
| IFC and coordination | Supported envelopes, straight walls, finite elbows/tees/transitions, source-bound local linked duct chains, saved geometry and scoped clashes/drawings | General network authoring, complete equipment/product fidelity and installation acceptance |
| Revit | Compiled native adapter, provenance/diagnostic logic and local deployment preparation | Native execution blocked by host signing policy; creation/reopen/system validation unverified |
| Lighting and energy | Historical executed Radiance/OpenStudio/EnergyPlus workflows and source-bound adapters | Current host blocks relevant native components; full performance/design acceptance pending |
| Hong Kong rules | Selected official-source-pinned electrical, lighting, HVAC and plumbing modules | Full applicability, discipline coverage and whole-project conformity |

See [native Revit](adapters/revit/README.md), [three-phase studies](docs/THREE_PHASE_NETWORKS.md), [water binding](docs/WATER_BINDING.md), [rectangular duct models](docs/RECTANGULAR_AIR_NETWORKS.md), [lighting](docs/LIGHTING.md), [energy](docs/ANNUAL_ENERGY.md), and [rule packs](docs/REGULATION_PACKS.md) for exact contracts. Successful examples are evidence only for their stated scope.

For a repeatable source-bound sanitary example, see [Hong Kong drainage](docs/HK_DRAINAGE.md). Its public runner creates fictional survey/DU inputs and executes positive, unknown-route and prohibited-connection workflows using a supplied hash-pinned official PDF. It preserves whole-design review and does not need private coursework.

The [current WNTR runtime probe](docs/WATER_RUNTIME.md) distinguishes installed packages from usable native dependencies. Its observed import failure prevents fresh EPANET hydraulic results on this host; scoped fixture-demand calculations do not use that solver.

The [2026-11-11 complete regression](docs/REGRESSION_20261111.md) finished988 test invocations with25 failures,17 errors and103 skips. Native startup failures and their downstream effects remain visible; the suite is not green. Subsequent targeted diagnostic checks do not replace a full rerun.

## Verification and delivery

[Workflow verification](docs/WORKFLOWS.md) checks recorded sources/artifacts. [Delivery review](docs/DELIVERY_REVIEW.md) checks every requirement and retains missing evidence. Native DWG acceptance needs independent AutoCAD reopening and actual plotted-page inspection. A successful script or DXF is insufficient.

Keep numerical execution, geometric correspondence, source applicability, visual review and engineering acceptance explicit. Record unknowns rather than inventing values or changing a criterion to obtain a pass. Internal run/revision IDs belong in provenance; submitted titles, filenames and narrative omit internal iteration labels while preserving actual cited editions.

The earlier [2026-11-09 regression](docs/REGRESSION_20261109.md) is historical; the 2026-11-11 complete regression above is the current full-suite record. Later focused tests do not supersede it. Historical engine execution must not be presented as current availability, and host policy is not changed to make tests pass.

## Development and provenance

Development and generated artifacts stay in this repository. Completed historical coursework remains read-only. Existing upstream engines are preferred to replacements; dependencies, licenses and attribution are recorded with each integration. No Autodesk API binaries, private coursework, credentials or generated environments are published.

Project skills are under .agents/skills. Detailed workstream gaps remain in [ROADMAP](docs/ROADMAP.md); [historical implementation notes](docs/PROJECT_HISTORY.md) preserve earlier milestones and their superseded limitations. The project has no root distribution license selected yet; retained third-party licenses remain applicable.
