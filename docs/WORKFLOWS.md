# Requirements-to-tools orchestration

For finite circular elbows use `ifc_route_drawing` with original source `model`, drawing `settings`, and exactly one saved `ifc` or registered IFC producer `depends_on`. It checks complete coplanar circular-wall geometry and emits true arcs, OD outlines and GUID-linked schedules. `ifc_native` can depend on that drawing producer and reconciles native arcs as well as lines/text; full arc/annotation bounds must fit the sourced sheet window. See [route drawings](IFC_ROUTE_DRAWINGS.md) and `examples/circular-elbow/delivery-plan.json`. Source/geometry/scale and actual visual review stay separate from complete installation acceptance.

The host AI reads and interprets the user's brief. The deterministic workflow runner checks that the interpretation quotes the actual source and calls known engineering adapters. It does not invoke a hidden model API or claim arbitrary engineering language can be understood by keyword matching.

## Commands

The unified entry point executes an already interpreted source-linked plan, then validates the resulting evidence and saves `diagnosis.json` with dependency blockers:

```powershell
.venv/Scripts/python -m bsa.cli workflow examples/shared-lighting-plan.json --out runs/new-assignment
```

Optionally add `--review runs/new-assignment-review.json` to initialize the existing delivery-review contract in the same invocation. The review must be a new file outside the run directory; conflicting destinations are rejected before engine execution. Every requirement starts pending, bound to the plan and workflow hashes. Review it with the delivery skill and `bsa.delivery audit`; creating the record does not approve any requirement. Without this flag no review is created. A later review-writing error leaves the completed run/diagnosis available; recover with `bsa.delivery template` rather than rerunning engines into that directory.

It accepts the same explicit `--autocad`, `--energyplus`, `--radiance-bin` and `--ifcmcp-python` paths as workflow execute. It does not discover runtimes, interpret the brief, repair failures or approve the design. Missing engines and manual review remain unresolved (exit 2); a successful execution still reports `design_accepted: false`. Use a new output directory for each attempt. `diagnosis.json` binds the source plan and workflow report hashes and is a derived handoff, not an additional engineering verification or authenticated evidence ledger.

Any task may declare `"requires_pass": ["hk-check", "coordination-check"]` as additional execution prerequisites. Each ID must name a unique earlier task; forward references, cycles, self-references and malformed lists are rejected. All listed tasks must have execution status `pass` before the adapter is called. Otherwise the task stays pending, names its blockers and produces no task artifact directory. Independent tasks continue. These gates supplement adapter-specific `depends_on`/`ifc_from` artifact dependencies rather than replacing them.

`workflow_status` includes these gates when tracing blockers and upstream action tasks. A gate is an explicitly selected narrow tool check, not whole-project approval. Known electrical/lighting consumers now require byte-identical project inputs to upstream electrical_regulations/lighting_regulations checks, and geometry too when both tasks consume it. Identical copies are allowed. Checks propagate through intermediate prerequisites and source-producing depends_on chains, including native drawing consumers. workflow.json records these source bindings. Changed inputs before a task prevent its adapter from executing. The plan author must still establish actual scope: this mechanism does not infer required jurisdiction rules, validate arbitrary cross-domain source correspondence or replace engineering review. For example, an `electrical_regulations` task and its gated `electrical` overlay should use the same electrical project file. The actual Hong Kong baseline/long-feeder execution evidence in `docs/evidence/workflow-gates` shows a permitted DXF run and a withheld DXF run, with full review pending in both.

`route_model` and `route_optimize` accept relative `routing`, `settings` and `network` files under the contract in ROUTE_SEARCH.md. All three sources enter integrity tracking. The first compiles the requested finite-grid route; the second retains the length baseline and selects the fixed-bore prescribed-flow pressure objective. Both run native IFC author/reopen and geometry/pressure reconciliation. Their IFC outputs are registered for downstream `ifc_clash` and other compatible IFC consumers. Failed calculated checks leave dependent tasks pending. `examples/route-search/coordination-plan.json` exercises pressure-selected route self-coordination with an explicit synthetic contact policy and a separate pending full review. Its obstacle column is not in the IFC and must not be claimed as checked by self-coordination.

