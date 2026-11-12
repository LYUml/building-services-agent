# MOOSAS surface recognition fixtures

These original synthetic metre-coordinate GEO inputs exercise pinned
KLEGB/MOOSAS surface-to-space transformation, rather than building spaces in the
wrapper. They are software geometry controls, not measured buildings/designs.

- closed-room.geo: six faces of a4x3x3m closed room;expected12m2and3m height.
- two-rooms.geo: adjacent4x3x3m and2x3x3m rooms,including coincident party walls;
  expected two spaces of12m2and6m2,both3m high.
- missing-wall.geo: the first room with one side removed;expected zero spaces.
- l-shaped-room.geo: concave closed14m2room,3m high;source boundary correspondence passes.
- rotated-room.geo: rotated/translated12m2room,3m high;recognition/reload completes,
  but upstream millimetre rounding changes its area to12.00207m2and fails the
  declared fixture boundary tolerances.
- narrow-notch.geo: a4x3m footprint with a0.4mm wide,0.5m deep notch;upstream
  transformation fails with a recorded TypeError after losing horizontal references.

The latter three fixtures have explicit `.expected.json` source declarations.
`bsa.spatial_recognition_check.check` reuses pinned Shapely2.2.0 Hausdorff and
symmetric-difference operations against those declarations,with complete unique
room coverage,height and closure checks. The caller must supply positive length
and area tolerances. Here1e-6m and1e-8m2are software fixture targets,not installation
or regulatory limits. The checker does not repair geometry or authenticate source
interpretation. See docs/evidence/moosas-transform-boundary-check.json.

```powershell
.venv/Scripts/python -X utf8 scripts/probe_moosas_transform.py --source examples/moosas-transform/two-rooms.geo --upstream tools/moosas-review --deps tools/moosas-exchange-deps --out runs/new-transform-probe --empty-catalogue
```

The script requires the clean upstream commit recorded in probe_moosas_ifc.py,
and pinned rdflib7.1.4,pyparsing3.2.3and Shapely2.2.0. It invokes the upstream
pipeline and saves/reloads native MOOSAS XML/GEO. Raw worker output,source/method
hashes,recognized space metrics and failure diagnostics remain in the new output.
Zero recognized spaces can be a completed engine execution;it does not establish
complete architectural coverage. Actual caller expectations must be checked.

The default bundled catalogue fails its upstream version check. The optional
flag temporarily routes only the pipeline's resource configuration call through
the upstream configure_model_resources(template_path=...) API using an explicitly
empty version5catalogue. Native XML reload uses the same directory. Both overrides
are restored in finally blocks;no upstream files or geometry algorithms change.
The directory selects no materials,occupancy,HVAC or jurisdiction templates.

See docs/evidence/moosas-transform-probe.json for all four executed cases,
including the default failure. This probe is not a registered common provider,
DWG/RVT architectural recognizer,thermal-ready model or completed MEP design.
KLEGB/MOOSAS remains Apache-2.0;see third_party/licenses/moosas.txt and
docs/MOOSAS_MODULE_MAP.md for attribution and the fixed upstream commit.
