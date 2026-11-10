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

## Boundary pressure paths

The saved ports and directed product/interface edges now form a checked local
one-inlet divergent tree. Every product and port must belong to at least one
inlet-to-outlet path; merges, disconnected cycles and more than256 outlet paths
reject. Shared-cap interface steps record connectivity only, without claiming
verified physical joint losses. Each path retains its outlet flow, ordered native
port/product identities, known straight contribution and missing fitting-path
count. Unknown full path pressure remains null. Parallel outlet paths must never
be summed into a system pressure drop; a common straight can occur in multiple
paths without becoming multiple physical ducts. Critical path stays null until
all applicable losses and boundary pressure requirements are established.

Actual private execution traces three outlets. One path contains no separate
straight span; two share the same saved straight. Their missing-fitting counts
are2,4,4: this includes shared fitting paths, not ten distinct fittings or ten
unique missing records. The eight unique loss paths remain unresolved. Native
tests independently check the three outlet flows, exact path adjacency and
shared-straight accounting; isolated graph controls reject a disconnected cycle
and a merged outlet. These controls do not establish product applicability.
Aggregate executed evidence is in evidence/duct-boundary-paths.json; private
source models, numerical project data and rendered reviews remain local.

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

## Additional upstream candidate investigation

`scripts/probe_hvac_pressure.py` executes only the reviewed PyPI
hvac-pressure0.1.1 wheel SHA256
`87a469dc3dd954c44da9f6b0e76ce5fffd5da8782de0490578ef8b88b402b82b`.
It imports directly from that wheel without installation, records Python/license
file hashes, and probes public APIs. It does not copy coefficient tables or
validate their numerical accuracy. See
[upstream source and MIT license](https://github.com/JeremySimonneau/hvac-fitting-loss)
and the [exact release](https://pypi.org/project/hvac-pressure/0.1.1/).

```powershell
.venv/Scripts/python -I -X utf8 scripts/probe_hvac_pressure.py tools/hvac-pressure-review/hvac_pressure-0.1.1-py3-none-any.whl --out runs/hvac-pressure-probe
```

Actual execution confirms out-of-range angle and area queries return boundary
coefficients without warnings. The candidate's SR5-1 metadata requires a rounded
branch with r/Wb=1; SR4-1 requires two parallel sides. Our equal-section tee is
sharp, and the current tapers change both width and height. Those table names
therefore do not establish applicability to the saved bodies. No production
dependency or replacement coefficient is adopted. Future integration needs
explicit bounds rejection, independently verified source/edition/geometry and
reference pressure, plus table distribution review. The publisher's
[official supplemental reference](https://xp20.ashrae.org/SupplementalFiles/PHVAC9/Fitting_Loss_Coefficients.pdf)
is a separate2021 source with its own use terms; the candidate README's2009
Handbook claim must not be treated as verification against that reference.