```powershell
.venv/Scripts/python -m bsa.workflow intake examples/workflow-brief.md --out runs/intake.json
.venv/Scripts/python -m bsa.workflow validate examples/workflow-plan.json
.venv/Scripts/python -m bsa.workflow execute examples/workflow-plan.json --out runs/workflow --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe' --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python -m bsa.workflow verify runs/workflow
.venv/Scripts/python -m bsa.workflow_status examples/workflow-plan.json runs/workflow
```

The sample contains an explicit manual review task. Execute therefore returns exit code 2 with a durable workflow report: three technical tasks succeeded but manual review remains pending. This is intentional. Do not suppress the pending task to obtain a successful exit code.

`bsa.workflow_status` supplies a read-only, source-bound handoff for the host agent. It validates plan/run correspondence and all recorded input/artifact hashes, then lists task statuses, original scope messages, direct blockers, transitive upstream action tasks, requirement IDs and evidence paths. It rejects stale evidence and a passing child with nonpassing parents. Exit 2 means unresolved execution or invalid evidence; a JSON result is printed only for valid evidence. Resolve the recorded condition and execute into a new run directory; this command does not resume, rerun, repair, or approve tasks. Pending conditions remain verbatim rather than being guessed from error keywords. Successful execution still requires a separate full-requirement review.

## Plan contract

Workflow kind `three_phase` takes an explicit source-bound `project` under THREE_PHASE_NETWORKS.md and optional `requires_pass`. Execute with `--three-phase-python <isolated-python.exe>` in either workflow CLI. Missing runtime stays pending; numerical or declared current/voltage target failure stays fail and blocks required downstream tasks. Source basis files and the fixed runner/adapter/bridge enter the workflow input inventory. The isolated bridge validates child evidence and preserves logs; no arbitrary runtime command is accepted from plan JSON. Full cable/protection/neutral/harmonics/Hong Kong and CAD/BIM acceptance remains separate.

### Missing and conflicting design inputs

Optional `unresolved_inputs` records known input problems separately from task execution. For example:

```json
"unresolved_inputs": [{
  "id": "installation-basis",
  "kind": "missing",
  "description": "Installation conditions needed for the sizing basis remain unconfirmed",
  "sources": [{"passage": "P002", "quote": "Verify installation conditions before sizing."}],
  "blocks_tasks": ["sizing"]
}]
```

Each issue requires these exact fields, a unique path-safe ID, `missing` or `conflict`, a nonempty description, exact passage/quote citations, and unique existing task IDs. A conflict requires at least two distinct citations; the tool checks their source linkage, not whether they conflict in meaning. Supplemental-document passage IDs are supported. These records supplement the requirement matrix rather than replacing requirement coverage.

An affected task remains pending and its adapter is not called. Dependent tasks still obey their existing dependency gates; independent tasks continue. The register is retained in `workflow.json`, rendered in the requirement report, and verified during dependency diagnosis and delivery audit. `input_blockers` identifies the source-linked issues for each affected task. Reviewer assertions cannot clear them, including for manual tasks. Diagnose rejects a recorded passing task with unresolved inputs and rejects a register differing from the source plan.

Plans and declared task input files must still satisfy their existing validation contracts: this feature does not permit fake or absent project files as placeholders. If the required adapter input cannot yet be authored, preserve the requirement as a manual task with an explicit missing implementation/data scope until a valid source-backed design is available. Resolving an issue means obtaining actual evidence, revising the design basis and source-linked plan, and running into a new directory. There is no `resolved=true` override. Removing an issue is a plan-author decision, not independently verified resolution; preserve previous runs and review the new basis. The software does not infer missing parameters, compare arbitrary engineering values/units, or prove that a declared issue list is complete.

See examples/workflow-plan.json. Version 1 requires:

- `brief`: relative source path and `brief_sha256`: digest of the interpreted bytes.
- `passage_dispositions`: every source paragraph classified as requirement or context. The AI must review context classifications; validation cannot prove that a requirement was not misclassified.
- `requirements`: unique id, source passage id, exact source quote, task id and a complete acceptance description. Multiple requirements may cite a paragraph. Partial quotation alone is not evidence that the complete paragraph has been interpreted correctly.
- `tasks`: unique path-safe ids and a registered adapter (scoped contracts below), or manual. Project/input files use relative paths inside the plan directory. Dependencies must name earlier supported producers. No arbitrary shell commands or executable paths can be supplied in plan data; optional engine paths are explicit CLI arguments.

