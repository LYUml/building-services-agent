# Native short-stub straight-friction component

Reuse decision: compose existing network.friction_factor and pinned fluids1.3.1
core.Reynolds,K_from_f,dP_from_K. Existing laminar64/Re and turbulent Colebrook
Darcy methods stay authoritative;no new friction solver. Pin both fluids source
files and network.py. Existing upstream licenses/attribution remain unchanged.
The full tree calculator requires supply/target/minor-loss quantities that are
not known here,so this thin adapter reuses its friction engine without inventing
supply pressure,velocity targets or zero fitting losses.

`python -m bsa.spatial_stub_friction STUB_REPORT --basis BASIS --out NEW` (one line)
requires verified terminal-stubs.json. It reads exact saved hollow profile bore
and depth,native directed port endpoints and saved maximum/minimum flow
properties. Profile depth must match native port separation. Density is inherited
from the corresponding original room air-balance input,through hash-pinned
stub/inlet/envelope/performance/allocation/balance ancestry. It cannot be supplied
again by the caller. Native dimensions retain their original study basis so
model-derived does not become a claim of installed measurement.

BASIS has exactly dynamic_viscosity_pa_s (Pa.s) and roughness_m (m),each a
value/unit/source/classification record. No replacement density,flow,length or
bore is allowed. Positive finite viscosity and nonnegative roughness with
relative roughness<0.05 are required. Transitional2000<=Re<4000 cases retain
unknown friction and a request for a supported justified method;never extrapolate.

Outputs include individual maximum/minimum velocity,Reynolds,Darcy factor and
straight friction inPa for each stub. Signed rho*g*dz is a separate geometric
term based on actual flow-direction endpoint elevations. It is not added to
friction as a fan duty or ambient-referenced pressure. Parallel branch pressures
are not summed,and terminal static/total pressure and fitting losses are not
inserted. Native/source/method pins and complete replay protect the result.

Actual native/MOOSAS chains produce identical six-stub calculations with12flow
cases. Density remains source-classified1.25kg/m3 from the original assumed room
basis. Viscosity1.8e-5Pa.s and roughness0.09mm are explicit synthetic assumptions,
not measured state,manufacturer data or authenticated chart conditions.
See evidence/spatial-stub-friction.json.

These stubs have L/D<1. Fully-developed friction is only a theoretical component
under the declared model;entrance,developing-flow,exit and actual joint effects
remain unverified. engineering_status stays pending even when numerical cases
calculate. No whole-network pressure,fan selection,compressibility/air-state,
regulatory or design acceptance is established. Original six interface-clearance
failures are untouched. Workflow-task and further performance integration remain
unfinished.

Validation:14 related tests pass. Laminar pressure matches independent
Hagen-Poiseuille arithmetic;the turbulent factor satisfies an independent
Colebrook residual. Transitional pressure stays unknown. Native-profile/port,
inherited flow/density classification,report tampering and forbidden replacement
inputs are checked alongside existing circular-tree and air-load regressions.
