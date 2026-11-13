# Unequal tees from source rays and explicit construction choices

The standalone source_tee_candidates adapter reuses the existing rectangular tee,
centred-transition composer, source fit review and selected elbow backbone. There
is no new geometry kernel, equipment catalogue, flow solver or dependency.

```powershell
$env:BSA_PROJECT_ROOT='C:/ABSOLUTE/COURSEWORK'
python -m bsa.source_tee_candidates run SELECTED_ELBOW_RUN POLICY --out FRESH_OUTPUT
python -m bsa.source_tee_candidates verify FRESH_OUTPUT
```

The CLI retains exit 2 for this incomplete candidate/network study, including
an integrity replay. Inspect the returned integrity/status fields separately
from full engineering acceptance; a partial IFC file alone is not a completed run.

The selected source must already verify through actual native-sheet/sizing ancestry
and the elbow selector. POLICY contains exactly basis and nodes; every original
unequal-section tee must have an explicit row. Row fields are core_section_m,
main_half_length_m, branch_length_m, start_length_m, end_length_m,
upstream_angle_degrees, transition_method, classification and source. All geometry
is a declared study choice, not a default product or inferred regulatory limit.
transition_method is upstream_mep_shape or explicit_station_brep; see the explicit
station variant in RECTANGULAR_TRANSITIONS.md. Legacy upstream disagreement still
blocks; it never silently switches authoring method.

The compiler identifies exactly one opposed source main-axis pair and perpendicular
branch, builds a right-handed native placement, inherits original XY and classified
elevation/gauge, and preserves source external widths/heights and supply directions.
Equal core/end sections stay bare; unequal ends get centred transitions. Source
angle/section dimensions determine taper stations. Every local source ray/size/end
is assessed with the existing fit tool; installation elevation/roll remain unverified.

The budget deducts both original selected elbow reaches and every declared tee
reach on each original source section, retaining the elbow policy's existing
minimum remainder. Every responsible tee at an insufficient section stays blocked;
its complete declared budget remains recorded even when no body is authored.
Other fitting types/physical joints stay unknown. Only eligible isolated candidate
assemblies are authored, through the existing native composer and all its material,
volume, bore, port, topology and schema checks. Original backbone geometry is not
trimmed or merged by this adapter. The two multi-branch nodes remain unattempted.

Verification replays source compilation/budgets from the unchanged source/policy
and inspects each saved native assembly again. Exact source/method and artifact
pins remain; changed source/failed authoring must not be marked complete. Existing
tee/transition/composition/fit runs now permit the explicitly selected external
project workspace, with unselected outputs rejected and source protections retained.

## Executed real study

All 15 original unequal tees have explicit classified candidates. The actual study
uses maximum incident nominal width/height for the core, a declared 0.1 m core-arm
extension beyond half-width, 0.05 m transition straights, and 30-degree included
angle. These are host-selected geometry assumptions, not manufacturer dimensions,
code requirements or installed measurements. The inherited positive remainder
is unchanged. This scenario is not a generally recommended fitting specification.

Fourteen local source-matched assemblies author and independently replay: 42 native
fitting components, 98 owned ports and 28 internal cap-matched connections. Their
source inputs retain all 33 requirement IDs. A separate actual native/source-fit
run also checks one saved candidate in the external project workspace.

ROOT is blocked by the combined original elbow/declared tee reaches on A-03 and
D-01. This proves failure of this component combination, not that every possible
design is impossible. No smaller lengths or altered source routes are substituted.
The original 47-straight/10-bend backbone and its failed coordination are unchanged;
the new assemblies have not been merged into it. Whole-network fitting/clearance,
pressure, products and installation acceptance remain pending. The actual J0 IFC
preview was inspected; some labels overlap and it is not a delivery drawing.

Native/source tests and original workflow regressions pass in two overlapping
suites (11 and 9 executed checks, no skips). See [aggregate evidence](evidence/source-tee-candidates.json).
These counts describe test executions, not complete engineering acceptance.