Source changes invalidate the brief digest. Escaping input paths, unknown adapters, uncovered paragraphs, fabricated quotations and unreferenced tasks are rejected before execution. Missing optional tools remain pending. Adapter exceptions are recorded as failures; later independent tasks can still run.

Native electrical conversion requires its producer to pass, including the bound electrical/lighting producer. Missing Radiance leaves both that producer and its native dependent pending even when AutoCAD is supplied; it must not attempt to open a nonexistent DXF. A failed producer likewise blocks conversion. The recorded scope names the producer and status so the agent can resolve the upstream condition before executing a new run. Independent tasks still run. Dispatch regression controls are retained in `docs/evidence/native-dependency`; mocked conversion proves scheduling only, not native drawing fidelity.

## Evidence and acceptance

`workflow.json` records input hashes, source line locators, task scopes, output evidence paths and task-artifact hashes. `index.html` summarizes the matrix. `verify` rehashes recorded inputs and task outputs, and detects missing or changed files. This is integrity checking, not a signed tamperproof ledger. It does not assess semantic correctness or hash its own report.

Task execution statuses pass/fail/pending are separate from requirement acceptance, which remains pending review. A task's success proves only the named adapter scope. For example, native conversion verifies circle/text entities and emits a PDF, but cannot prove arbitrary quoted layout requirements, print scale, visual quality or all electrical safety conditions.

Intake now reads UTF-8 Markdown/text, PDF and DOCX with explicit coverage/review gates; optional offline OCR supplies page-bound text for otherwise unreadable PDF pages. See DOCUMENT_INTAKE.md. General drawing-note semantics remain pending. CAD is limited to the supported overlay, energy to two synthetic thermal zones/design days. Broad MEP authoring, hydraulic analysis and full engineering acceptance remain outstanding.

The `bim` adapter uses the explicit IFC envelope input contract in IFC_MODELS.md. Its success covers native IFC geometry and relationships, not physical routing, manufacturer fidelity, visual appearance or a finished building-services design.

The `network` adapter calculates prescribed-demand circular tree pressure budgets using NETWORKS.md. It preserves failed targets as task failures and does not claim loop solving, passive branch balancing or fan/pump selection.

The `annual_energy` adapter takes relative `project` and `weather` (EPW or lossless gzip) inputs. Plan validation checks the weather source hash, station and full hourly calendar; execution requires the CLI EnergyPlus path. It checks actual weather-only SQL completeness, monthly/annual reconciliation, lighting balance and sourced per-zone unmet targets. Weather bytes are part of workflow input integrity. See ANNUAL_ENERGY.md and examples/annual-energy/plan.json. Ideal thermal demand, lighting electricity, native completion discrepancies and unresolved actual-building/plant applicability remain distinct.

The `water_network` adapter takes a relative `project` under WATER_GRAPHS.md with the optional pinned water runtime. It solves EPANET steady water graphs, including loops/parallel pipes and global PDA, retaining native INP/RPT/BIN and signed flows/static heads. Independent scalar pipe-energy and reservoir-boundary checks join continuity, demand-law, pump and supplied-target checks; failures fail the task. Source-linked energy tolerances are mandatory. It has no geometry-producer/IFC binding or default-efficiency electricity estimate. Use examples/water-loop/plan.json; actual route/product applicability and domain acceptance remain pending.

The `water_coordination` adapter takes a geometry-free hydraulic `project`, explicit GUID `binding`, and exactly one saved `ifc` or earlier supported IFC producer `depends_on`. It derives saved hollow-pipe geometry and node elevations, requires full selected-system topology coverage and runs the same EPANET checks. Its unchanged `model.ifc` can feed downstream IFC tools; source and copied-byte integrity are recorded. See WATER_BINDING.md and examples/water-loop-ifc/plan.json. Zero-loss node/bend idealizations, real product/K/visual and domain gates remain explicit.

