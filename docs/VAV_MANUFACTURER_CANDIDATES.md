# Manufacturer VAV candidates

Twenty precise Connection_Layout group flows now have a separate Krueger LMHS
base-unit capacity and minimum-static-pressure study. No equipment is selected
or inserted into the IFC. Originals remain preserved.

The official MiniCatalog source is SHA-pinned. PDF pages2,5,24 were rendered and
visually inspected: printed A2-4 capacities, A2-7 dimensions and A2-26 pressure.
Duplicate pressure columns on A2-27 agree. Smallest capacity-compatible choices
are two size9, sixteen size10 and two size12. This is not a product optimum.

The existing pinned fluids1.3.1 interpolation is reused with explicit range
guards; independent Decimal arithmetic agrees for supported queries. All160
candidate/condition cases retain capacity/range rejections. All40 conditions of
the smallest capacity candidates fall within published brackets. Estimated
minimum static differences range22.0920–40.3656Pa at maximum flow and
4.1730–7.1161Pa at the given40percent minimum. Linear interpolation is an
explicit design approximation, not K-Select execution.

Static differences are not total-pressure losses. Actual collars are undersized
relative to nominal inlets; casing dimensions do not establish clear outlet
areas. Inlet transitions, four-outlet plenums, flex routes, control/acoustics and
installation clearances remain unresolved. The rigid-network31conditional/
32unknown fitting result is unchanged. No unknown is made zero.

Derived course HTML/JSON:05_Calculations/Connection_Layout/VAV Manufacturer
Candidate Review and VAV_Manufacturer_Candidate_Check. Private source/scripts/
160case evidence:07_Agent_Work/runs/vav-manufacturer-capacity. No source PDF is
published. See [safe evidence](evidence/vav-manufacturer-candidates.json) and
[official source](https://www.krueger-hvac.com/file/4034/LMHS_MiniCatalog.pdf).

Next: source-backed interfaces and equipment/control/acoustic selection, then
static/total station reconciliation before adoption into the actual network.
