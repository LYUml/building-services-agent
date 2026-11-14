# Reduced-branch network and two-flow pressure study

The thirteen source-linked local revisions now execute in a separate copy of
the original compound-network scenario. The original network and the later
Connection_Layout VAV relocation/duct-sizing scenario remain unchanged. These
are not yet one unified coursework design.

The project-specific composition reuses pinned IfcOpenShell 0.8.5 body-copy,
property and port APIs, the existing native inventory/tree inspector,
source_network_analysis.calculate, source-linked table interpolation, pressure
ledger, Manifold/IfcOpenShell clash engines and native CAD adapters. It does not
add a geometry kernel, flow solver or coefficient database. This composed trial
is not registered as a common MCP producer; private scripts and detailed source
data remain in the selected project workspace.

An actual first trial failed expected-property correspondence. Inspection of
the installed edit_pset implementation showed that it removes entries from the
caller-supplied properties dictionary. Passing a deep copy preserves the
independent expected record; no validation condition or tolerance was relaxed.
The failed trial remains separate. Changed branch caps are checked against the
literal inspected branch profile; unchanged canonical source profiles are
retained only after native cap and source geometry correspondence checks.

The revised saved IFC has 89 bodies, 197 owned ports and 88 directed interfaces,
forming one connected tree with the same 20 outlet boundaries. Independent
source/saved replay preserves all 45 retained straights, their source flows and
friction, and all 33 requirement IDs. All 88 material cap pairs match. The same
unwaived raw numerical policy covers all 89 represented bodies and finds zero
material intersections, but 88 clearance violations at connected interfaces.
Those software tolerances are not installation clearances. Neither connected
ports nor material cap agreement waive the raw findings.

There are 63 fitting paths, compared with the original 76. Removing 13 branch
tapers removes 3 previously populated transition values and 10 unknown paths.
One revised sharp branch obtains a new bounded source value. Thus 29 paths have
conditional numerical values and 34 remain unknown, compared with 31/45 in the
parent. All 28 retained original finite contributions reconcile independently;
the new branch matches the separate Decimal source-point audit. No complete
pressure saving is inferred from the old unknown branch pressure.

The original brief's 40-percent minimum-flow condition is also executed on the
same saved model. All 197 port flows independently reconcile to 0.4 times their
maximum source values, with all 20 outlet paths conserved. Straight friction
and elbow Reynolds quantities are recalculated rather than scaled blindly.
Initially one maximum-flow binding covered only the published high-Re plateau,
so its minimum-flow query correctly remained unknown. The same original
ASHRAE 2021 printed page 12 was rendered and inspected: its lower-Re correction
row supplies the missing support. Existing bounded 3D interpolation now applies
that row with the unchanged radius condition and numerical upper study bound.
Independent Decimal arithmetic agrees, the maximum case and other fitting
values stay unchanged, and both final flow cases retain 29 conditional values
and 34 gaps. No source extrapolation or physical acceptance follows.

The full revised rigid-network overview reuses native IFC silhouette projection,
ezdxf and isolated AutoCAD save/reopen/plot. All 89 product GUIDs survive in
linked contours; 112 saved entities reconcile. The actual A4 1:200 page was
inspected: readable headings/notes and no observed contour/reference overlap or
clipping. The 10 m reference measures 49.995667 mm against 50 mm expected. This
is not an installation drawing or full equipment/architectural coordination.

Private results: project runs/reduced-branch-network-reviewed, including the
independent review, maximum/minimum ledgers, Reynolds source extension and
actual drawing. Clean study DWG/PDF/IFC and a two-flow pressure review are in
the selected project's delivery folders. Only scoped aggregate evidence is
published here: [network evidence](evidence/reduced-branch-network.json).

Remaining work includes 21 junction and 13 transition numerical gaps, source
applicability, whole-fitting friction/stations, close-fitting/joint interaction,
flexible ducts, terminals/equipment, boundary pressures, load/ADPI, architecture
and installation review. Full pressure, critical path and fan duty remain null.
Producer registration and final rebase onto one selected coursework scenario
are still required before unified delivery acceptance.
