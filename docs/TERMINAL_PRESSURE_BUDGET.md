# Terminal pressure and conditional path budget

The existing source-bound smooth-rigid pressure study stopped at80terminal neck
connection planes. A separate terminal-pressure consumer now adds the reviewed
nominal8inch Model1400 catalogue pressure requirement once to each path, in both
flow cases. It produces160conditional budgets tied to original endpoint GUIDs.
The original pressure ledgers and classroom/manufacturer ADPI studies are unchanged.

## Executed source and upstream reuse

The pinned2012Krueger performance PDF SHA073c639219b28068a0c8190a926d493e42a12c0918db464ee8439c55a3994aef,
PDF2/printedB1-12, was rendered and actually viewed. Its9nominal8inch rows are
for24x24inch/600x600mm panels without damper. The existing manufacturer_adpi
catalogue reader is reused unchanged. Existing MIT fluids1.3.1 interp supplies
piecewise linear pressure interpolation with squared flow as the independent
variable. No new numerical engine, product selection or K-Select MCP is built.

The squared-flow method is an explicit comparison assumption, supported by the
source rows rather than an asserted manufacturer algorithm. Holding each of7
internal rows out yields14Pt/Ps checks. The residuals are compatible with an
assumed nearest0.1Pa rounding of both target and interpolated endpoint values.
An additional constantP/Q-squared compatibility screen uses explicitly assumed
nearest1L/s and0.1Pa rounding. These are source-consistency diagnostics, not
manufacturer accuracy, experimental uncertainty or installation allowances.

The user's existing K-Select toolkit CLI capabilities and report-verify commands
were actually called on two original saved native PDFs. Model,neck,module,border,
flow,throw pattern and terminal velocity checks pass; source hashes remain
unchanged. No desktop operation or native software rerun occurred. Toolkit commit
and both PDF hashes are recorded in evidence/terminal-square-flow-pressure.json.

At the native112CFM effective flow, linear-flow interpolation gives3.98757Pa;
squared-flow interpolation gives3.64408Pa. The latter lies within1.24544..3.73633Pa,
the interval implied by assuming nearest0.01inch-water display rounding. At280CFM,
both methods lie within the native0.09inch-water display interval. This removes
the numerical mismatch for this comparison method; it does not prove that the
software uses that method or remove its throw-label/acoustic/ADPI limitations.

## Actual path results and limitations

All80maximum and80minimum prescribed terminal flows lie inside33..297L/s source
support. Conditional cataloguePt is19.731..44.780Pa at maximum and3.155..7.187Pa
at minimum. The new budget is represented straight friction plus conditional
component contributions plus one terminalPt. Ps and neck velocity pressure are
not added again. Source-bound terminal pressure is not inferred from nominal
neck dimensions or envelope area.

Treating cataloguePt as terminal inlet total pressure relative to a common0Pa
room-static reference is an explicit study assumption. Source test-plane,
physical collar and actual connection correspondence remain unverified. The
underlying branch construction remains the separate smooth-rigid candidate,
not installed corrugated flex. Every path retains3numerical component gaps;
104unique compound/VAV/plenum paths and global physical/friction/interaction
checks remain unresolved. No complete pressure, hydraulic critical path or fan
duty is claimed; partial sums are not lower bounds, and parallel paths are never
summed. Three source-domain/type rejection controls also execute.

No geometry changed, so the existing reopened native DWG remains the geometry
reference. No new native plot or final installation acceptance is claimed.
Course outputs under05_Calculations/Connection_Layout are Terminal Pressure and
Conditional Path Budget.csv/.html and Terminal_Pressure_Budget_Check.json.

## Plenum research retained separately

Manufacturer J-outlet dimensions alone did not supply an applicable performance
curve. The held ASHRAE fan-discharge-to-plenum data and the upstream Crane
single-tee function are not substituted for this lined four-outlet attenuator.
The Illinois primary research PDF endpoint returned403 in both browser and
direct fetch; its equations were not read or adopted. Plenum losses remain null.
