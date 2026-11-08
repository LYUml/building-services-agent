# Requirements-to-tools orchestration

The host AI reads and interprets the user's brief. The deterministic workflow runner checks that the interpretation quotes the actual source and calls known engineering adapters. It does not invoke a hidden model API or claim arbitrary engineering language can be understood by keyword matching.

## Commands

```powershell
.venv/Scripts/python -m bsa.workflow intake examples/workflow-brief.md --out runs/intake.json
.venv/Scripts/python -m bsa.workflow validate examples/workflow-plan.json
.venv/Scripts/python -m bsa.workflow execute examples/workflow-plan.json --out runs/workflow --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe' --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python -m bsa.workflow verify runs/workflow
```

The sample contains an explicit manual review task. Execute therefore returns exit code 2 with a durable workflow report: three technical tasks succeeded but manual review remains pending. This is intentional. Do not suppress the pending task to obtain a successful exit code.

## Plan contract

See examples/workflow-plan.json. Version 1 requires:

- `brief`: relative source path and `brief_sha256`: digest of the interpreted bytes.
- `passage_dispositions`: every source paragraph classified as requirement or context. The AI must review context classifications; validation cannot prove that a requirement was not misclassified.
- `requirements`: unique id, source passage id, exact source quote, task id and a complete acceptance description. Multiple requirements may cite a paragraph. Partial quotation alone is not evidence that the complete paragraph has been interpreted correctly.
- `tasks`: unique path-safe ids and a registered adapter (scoped contracts below), or manual. Project/input files use relative paths inside the plan directory. Dependencies must name earlier supported producers. No arbitrary shell commands or executable paths can be supplied in plan data; optional engine paths are explicit CLI arguments.

Source changes invalidate the brief digest. Escaping input paths, unknown adapters, uncovered paragraphs, fabricated quotations and unreferenced tasks are rejected before execution. Missing optional tools remain pending. Adapter exceptions are recorded as failures; later independent tasks can still run.

## Evidence and acceptance

`workflow.json` records input hashes, source line locators, task scopes, output evidence paths and task-artifact hashes. `index.html` summarizes the matrix. `verify` rehashes recorded inputs and task outputs, and detects missing or changed files. This is integrity checking, not a signed tamperproof ledger. It does not assess semantic correctness or hash its own report.

Task execution statuses pass/fail/pending are separate from requirement acceptance, which remains pending review. A task's success proves only the named adapter scope. For example, native conversion verifies circle/text entities and emits a PDF, but cannot prove arbitrary quoted layout requirements, print scale, visual quality or all electrical safety conditions.

Intake now reads UTF-8 Markdown/text, PDF and DOCX with explicit coverage/review gates; optional offline OCR supplies page-bound text for otherwise unreadable PDF pages. See DOCUMENT_INTAKE.md. General drawing-note semantics remain pending. CAD is limited to the supported overlay, energy to two synthetic thermal zones/design days. Broad MEP authoring, hydraulic analysis and full engineering acceptance remain outstanding.

The `bim` adapter uses the explicit IFC envelope input contract in IFC_MODELS.md. Its success covers native IFC geometry and relationships, not physical routing, manufacturer fidelity, visual appearance or a finished building-services design.

The `network` adapter calculates prescribed-demand circular tree pressure budgets using NETWORKS.md. It preserves failed targets as task failures and does not claim loop solving, passive branch balancing or fan/pump selection.

The `water_network` adapter takes a relative `project` under WATER_GRAPHS.md with the optional pinned water runtime. It solves EPANET steady water graphs, including loops/parallel pipes and global PDA, retaining native INP/RPT/BIN and signed flows/static heads. Independent scalar pipe-energy and reservoir-boundary checks join continuity, demand-law, pump and supplied-target checks; failures fail the task. Source-linked energy tolerances are mandatory. It has no geometry-producer/IFC binding or default-efficiency electricity estimate. Use examples/water-loop/plan.json; actual route/product applicability and domain acceptance remain pending.

`electrical_coordination` takes both project and geometry relative input paths (COORDINATION.md). Its saved calculation/DXF/IFC outputs are reconciled. A later native_cad task may depend on this adapter as well as the standalone electrical adapter. Its additional geometry input is included in source-hash checks.

The lighting adapter uses LIGHTING.md and an explicit --radiance-bin CLI argument; IES inputs are added to plan integrity records. It checks supplied sample-grid targets and two numerical parameter settings, not all lighting design criteria.

Hashed examples and recorded evidence use .gitattributes -text to preserve their exact bytes across checkout platforms. Do not normalize/reformat an input after hashing it; update its version and re-interpret/rebind the plan instead.

The `drawing_intake` adapter uses `drawing` and optional `selection` paths. It inventories source DXF directly or exports an isolated DWG copy via the explicit AutoCAD executable. Selections bind source SHA256, dimension proof and area handles. See DRAWING_INTAKE.md; extraction success does not establish semantic or full drawing acceptance.

