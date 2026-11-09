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

This trial runs the established geometry runtime used by existing project adapters. It does not load or bypass the blocked FreeCAD or IfcOpenShell 0.9.0 kernels. Next integration work includes stable source identities, placement/rotation support, actual adjoining pipe connections and solid/clearance checks, source-backed directional junction losses, saved-network binding and drawings. Do not substitute it for a standard-compliant product, use a zero-loss junction by implication, or mark a complete engineering design on this evidence.


## Connected three-pipe assembly trial

```powershell
.venv/Scripts/python scripts/probe_tee_assembly.py --tee-spec examples/tee-trial/spec.json --assembly-spec examples/tee-trial/assembly.json --out runs/new-tee-assembly
.venv/Scripts/python scripts/test_tee_assembly.py
```

The assembly trial adds three explicitly sourced 200 mm hollow pipe stubs to the tee using unmodified IfcOpenShell profile, representation, placement and system.connect_port APIs. Each stub starts at one tee opening, has the same 32 mm bore/40 mm outside diameter and points outward. The example is butt-ended geometry only: no socket insertion, weld allowance, seal or manufacturer connection is implied. Each pipe has two reversible ports; the three pairs of adjoining tee/pipe ports produce six directed IFC connection relationships.

The saved IFC is reopened and the original tee checks rerun. Each pipe's native hollow profile, solid placement, axis/depth, actual endpoints and outward port axes must match its source dimensions and expected opening. Port flow directions and exact connection arcs are checked independently. Four material bodies are then converted through the established native geometry reader and Manifold closed-mesh adapter; all six material intersections must be below the explicit numerical 1e-12 m3 threshold. The maximum observed residual was 7.3e-23 m3. This is a contact/interpenetration test, not a code-prescribed clearance rule or proof of installation accessibility.

Positive source/geometry/topology checks passed; native IFC schema/EXPRESS validation reported zero statements. Two controls keep all ports and connection relationships unchanged but shift the branch pipe body 10 mm: inward produces material overlap and endpoint mismatch, outward produces a gap and endpoint mismatch despite zero overlap. Both are rejected. Evidence is retained in docs/evidence/tee-assembly/native-trials.zip.

The assembly remains a standalone geometry trial. Random IFC identities are not yet a reusable source-namespace contract; no network loss coefficient, system hydraulic solution, arbitrary placement/rotation, product selection, native drawing or installation acceptance is provided. Future integration must preserve finite fitting lengths and directional losses rather than silently replacing the tee with a zero-loss mathematical junction.
