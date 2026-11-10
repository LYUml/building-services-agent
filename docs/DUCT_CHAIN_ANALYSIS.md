# Source-bound local chain analysis

`bsa.duct_chain_analysis` reads the saved local chain from DUCT_FITTING_CHAINS.md,
rechecks its native geometry/connectivity/source snapshot, and binds every port
to the inherited preliminary design flow. There are no replacement IFC, flow,
air-property or length overrides.

```powershell
.venv/Scripts/python -m bsa.duct_chain_analysis runs/span-project.json runs/chain-workflow/chain --out runs/chain-analysis
```

The chain project must match the recorded producer. Source/component/native IFC
and snapshot hashes must be unchanged. The original native-sheet→sheet→schedule
ancestry supplies selected flows and air properties. Endpoint bindings and their
recorded source-node reviews determine port-flow identities. Each section/flow/
size must agree, every saved port must be covered, and linked SOURCE/SINK pairs
and products must conserve prescribed flow. External local boundary inflows and
outflows must balance. This is not a pressure-dependent flow solution or evidence
of measured site airflow.

Cross-sections come from saved native bodies: tee inner prisms, transition inner
end rings, and straight hollow profiles. Actual rectangular velocity and velocity
pressure are recorded at each port. Velocity can change across a taper while
volume flow stays unchanged. A source section ID identifies its inherited flow;
it does not replace every interior fitting port's dimensions.

## Straight contribution and incomplete pressure scope

Dimensions and extrusion length come from the saved straight span. Existing
duct_equivalent.calculate and pinned fluids1.3.1 Colebrook/Darcy friction are reused
with the original schedule's air conditions. Actual rectangular velocity stays
separate from equivalent-round friction velocity. This is the same method as
DUCT_SCHEDULE.md, not hydraulic-diameter rectangular network analysis. Source air
conditions/assumptions and applicability remain inherited rather than reclassified
as measured product/environment properties. Method and upstream friction source
hashes are recorded alongside runtime pins. See the official
[friction API](https://fluids.readthedocs.io/fluids.friction.html).

Both fitting reaches have already been deducted from the source centreline.
Friction uses only the saved separate span, never the full source centreline
again. No straight-end/taper/core fitting friction is silently included or set
to zero; applicable whole-fitting losses and friction conventions remain needed.

Each tee needs a separate incoming→outgoing loss path for each outlet; each
transition needs its own path basis. Required records identify actual product/
port GUIDs and native inlet/outlet velocities. Coefficients remain null until
rectangular geometry, flow ratio, total-pressure/reference velocity, source/edition
and included-friction conventions are established. Installed fluids conical and
Crane tee interfaces use pipe diameters; this investigation does not verify
equivalent-diameter substitution for the rectangular fittings. See the official
[fittings API](https://fluids.readthedocs.io/fluids.fittings.html). No new solver
or copied upstream fitting table is introduced.

The result retains pressure_budget_complete=false and
complete_chain_pressure_drop_Pa=null in this scoped adapter. A finite straight
subtotal is not full pressure loss, fan duty or accepted design. Product
construction, elevation/installation, full-network conditions and regional checks
remain separate. A calculated result exits2 for incomplete engineering scope.

## Workflow gates

Workflow kind duct_chain_analysis requires depends_on on an earlier
duct_fitting_chain and inherits its project/chain.ifc. IFC inventory gates must
select that same producer; the analysis can gate same-model consumers. Missing
fitting data keeps the task pending while retaining analysis.json. Required
downstream consumers stay unexecuted. Review text cannot create a pressure budget.

Native tests check16 port flows,seven products,six interfaces,four boundaries,
eight missing paths and independent straight length/pressure arithmetic. The
Colebrook residual and actual/equivalent-round velocities are checked separately.
Product/interface imbalance, incomplete port coverage, negative flows, invalid air
and empty models reject. Stage controls check pending release, forbidden overrides
and different-model gates; these mocked controls are not native geometry evidence.

The actual private local chain conserves inherited source flows. Its isolated
straight contribution is about7.119Pa with the existing method. Six fittings need
eight path-loss records; the full pressure result stays null and pressure-gated
release is blocked. This is one preliminary local case, not the completed
coursework network or a substitute for minimum-flow/ADPI checks. Aggregate
evidence is in evidence/duct-chain-analysis.json; detailed private data stays local.
