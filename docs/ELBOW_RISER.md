# Independent finite-elbow riser

The current actual AutoCAD opt-in regression reexecutes this synthetic elevation
and the true-arc route native check: both tests pass, with independent receipt
verification. Native save/reopen and numerical plot-reference checks execute;
visual plot review remains pending. This does not accept a real installation or
coursework design. See evidence/native-riser-route-regression.json.

`examples/elbow-riser` reuses the actual IFC/pressure/clash/route/native adapters with a new namespace and explicit independent inputs. The source data declares a 60/75 mm bore/OD, 0.24 m radius, negative-X/positive-Z elbow, 1.8 m vertical riser, 1.2 m horizontal branch and 2.04 m endpoint rise. Density 997 kg/m3, viscosity 0.0012 Pa s, 0.00006 m3/s demand, excess K 0.6, 25000 Pa supply total pressure and 2000 Pa terminal target are synthetic assumptions, not inherited measurements or product ratings.

```powershell
.venv/Scripts/python -m pip install -e ".[bim,network,clash]"
.venv/Scripts/python -m bsa.workflow execute examples/elbow-riser/plan.json --out runs/riser-delivery --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
.venv/Scripts/python -m bsa.workflow verify runs/riser-delivery
$env:BSA_TEST_AUTOCAD='1'
.venv/Scripts/python -m unittest discover -s tests -p test_elbow_riser.py -v
```

## Independent numerical checks

The saved straight-plus-quarter-circle length is `3 + pi*0.24/2 = 3.376991118 m`. Independent Poiseuille friction is 0.764394424 Pa, declared excess minor loss 0.134689627 Pa and `rho*g*2.04` is 19945.549302 Pa. The calculated downstream total pressure is 5053.551614 Pa. The test derives these values independently from the explicit scenario and compares individual terms, not just a global pass flag. Total pressure is the tree adapter's contract; this does not extend the EPANET static-head adapter to finite fittings.

All three saved hollow elements and two actual contacts pass native mesh/solid coverage. The independently declared 15 mm clearance and 0.085 m joint regions pass both outside-to-full proofs. These thresholds are scenario assumptions, not regulation or product clearances.

Flow goes from the left arc end upward toward the right branch: clockwise in the X/Z sheet. DXF stores the same geometric quadrant as a counterclockwise 90-to-180 degree ARC. Saved source port order and pressure topology remain unchanged; no hydraulic reversal or chord substitution is introduced. The drawing is an elevation at Y=1.2 m, with a 72 mm expected native PDF reference for the 1.8 m axis at 1:25.

An explicit 20000 Pa supply control leaves only 53.551614 Pa at the end and fails the 2000 Pa target. The actual failed calculation and IFC remain retained; dependent clash/drawing/native tasks stay pending without output directories. Integrity verification still passes: a correctly retained engineering failure is not a corrupted run.

## Layout failure found by reuse

The original source/geometry/scale workflow completed, but its actual PDF showed the bend leader crossing the turn and lying over the branch. That baseline fails the quoted graphic requirement and is retained as failed visual evidence. Tool execution status was never sufficient for semantic/visual acceptance.

The corrected [route annotation planner](IFC_ROUTE_DRAWINGS.md) moves the TURN label above BRANCH and routes outward around conservative obstacles. Numeric layout evidence is reconciled to saved DXF leader segments, then all geometry and GUIDs are checked after independent AutoCAD reopen. Actual PDF inspection remains a separate gate.

Evidence under `docs/evidence/elbow-riser` retains the original bad sheet, corrected native DWG/PDF, source snapshots, pressure/clash/layout checks, inadequate-supply control and test/review records. Product/joint/support/insulation detail, BIM-viewer review, formal installation sheets, source/code applicability and complete engineering acceptance remain pending.

Four actual independent-riser tests passed, including AutoCAD reopen and the failed supply control. Nineteen related regression cases passed for the original route, graphic routing and workflow source tracking. These are 23 distinct tested cases, not a claim of a new full-suite run. The final corrected native model contains 21 entities and 19 GUID-linked entities; the printed reference measured 71.966667 mm. Five source-linked review rows pass their limited synthetic checks. The R2 supplementary experiment binds the separate negative run to the baseline network, checks that only name/supply differ, and retains actual negative inputs/results; it is not mislabelled a render or the unchanged positive run. Original workflow and automatic visual-pending fields are retained; full design acceptance remains false.
