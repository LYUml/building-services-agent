# Source-checked surface recognition

The existing automatic module_exchange task already supports this registered
provider. A source-linked public workflow builder now composes recognition,
the existing HK office LPD consumer,manual acceptance and an independent
electrical calculation. The lighting consumer accepts validated polygon-space
areas as well as the previous box-space areas;it never substitutes bounding-box
area or accepts a repeated area override in the lighting basis.

Five actual workflows with the exact pinned official BEC source bytes retain
enabled,exceeded-power,unknown-fact,disabled-provider and missing-source states.
The independent electrical branch passes in every case;full acceptance remains
pending. Twenty-four related tests pass;unit rule fixtures use explicitly
synthetic source bytes and are separate from these retained official-source runs.
See evidence/moosas-recognition-lighting-workflow.json.

Registered provider `moosas.surface-room-recognition` exposes capability
`spatial.surface-room-recognition` through bsa.modules. It calls the pinned
KLEGB/MOOSAS transform in a separate Python process and returns contract
`bsa.spatial-polygons/1`,rather than replacing concave rooms with bounding boxes.
The existing box-space exchange contract/providers remain separate.

```powershell
.venv/Scripts/python -X utf8 -m bsa.modules examples/moosas-transform/l-shaped-room.request.json --provider moosas.surface-room-recognition --upstream tools/moosas-review --deps tools/moosas-exchange-deps --out runs/new-common-recognition
```

The request sources are `geometry` and `expectations`,optionally with `ifc_source`
for the saved-native IFC intake described in IFC_SPACE_SURFACES.md. With that
role,the provider replays native extraction and pins the original IFC;replacement
expectations cannot override it. The expectations file binds
the geometry SHA256,metre units,declared classification,source room IDs,planar
single-ring boundaries,height,floor elevation and explicit length/area tolerances.
These expectations require source interpretation;the provider does not infer or
authenticate them. Unsupported holes,sloping/variable-height spaces,arbitrary
architectural recognition and other unsupported semantics are not established.

Geometry,requests and outputs may now use the explicit host BSA_PROJECT_ROOT
workspace as well as the tool repository. The upstream checkout and isolated
dependency directories remain repository-local trusted host runtime paths.
An explicit clean upstream checkout and isolated dependency directory are host
arguments,never commands selected by documents. Missing/disabled runtime is
unavailable;failed execution or source correspondence produces no successful
payload. Verification requires the same explicit host workspace selection.
Unselected external siblings reject. This migration is scoped to surface/direct
IFC recognition and common module request discovery,not every other provider.

The worker explicitly uses an empty version5geometry-only template catalogue and
a1e-9m coordinate grid;it restores process-local settings after native XML reload
or failure. These are documented compatibility settings,not new upstream APIs,
materials,occupancy,HK regulations or relaxed source checks. The upstream checkout
is unmodified at dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c. Preserve Apache-2.0
attribution in THIRD_PARTY.md and third_party/licenses/moosas.txt.

Each successful payload retains the stable declared source ID separately from
the generated native ID,actual recognized boundary/area,height and elevation.
Source-boundary checking requires complete unique coverage,closure,planar
Hausdorff/symmetric-difference limits and height/elevation agreement. Verification
reconstructs the common projection from the retained recognized-space audit and
source expectations,checks saved artifact hashes and rechecks pinned methods.
It is source correspondence,not an independent geometry kernel,authenticated
execution record or proof that coherently rewritten source/audit bundles are true.

Actual L-shaped,rotated and narrow-notch fixtures complete native transform and
XML reload through the common runner. Twenty-three related tests pass,including
disabled/missing runtime,wrong floor elevation and rewritten common height.
See evidence/common-moosas-recognition.json. Prior default-grid failures and
the finer-grid source checks remain in the existing probe evidence.

Execution completion retains acceptance pending,simulation_ready false and
design_accepted false. No thermal boundary construction,system routing,physical
installation,room-load/ADPI result or whole-project conformity follows from this
geometry contract. There is no inherited polygon-to-thermal consumer yet.

Generate a new synthetic workflow without copying copyrighted sources to Git:

```powershell
.venv/Scripts/python -X utf8 examples/moosas-transform/build_workflow.py --out runs/new-recognition-inputs --sources runs/existing-official-cache
.venv/Scripts/python -X utf8 -m bsa.workflow execute runs/new-recognition-inputs/plan.json --out runs/new-recognition-workflow --moosas-upstream tools/moosas-review --moosas-deps tools/moosas-exchange-deps
```

Omit --sources to retain missing official-source checks as pending. Geometry,
watts and applicability facts in this builder are synthetic software controls,
not measured building evidence or equipment specifications. The selected BEC2024
edition in this example does not decide a real project's statutory applicability.