The `ifc_views` adapter takes `settings` plus exactly one saved `ifc` or supported earlier IFC producer `depends_on`. It emits complete per-view axis/end-on representations, combined nonzero coverage, GUID-linked DXFs and a common schedule. `ifc_views_native` takes either that earlier producer or a source `manifest`; every manifest artifact is included in direct-input integrity tracking. It requires the CLI AutoCAD path, preserves individual native/printed proofs and merges verified PDF pages. See IFC_VIEWS.md and examples/water-loop-ifc/views-plan.json. Actual visual review and full installation acceptance remain separate.

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

### Native HVAC regulatory prerequisite

`hvac_regulations` takes `depends_on` (earlier `energy` task), `basis`, `pack` and `sources`. It reads both actual producer variants, verifies saved IDF/OSM/SQL and native completion artifacts, then evaluates supported design conditions. It forbids replacement project/IDF inputs or checking only one variant. Downstream tasks declare `requires_pass: [check-task-id]`; unresolved conditions retain blocking causes. See [native HVAC checks](HVAC_IDF_RULES.md). Full regulatory and engineering acceptance remains separate.

### HVAC water-pipe regulatory prerequisite

`water_pipe_regulations` takes `project`, `basis`, `pack`, `sources` and returns scoped per-segment rules plus fresh hydraulic results. A downstream `network` task uses `requires_pass`; the checked and consumed network input bytes must match. Failure or pending checks skip the downstream task. CAD/BIM and optimized-model correspondence is not established by this adapter. See [water piping](HK_WATER_PIPING.md).

### Regulatory water-model selection

`regulated_water_model` uses project/model/binding/catalogue/geometry/basis/classifications/pack/sources and exposes the saved selected IFC plus derived network to existing consumers. Selection must pass before dependent consumers execute; downstream clash checks and drawing prerequisites remain explicit. See [water-piping selection](HK_WATER_PIPING.md).


### Saved IFC circulation pump iteration

For the current contract and executed native example, see [selected pump IFC](SELECTED_PUMP_IFC.md). `circulation_pump_design` accepts a standalone project or inherits the exact derived network from a passing `water_coordination` task. `selected_pump_ifc` inherits that screen and writes a new IFC plus revised template with stable identities. `ifc_circulation_checks` can consume either the original water producer or the selected producer's rebound. Failed baselines block inherited screening by default; explicit allow_failed_baseline accepts only reverified target failures for search, preserves baseline fail status and cannot bypass requires_pass. No-feasible screens block model revision. Keep original attempts and source identity checks.

### Upstream IDS information checks

Use `ids_check` with `ids` and exactly one of `ifc` or `depends_on` on a supported IFC producer. This calls pinned IfcTester and interprets its JSON audit rather than trusting process exit 0. Declare `requires_pass` on relevant downstream tasks and ensure their model is the checked model. See [IDS workflow](IDS_WORKFLOW.md); information requirements do not replace geometry, performance, source authenticity or regulation checks.

The main agent skill routes these operations through network, IFC, regulations and delivery skills. Existing upstream engines supply computation; consult [reuse survey](REUSE_SURVEY.md) before implementing a missing engine. Trial scripts and researched MCP endpoints are not registered, verified production adapters merely because their names appear in the survey.


### Equal-bore tee assembly and directional diagnostics

Use `tee_assembly` with tee_spec and assembly_spec, then `tee_losses` with basis and depends_on on that producer. The latter inherits source specs and IFC; it cannot accept replacement model inputs. See [tee workflow](IFC_TEE_TRIAL.md) and examples/tee-trial/placed-plan.json. Geometry or coefficient task success leaves complete hydraulic, native drawing, product and regulatory acceptance unresolved. The design, IFC, network and delivery skills now route this supported path explicitly.

`tee_pressure` and `tee_split` also inherit tee_assembly with a sourced basis. tee_split adds control for fixed total flow, bracket and tolerances; its source pressure is available capacity, not an independently imposed boundary. Failed/no-root solves block requires_pass consumers, which must share the checked model identity. See examples/tee-trial/split-plan.json and IFC_TEE_TRIAL.md.
