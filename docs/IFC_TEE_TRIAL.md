# Equal-bore hollow tee geometry trial

This is an executed synthetic geometry trial, not a manufacturer fitting or production workflow adapter. Existing IfcOpenShell 0.8.5 ShapeBuilder and geometry.add_boolean construct IFC CSG; its native geometry engine evaluates the saved model. Existing Manifold3D 3.5.4 checks the resulting mesh. The installed ShapeBuilder was inspected first: it offers MEP bend/transition helpers but no tee helper was identified. No upstream implementation was copied or modified and no new kernel was written.

```powershell
.venv/Scripts/python scripts/probe_ifc_tee.py --spec examples/tee-trial/spec.json --out runs/new-ifc-tee
.venv/Scripts/python scripts/test_ifc_tee.py
```

The explicit example uses outer radius 20 mm, bore radius 16 mm, main half-length 100 mm and branch length 100 mm. These are software-test assumptions. Parameters are finite positive SI lengths with 0 < inner radius < outer radius < both arm lengths. The main cylinder is centred on Z, the branch runs along positive X from the origin. The material body is the union of outer cylinders minus the union of equal-radius inner cylinders. Three reversible distribution ports sit at the opening centres with outward axes. Source text and dimensions are stored in BSA_TeeTrial. No K-factor, pressure rating, flange/socket, wall-strength or manufacturer claim is inferred.

For equal perpendicular cylinders, the positive-X half of their intersection has volume 8r^3/3 when both arms extend beyond the radius. Subtracting the inner union from the outer union gives the independent reference:

`Vwall = pi * (R^2 - r^2) * (2L + B) - 8/3 * (R^3 - r^3)`.

Saved-model checks use 10 micrometre mesh linear deflection and 0.05 rad angular deflection; the analytic-volume relative tolerance is 0.2%. The observed wall volume is 0.0001252956012 m3 against 0.0001253061360 m3 analytic (about 0.0084% difference). Manifold reports a valid, single connected wall. Main and branch cylindrical probes at 90% of bore radius have zero material intersection, while a wall probe detects material. The three saved port positions/axes match the declared openings. These finite probes are not a universal proof of every bore point, and full manufacturing detail is absent.

A deliberately damaged IFC removes branch-bore subtraction while retaining outer geometry and all ports. It fails both analytic volume and bore-clearance checks while its ports still pass. The positive model separately passed native IFC schema/EXPRESS validation with zero statements. Both models and native reports are retained in docs/evidence/ifc-tee/native-trials.zip.

This trial runs the established geometry runtime used by existing project adapters. It does not load or bypass the blocked FreeCAD or IfcOpenShell 0.9.0 kernels. The subsequent assembly and identity sections cover adjoining pipes and stable identities. Remaining integration work includes complete directional pressure balance, saved-network binding and drawings; subsequent sections document rigid placement and coefficient diagnostics. Do not substitute it for a standard-compliant product, use a zero-loss junction by implication, or mark a complete engineering design on this evidence.


## Connected three-pipe assembly trial

```powershell
.venv/Scripts/python scripts/probe_tee_assembly.py --tee-spec examples/tee-trial/spec.json --assembly-spec examples/tee-trial/assembly.json --out runs/new-tee-assembly
.venv/Scripts/python scripts/test_tee_assembly.py
```

The assembly trial adds three explicitly sourced 200 mm hollow pipe stubs to the tee using unmodified IfcOpenShell profile, representation, placement and system.connect_port APIs. Each stub starts at one tee opening, has the same 32 mm bore/40 mm outside diameter and points outward. The example is butt-ended geometry only: no socket insertion, weld allowance, seal or manufacturer connection is implied. Each pipe has two reversible ports; the three pairs of adjoining tee/pipe ports produce six directed IFC connection relationships.

