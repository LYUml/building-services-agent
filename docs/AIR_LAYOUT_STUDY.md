# Declared diffuser layout alternatives

Directional cases now record polygon-hit coordinates,source component/ring
indices (exterior or interior),screened endpoints and controlling geometric
candidates. Coincident controls retain both candidates. This is topological
provenance,not wall/column semantics or verified jet interaction. Existing pinned
Shapely nearest-point/ring operations are reused without a new engine. Ten
layout/allocation tests pass,including interior-hole and aligned/off-axis cases.
A fresh private three-layout replay records960directions;the current aligned
alternative has280midpoint and40boundary controls. All320nearest boundary hits
belong to exterior rings. Physical L/installation/ADPI applicability stays pending.

`bsa.air_layout_study` compares explicit position alternatives using existing
air_allocation.prepare,Shapely2.2.0 service geometry and fluids1.3.1 bounded throw
interpolation. It retains the original load assumptions,total airflow,terminal
IDs and catalogue. The host agent authors design alternatives;the tool does not
infer a physical jet model or automatically select an accepted layout.

```powershell
.venv/Scripts/python -m bsa.air_layout_study runs/project/allocation.json runs/project/lookup.json runs/project/layout-study.json --out runs/project/layout-comparison
```

The study JSON contains exactly basis,panel_size_m,ratio_range,references and
variants. Panel dimensions are explicit planar width/height in metres;the basis
and source/hash references explain product size,axis alignment and selected
diagnostic ratio interval. References use the existing relative-path/hash map.
They pin source bytes without authenticating the design interpretation.

Each variant contains a unique id,basis and changes list. Each change has exactly
id and center_m. IDs must already exist and cannot be duplicated. An empty list
retains the original layout. No terminals are added or removed. Explicit position
choices remain design choices;they do not become measured or course-given facts.

For each alternative,the existing allocation engine recomputes clipped service
areas and conserved max/minimum flows from unchanged classified load inputs.
Axis-aligned panel rectangles are checked against the interpreted polygon and
each other. These envelopes exclude product depth,ceiling/elevation,insulation
and installation constraints. Invalid/outside/duplicate centres reject rather
than generating a fake feasible layout.

For each of four cardinal rays,the nearest interpreted polygon boundary includes
holes. A geometrically aligned neighbouring centre supplies a midpoint candidate.
The shorter ray length is compared with the allocation-cell ray length. The
1e-7m coincidence threshold is numerical bookkeeping,not a permitted installation
offset or validated jet spread. Off-axis neighbours do not become opposing jets.
Neither length is automatically an authentic ASHRAE characteristic length:
wall/column semantics,outlet pattern,ceiling and intersecting-flow interpretation
still need source/engineering review.

Maximum/minimum bounded throw lookups use the screened ray lengths and declared
diagnostic interval. Out-of-catalogue and outside-interval cases remain visible;
no clamping or criterion changes are made. A geometric_candidate result means
only no reported panel,ray-consistency or interval issues. All results remain
selected=false,ADPI_verified=false and design_accepted=false. CAD,connections,
new flow-dependent sizing and complete acceptance must follow separately.

The new output contains study.json and a summary index.html. Every source and
method is pinned before/after evaluation. Existing studies and original inputs
are preserved. The adapter introduces no new dependency or optimisation engine.

Twenty focused tests pass across layout study,allocation binding and throw
lookup. Actual80-terminal comparison retained three alternatives and unchanged
total flow. The original positions have8 cell/ray differences;using the newly
screened ray lengths yields16 diagnostic interval issues. This is not a change
to the old report's cell-length results. Aligning only the upper8 outlets removes
the differences but leaves2 interval issues. Aligning24 lower right outlets to
the existing upper columns has no panel boundary/overlap,cell/ray or interval
issues across320 directions and640 flow cases. This last alternative is still
unselected and has not been written into CAD. See
[executed evidence](evidence/air-layout-study.json).

Subsequent source-bound [terminal revision](TERMINAL_LAYOUT_REVISION.md) has
written and natively verified a separate copy of the24-position alternative and
selected it for continued design. The immutable comparison above remains an
unselected study record. Selection and later native evidence are recorded
separately;the original baseline and unresolved engineering acceptance survive.
