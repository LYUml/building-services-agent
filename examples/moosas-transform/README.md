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

The probe now accepts explicit host `--point-grid-m 1e-9` for a finer process-local
upstream coordinate/recognition grid. It sets geom.POINT_PRECISION before pipeline
import/execution,keeps that selection through native XML reload,and restores the
original value in finally,including on catalogue failure. This is an explicitly
documented constant override,not a new upstream public configuration API. No
upstream file or geometry algorithm is patched. Default operation remains1mm.

With the finer grid,the rotated and narrow-notch inputs pass their original
1e-6m/1e-8m2source correspondence targets. The rotated boundary Hausdorff error is
about3.79e-10m;its symmetric-difference area is about2.11e-9m2. The notch matches
exactly in this trial. Closed/two-room/missing-wall controls still return1/2/0spaces.
Eight tests pass with BSA_TEST_MOOSAS_TRANSFORM=1,including actual upstream runs,
default precision failure and restoration after failed catalogue configuration.
See docs/evidence/moosas-transform-finer-grid.json. This bounded result does not
validate finer numerical grids for arbitrary buildings or silently remove small
features;each future source still needs its own correspondence check.

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
