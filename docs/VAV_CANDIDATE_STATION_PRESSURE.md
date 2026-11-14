# VAV static-to-total candidate station study

Twenty VAV paths now have a separately calculated fully-open pressure term in
each design-flow case. The study uses the source2021LMHS static curve plus
explicit candidate reference areas, not the ambiguous IOM velocity column.
It yields374conditional numerical component values and84unresolved directed
component paths. Each of80terminal paths retains two numerical gaps: one
compound-main path and one Jplenum path. This is improved numerical coverage
under stated assumptions, not manufacturer or full-design acceptance.

## Pressure basis and source correspondence

The current official Terminal Unit Engineering PDF, SHA
3bdcce59cc18b63bdefa9e0faf4b8cc445f484fe3c2649ce258a8ed81ee0c255,
PDF7/printeda2-7, was downloaded, rendered and actually viewed. It defines the
minimum static difference across inlet and discharge with the damper fully open.
The held2021MiniCatalog A2-26/27 supplies the actual numerical static curve;
no2012performance numbers are substituted. All40bounded source interpolations
are freshly reconciled to their prior source extraction and independent Decimal
arithmetic. The IOM29supported/11unsupported baseline remains separate.

At equal-flow reference stations the pressure identity is
deltaPt = deltaPs + rho(Q/Ain)^2/2 - rho(Q/Aout)^2/2.
The existing loss_reference numeric guards and declared pressure identity form
the thin static_total_balance helper; it is not a new loss engine. Existing
MITfluids1.3.1 interp, prescribed_flows, boundary_paths and source_pressure_ledger
are reused. Four tests/three subtests check cancellation of an intermediate
station in series, equal area/static regain, signed incompatible passive cases,
and missing/zero/boolean/unlabelled station inputs. Negative results are not
clamped or converted into accepted device losses.

The upstream reference area comes from the saved nominal circular duct port.
The downstream reference comes from the saved lined J-entry candidate geometry.
Their correspondence to the manufacturer's test sections is assumed, not
confirmed. Test density is also unverified; the declared design air density is
retained. No bore is inferred from an outside collar. All140manufacturer-unknown
port areas remain null;100candidate geometric areas are exposed separately.
The new signed pressure values have no invented manufacturer K/referenceVP.

## Executed current-model and path checks

The current stepped-joint IFC6abd9110... is read. All584other distribution
representations match the original logical model; the20Jchambers use their
separately verified candidate geometry. All1287frames and603flow links match.
The actual604product graph re-derives and reconciles every1287flow value in each
case. Nonflow sleeve/bondline accessories do not become extra hydraulic spans.
New analysis, fitting-data and pressure-ledger outputs are reconstructed in a
new private run; historical method-bound records are not rehashed or overwritten.

Each terminal's component subtotal changes by exactly its one VAV term. The
fully-open conditional VAV range is24.962..42.242Pa at maximum and3.919..7.026Pa
at minimum. No extrapolation into the IOM's unsupported low-flow region is used:
these values use the separate bounded2021static curve and declared station areas.
This is not evidence that the IOMvelocity column was identified or corrected.

The new160path rows also retain one previously verified catalogue terminalPt
boundary comparison, under the earlier assumed common0Pa room-static reference.
Ps and neck velocity pressure are not added again. The rigid-equivalent branch
assumption, three logical equipment interfaces per path, joints, measurement
stations, interactions and actual VAV control state remain unresolved. In
particular, a fully-open minimum-flow baseline is not an actual throttled VAV
operating point. All complete pressures, critical path and fan duty stay unknown.

Course outputs under05_Calculations/Connection_Layout are40VAVrows,160terminal
path rows, an HTML study and VAV_Candidate_Station_Pressure_Check.json, matching
docs/evidence/vav-candidate-station-pressure.json. No geometry changes or fresh
native drawing acceptance are claimed for this calculation-only milestone.

References: https://www.krueger-hvac.com/file/9262/Terminal_Unit_Engineering.pdf ;
https://handbook.ashrae.org/Handbooks/F21/SI/F21_Ch21/F21_Ch21_si.aspx