The saved IFC is reopened and the original tee checks rerun. Each pipe's native hollow profile, solid placement, axis/depth, actual endpoints and outward port axes must match its source dimensions and expected opening. Port flow directions and exact connection arcs are checked independently. Four material bodies are then converted through the established native geometry reader and Manifold closed-mesh adapter; all six material intersections must be below the explicit numerical 1e-12 m3 threshold. The maximum observed residual was 7.3e-23 m3. This is a contact/interpenetration test, not a code-prescribed clearance rule or proof of installation accessibility.

Positive source/geometry/topology checks passed; native IFC schema/EXPRESS validation reported zero statements. Two controls keep all ports and connection relationships unchanged but shift the branch pipe body 10 mm: inward produces material overlap and endpoint mismatch, outward produces a gap and endpoint mismatch despite zero overlap. Both are rejected. Evidence is retained in docs/evidence/tee-assembly/native-trials.zip.

The assembly remains a standalone geometry trial. A canonical project namespace now preserves the scoped product/port identities described below; no network loss coefficient, system hydraulic solution, product selection, native drawing or installation acceptance is provided. Future integration must preserve finite fitting lengths and directional losses rather than silently replacing the tee with a zero-loss mathematical junction.


## Stable identities for iteration

The tee spec now requires a canonical `project_uuid`. Retain it for revisions of the same project; use a different UUID for an independent project. Reusing the existing BIM adapter's UUIDv5 strategy, the trial derives GUIDs from namespace, IFC class and semantic object ID. Port keys additionally include their owning object ID. The fixed single-tee fixture has four physical products and nine ports; it is not a multi-tee authoring schema.

Saved assembly checks require all 13 expected identities to match and be unique. Real regenerate/reopen regression runs verify identical identities across repeat generation and a branch-length revision, disjoint identities under a different namespace, rejection of a substituted saved port GUID, and malformed namespace rejection before output creation. Existing blocked-bore, unchanged-port penetration and gap controls still pass. Relationships, property sets, representations and file bytes are not promised stable. Historical evidence archives predate this required input and retain their original random IDs.

Current positive IFC and checks are archived in `docs/evidence/tee-assembly/stable-identity.zip`. This improves revision correspondence; it does not supply directional hydraulic losses or establish engineering acceptance.


## Source-bound directional coefficient diagnostic

Run `python scripts/probe_tee_losses.py --model <saved-assembly.ifc> --tee-spec examples/tee-trial/spec.json --assembly-spec examples/tee-trial/assembly.json --basis examples/tee-trial/loss-basis.json --out <new-repository-run>` in the established environment. Regression: `python scripts/test_tee_losses.py`.

