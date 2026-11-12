# Source-checked surface recognition

Registered provider `moosas.surface-room-recognition` exposes capability
`spatial.surface-room-recognition` through bsa.modules. It calls the pinned
KLEGB/MOOSAS transform in a separate Python process and returns contract
`bsa.spatial-polygons/1`,rather than replacing concave rooms with bounding boxes.
The existing box-space exchange contract/providers remain separate.

```powershell
.venv/Scripts/python -X utf8 -m bsa.modules examples/moosas-transform/l-shaped-room.request.json --provider moosas.surface-room-recognition --upstream tools/moosas-review --deps tools/moosas-exchange-deps --out runs/new-common-recognition
```

The exact request sources are `geometry` and `expectations`. The latter binds
the geometry SHA256,metre units,declared classification,source room IDs,planar
single-ring boundaries,height,floor elevation and explicit length/area tolerances.
These expectations require source interpretation;the provider does not infer or
authenticate them. Unsupported holes,sloping/variable-height spaces,arbitrary
architectural recognition and other unsupported semantics are not established.

This initial worker supports repository-local geometry,runtime and output paths.
An explicit clean upstream checkout and isolated dependency directory are host
arguments,never commands selected by documents. Missing/disabled runtime is
unavailable;failed execution or source correspondence produces no successful
payload. External coursework workspace support and automatic workflow dispatch
remain unfinished.

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