The `base_overlay` adapter takes a common electrical `project`, source `drawing`, reviewed `selection`, rigid-transform/annotation `settings` and optional `sheet`. Portable mode saves/reconciles DXF; supplied AutoCAD enables native save/reopen. DWG input or a requested fixed-scale sheet without AutoCAD remains pending. See CAD_OVERLAY.md for the restricted geometry contract, PDF reference measurement and separate visual gate. Both variants of examples/base-overlay use the same source brief and project; portable mode does not claim native/plot acceptance.

The `network_design` adapter takes a `project` and sourced finite `catalogue`. Plan validation checks full segment choice coverage and the explicit search bound; both files join integrity records. Execution retains baseline and failed candidates, ranks feasible prescribed-flow network variants and reruns the selected input. No feasible variant makes the task fail with evidence retained. See NETWORK_DESIGN.md; finite-catalogue success does not approve geometry, fan/pump selection or the complete requirement's engineering acceptance.

The `network_model_design` adapter adds source `model`, port `binding` and independently sourced outside-envelope `geometry` to a skeleton `project` and hydraulic `catalogue`. All five files are integrity-bound. A shared project UUID preserves object/port identities across revisions. Space-contained options feed sizing, then a new IFC is generated and independently checked for original endpoints, selected bounds/diameters/IDs and model-derived pressure. See NETWORK_MODEL_DESIGN.md; geometry containment is not clash, product or full engineering acceptance.

The `ifc_clash` adapter takes a policy and either a source `ifc` or an earlier supported IFC `depends_on` task. Generated paths are resolved from registered producer outputs. It fails on geometry coverage, intersection or clearance violations while retaining evidence; source-connected contact exceptions are limited and never waive solid overlaps. See CLASH.md for Manifold3D Mesh64 checks, tolerance/source requirements and unresolved non-interface/visual/product gates.

The `ifc_drawing` adapter takes sourced `settings` and exactly one `ifc` or earlier registered IFC producer `depends_on`. Failed/pending producers leave drawings pending. It extracts all pipe/duct segment profiles and ports into a schedule and metre-coordinate projected centreline DXF with IFC GUID XDATA, preserving unsupported segment errors and excluded equipment classes. See IFC_DRAWINGS.md and examples/water-riser/delivery-plan.json. A passing task proves this scoped extraction/reload, not installation details, native DWG or print quality.

The `ifc_native` adapter takes sourced sheet `settings` and exactly one `dxf` or an earlier `ifc_drawing` dependency. It requires the CLI `--autocad` engine path; missing engine or nonpassing producer leaves it pending. It independently reopens the saved DWG, reconciles complete model-entity/IFC-XDATA identity and supported geometry, and checks an explicit reference's physical PDF scale. Use examples/water-riser/native-plan.json. Actual PDF visual acceptance is a separate hash-bound review, and complete installation/engineering acceptance stays pending.

The `pump_operating_point` adapter takes a sourced `curve` and exactly one `project` network input or earlier `network_coordination`, `network_design` or `network_model_design` dependency. Known producer paths supply the selected geometry-derived network; failed producers leave pump analysis pending. It solves only the explicitly declared single fixed-pressure terminal/free-flow model, retains sign-bracket/convergence failures, checks flow/velocity limits and reruns its saved state. See PUMPS.md and examples/water-riser/pump-plan.json. A converged root does not establish product, NPSH, electrical or complete engineering acceptance.

The `pump_electrical` adapter takes baseline electrical `project`, `network_binding`, `link`, an earlier pump `depends_on` and supported IFC producer `ifc_from`. Failed parents leave binding pending. It verifies/replays the pump, reconciles real pump/port/centre identity and emits a separate operating electrical scenario plus property-only IFC revision, retaining all baseline hardware and original IFC entities. Baseline and operating checks must both pass; lower operating current cannot approve a failed baseline. Its model.ifc is registered for downstream IFC checking/drawing. See PUMP_ELECTRICAL.md and examples/water-riser/coupled-plan.json; electrical IFC topology, other devices and full motor/protection acceptance remain pending.

Delivery reviews are deliberately a separate `bsa.delivery` command rather than a self-approving workflow task. Use DELIVERY_REVIEW.md to create an initially pending full-requirement template, record actual evidence/observations and audit it against the unchanged plan/run. The audit pins source requirement text, report/input/artifact hashes and render attachments. It can verify defined adapter Boolean facts and record manual review assertions, but never replaces missing engine execution, source data, semantic completeness or domain acceptance. Original workflow.json is not rewritten to obtain an accepted status.

The `electrical_fault` adapter takes a common electrical `project` and sourced `faults` JSON with exact circuit coverage. It checks the supported TN bolted hot-loop and standalone device/energy criteria, preserving null/uncovered guarantees as pending. Known capacity/CPC/envelope failures fail the task; actual device/code review and other protection remain unresolved. It changes no circuit hardware. See ELECTRICAL_FAULTS.md and examples/fault-plan.json. A pending automated fault task cannot be cleared by delivery-review text.