This calls unmodified fluids 1.3.1 `K_branch_diverging_Crane` and `K_run_diverging_Crane`. [Upstream reference](https://fluids.readthedocs.io/fluids.fittings.html) defines their coefficients against combined inlet velocity; signed run values must be retained. The trial supports only the verified equal-bore 90-degree assembly, either main leg as inlet, and two positive prescribed outlet flows. It reopens and verifies saved geometry/identities before binding the inlet/outlet GUIDs. Basis/source hashes and the installed fittings module hash are recorded.

The synthetic 0.75/0.25 L/s run/branch split produces K values -0.0625 and 1.0378515625. At assumed density 998 kg/m3, K times inlet dynamic pressure is -48.217 and 800.675 Pa respectively. These are correlation diagnostics, not terminal pressure predictions. Independent numeric anchors, fourfold pressure scaling on doubled flow, reversed main inlet mapping, unsupported branch-inlet rejection and changed saved-body rejection passed.

No general network adapter is enabled: the current segment interface assumes nonnegative local-velocity losses, whereas this diagnostic retains signed combined-velocity coefficients. Reference stations, finite fitting distributed friction and physical correlation applicability need resolution before a complete pressure balance. Prescribed split does not establish passive balancing. Manufacturer, regulatory and engineering acceptance remain false. Evidence: `docs/evidence/tee-assembly/tee-loss.json`, using the IFC in the stable-identity archive.


## Requirement-linked workflow

`python -m bsa.workflow execute examples/tee-trial/plan.json --out runs/new-tee-workflow` executes the sourced synthetic brief through `tee_assembly` then `tee_losses`. The geometry, assembly and coefficient implementations now live in `bsa.tee_geometry`, `bsa.tee_assembly`, and `bsa.tee_losses`; original scripts remain compatible CLI/import entry points.

`tee_assembly` requires `tee_spec` and `assembly_spec` and exposes `assembly.ifc` as its IFC artifact. `tee_losses` requires `basis` and `depends_on` pointing to that earlier assembly. It inherits both source specs and the saved IFC; replacement model/spec fields are rejected. It reruns saved geometry/identity verification. Failed upstream generation leaves the diagnostic pending and creates no diagnostic output. General IFC inventory prerequisites also apply to this consumer.

The example executed both tasks with intact source/artifact hashes and design acceptance false. Native geometry and coefficient regressions pass after extraction into package modules; a malformed geometry workflow verifies downstream blocking. Evidence is archived in `docs/evidence/tee-assembly/workflow.zip`. Task pass means only the recorded geometry or coefficient diagnostic scope, not complete pressure balance, actual product/installation or regulatory acceptance.


## Sourced rigid project placement

An optional `placement` on the tee spec contains `source`, `origin_m` (three coordinates in metres), and `rotation` (a row-major 3x3 matrix acting on column vectors). Rotation columns are the local axes in project coordinates. Require finite entries, unit orthogonal axes and determinant +1; scaling, shearing and reflection are rejected. Omission preserves the original explicit origin/axis fixture. Namespace and semantic IDs do not depend on coordinates.

The tee's native product placement carries the transform. World opening positions/axes drive adjoining pipe solids and ports. Saved checks compare the tee placement against the source matrix, reconcile world pipe endpoints and ports, rerun local wall/bore/volume checks, and perform world-coordinate material intersection tests. This is placement in a metre-based project frame, not a map projection/georeferencing implementation.

Run `python -m bsa.workflow execute examples/tee-trial/placed-plan.json --out runs/new-placed-tee`. The synthetic origin [12.3, -4.5, 2.7] m with 30-degree Z followed by 40-degree X rotation passed both workflow tasks and input/artifact integrity verification. Regression independently checks saved world endpoints, unchanged directional coefficients, rejection of a shifted saved tee, and pre-output rejection of scale/reflection. Evidence: `docs/evidence/tee-assembly/placed-workflow.zip`. Real survey coordinates, BIM-viewer inspection, multi-fitting authoring, full hydraulic solution and engineering acceptance remain pending.


## Agent routing and delivery state

The design orchestrator routes this workflow through the IFC authoring and network analysis skills; the delivery skill distinguishes geometry evidence from signed-coefficient diagnostics. All four updated skills pass the skill-format validator. This validates structure, not autonomous planning quality.

The actual placed workflow was used to run `python -m bsa.delivery template examples/tee-trial/placed-plan.json runs/tee-placed-workflow-v1 --out runs/tee-placed-review-v1.json` and the corresponding delivery audit. Both requirement rows remain pending; the audit returns needs_review with design_accepted false despite two passing execution tasks. No review was fabricated. The separate review/audit evidence is archived in `docs/evidence/tee-assembly/delivery-pending.zip`; the workflow artifacts remain unchanged.


## Prescribed-flow face-to-face pressure budget

`tee_pressure` inherits an earlier `tee_assembly` and takes a separate sourced `basis`. Run `python -m bsa.workflow execute examples/tee-trial/pressure-plan.json --out runs/new-tee-pressure`. It reopens and verifies the assembly, then derives pipe bores, lengths and outer-port elevations from native IFC. Existing network friction_factor reuses pinned fluids 1.3.1 Colebrook for turbulent flow and 64/Re for laminar flow; transition is rejected.

The input coefficients must explicitly represent tee inlet-face to outlet-face total-head difference, include all fitting wall friction, and reference combined inlet velocity. The module therefore adds only adjoining straight-pipe friction; it does not add or omit an implicit centreline fitting friction allowance. Coefficients are externally supplied scenario inputs, not automatically adopted from tee_losses. Their physical applicability remains a separate source review. The example deliberately uses synthetic coefficients and is not manufacturer or Crane validation.

For each path: outlet total pressure equals inlet total pressure minus inlet/outlet straight-pipe friction, minus signed K times combined dynamic pressure, minus rho*g times outer-port elevation rise. Total pressure is static plus velocity pressure with elevation accounted separately. Targets must use that same basis. Negative individual K remains signed, while flow-weighted net fitting dissipation must be nonnegative. Pressure/velocity failures remain failed and block declared downstream consumers.

Actual placed-model execution and source/artifact integrity passed. Independent Hagen-Poiseuille and elevation references validate a separate laminar case; low supply, negative net fitting dissipation and ambiguous coefficient contracts are rejected or fail their targets. A real low-pressure workflow leaves its dependent diagnostic unexecuted. Evidence: `docs/evidence/tee-assembly/pressure-workflow.zip`. This is a prescribed-flow budget, not passive splitting, a pump/system operating point, arbitrary network solving or full engineering/code acceptance.


## Bounded fixed-total-flow split

`python -m bsa.tee_split --model <saved-assembly.ifc> --tee-spec examples/tee-trial/split-spec.json --assembly-spec examples/tee-trial/split-assembly.json --basis examples/tee-trial/split-basis.json --control examples/tee-trial/split-control.json --out <new-repository-run>` is a standalone solver. Install optional `.[tee]` for the pinned geometry, fluids and SciPy runtime. It is also registered as workflow kind tee_split, as described below.

This mode assumes a fixed total flow from an adjustable-pressure source and specified outlet total-pressure boundaries. The pressure basis's inlet value becomes available source capacity, not an independently imposed operating pressure; outlet targets become boundary values. The control explicitly supplies total flow, an interior branch-fraction bracket, ratio/pressure tolerances and the sourced assumption that both complete face-to-face coefficients remain constant throughout that bracket. Original run/branch flow fields are replaced by the solved split. Flow-dependent coefficients, pump curves and flow reversal are unsupported.

The module reuses tee_pressure for every candidate, retaining input files, saved-model checks and pressure reports. It uses SciPy 1.18.1 brentq to equalize the two paths' required supply pressures. Endpoint friction regimes must match for each pipe so the interval does not cross the unsupported transition. A missing sign-changing bracket returns no split; residual tolerance, source capacity, velocities and net fitting dissipation are checked separately. A converged low-capacity solution stays failed. The adjusted-pressure final evaluation is retained independently of the available-capacity evaluations.

The horizontal synthetic laminar case explicitly assumes zero fitting losses. A 0.4 m branch and 0.2 m run outlet with equal bore and boundary pressure produce an independently predicted branch fraction 1/3. Actual execution yields 1.333333e-6 and 2.666667e-6 m3/s, required source total pressure 500.051808 Pa and zero recorded balance residual. Weak source and no-bracket controls pass as expected failures. These idealized coefficients validate solver plumbing, not real tee performance. Evidence: `docs/evidence/tee-assembly/split-native.zip`. General networks, real coefficient applicability, automatic component selection and engineering/regulatory acceptance remain unresolved.


## Split workflow registration

`python -m bsa.workflow execute examples/tee-trial/split-plan.json --out runs/new-split-workflow` runs assembly then tee_split. Inputs are basis, control and depends_on on an earlier tee_assembly. Source specs and saved IFC are inherited, not replaceable. Both source files participate in workflow hashing. Same-model gates prevent a split check from releasing a consumer of an unrelated IFC producer.

Actual execution retains all candidate/replay pressure reports, converged split and requirement links; workflow integrity passes with design_accepted false. Real no-root and insufficient-capacity cases leave downstream diagnostics pending without producing their outputs. Source substitution and unrelated-producer gating are rejected before execution. Evidence: `docs/evidence/tee-assembly/split-workflow.zip`. The network skill now distinguishes pressure budgets, bounded split solutions and diagnostic-only correlations.
