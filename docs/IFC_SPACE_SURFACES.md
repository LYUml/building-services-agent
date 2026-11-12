# Saved IFC spaces to recognition input

Provider `moosas.ifc-room-recognition`,capability `spatial.ifc-room-recognition`,
now accepts original `ifc` and `settings` sources directly through bsa.modules
or an existing module_exchange workflow task. Settings contain exactly explicit
positive length_tolerance_m and area_tolerance_m2. The provider composes this
intake and the existing moosas.surface-room-recognition provider;no second engine
or orchestration framework is introduced. It forwards the declared common frame
and source IDs and verifies the retained nested result and original IFC lineage.

Three actual direct-IFC workflows with pinned official BEC source bytes verify
enabled,disabled and missing-runtime states. Complete three-space recognition
feeds geometry-derived areas into the existing HK LPD consumer. Independent
electrical work continues when recognition is unavailable. Twenty-five related
tests pass,including unknown settings,no extraction on missing/disabled runtime,
altered public payload and dropped lighting-space GUID. Test rule-source controls
use synthetic bytes;the retained scenario evidence uses the actual pinned file.
See evidence/direct-ifc-recognition-workflow.json.

For the synthetic native fixture,generate a complete test workflow with:

```powershell
.venv/Scripts/python examples/moosas-transform/build_workflow.py --out runs/new-ifc-inputs --ifc runs/new-native-fixture/polygonal-spaces.ifc --length-tolerance-m 1e-6 --area-tolerance-m2 1e-8 --sources runs/existing-official-cache
.venv/Scripts/python -m bsa.workflow execute runs/new-ifc-inputs/plan.json --out runs/new-ifc-workflow --moosas-upstream tools/moosas-review --moosas-deps tools/moosas-exchange-deps
```

The builder's watts and applicability facts remain explicitly synthetic;passing
this example does not establish real equipment data or statutory conformity.
Disable the composed task provider with `--disable-module-provider
moosas.ifc-room-recognition`;provider selection applies to declared workflow tasks.
Standalone surface recognition remains available for its separate source contract.

`bsa.ifc_space_surfaces` reads every saved IfcSpace Body and generates MOOSAS
surface geometry,source expectations and a common recognition request. It reuses
IfcOpenShell0.8.5 world-SI geometry,Manifold3D3.5.4 closed-solid validation and
Shapely2.2.0 planar unions,with NumPy2.5.4. No new geometry kernel is implemented.
Heights,elevations and areas come from native bodies,not bounding-box area or
IfcSpace quantity metadata. No height is invented from a2Dplan.

```powershell
.venv/Scripts/python -X utf8 -m bsa.ifc_space_surfaces path/to/source.ifc --out runs/new-surface-intake --length-tolerance-m 1e-6 --area-tolerance-m2 1e-8
.venv/Scripts/python -X utf8 -m bsa.modules runs/new-surface-intake/request.json --provider moosas.surface-room-recognition --upstream tools/moosas-review --deps tools/moosas-exchange-deps --out runs/new-recognized-spaces
```

The tolerance values above are software-example targets,not regulatory or
installation limits. Callers must select and review actual project tolerances.
The intake supports explicitly selected BSA_PROJECT_ROOT paths;the current
MOOSAS worker still requires repository-local inputs/output. External coursework
recognition remains unavailable until that worker is migrated;do not silently
copy private project data back into the tool repository.

The initial boundary is IFC4 with an explicit SI metre-based unit,including
prefix conversion such as millimetres. All one-to-100 saved spaces must have
unique GUIDs and one Body. Supported bodies are planar faceted geometry or
linear polygon/rectangle extrusions. Each native mesh must be one connected
positive-volume closed solid. Every vertex belongs to the bottom/top planes;
floor/ceiling footprints,vertical side placement,total side area and native
volume must agree with the resulting vertical prism.

Holes,curved profiles,sloping/variable-height spaces,unsupported representation
items or missing bodies reject rather than dropping spaces,filling holes or
flattening geometry. These are explicit restrictions,not an arbitrary IFC reader.
World-SI coordinates are not proof of surveyed/georeferenced site positioning.

The generated request adds optional `ifc_source` alongside geometry/expectations.
The common provider pins the original IFC and replays this extraction before
accepting the recognized result. Regenerating hashes for replacement expectations
cannot substitute dimensions absent from that saved source. The provider's
verifier also replays source extraction. If the native source runtime becomes
unavailable,the adapter produces unavailable without a successful payload.

Actual saved synthetic IFC with a14m2concave room and24/30m2neighbouring rooms
passes native IFC4 schema/EXPRESS checks,complete GUID coverage,extraction,
MOOSAS recognition and source replay. Native volumes are42/72/90m3. Nineteen
distinct related tests pass,covering millimetre conversion,unsupported geometry,
source mutation,rehashed replacement expectations and runtime unavailability.
The latter is an explicit mock control,not a real policy-change observation.
See evidence/ifc-space-surface-recognition.json.

Generate the original synthetic fixture with
`examples/moosas-transform/build_ifc.py --out runs/new-native-fixture`.
It preserves the original box-authoring output and writes a new source copy
containing a native concave profile. Original MEP devices are test context and
have not been coordinated to the changed room. This is no completed engineering
design,thermal-ready model,IFC-to-DWG drawing set or full regulatory acceptance.
