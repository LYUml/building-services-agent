# Calculation-bound electrical schematics and schedules

The original thin adapter `bsa.three_phase_drawing` reuses existing Graphviz layout, ezdxf authoring, AutoCAD Core Console, source-DWG reopening and fixed-paper PDF verification. It does not rebuild those engines, attach to a live user document, or impersonate an IFC model. Electrical entity identity is stored in `BSA_ELECTRICAL` XDATA with kind/ID and the exact study hash.

## Executed use

Start with a passing `three_phase` workflow task under [THREE_PHASE_NETWORKS.md](THREE_PHASE_NETWORKS.md). `--study` is its task directory containing `three-phase.json` and `native/study.json`, not the standalone solver's output directory.

```powershell
.venv/Scripts/python -m bsa.three_phase_drawing examples/three-phase-network/project.json --study runs/three-phase-workflow-v1/power-flow --out runs/new-electrical-schematic --dot tools/freecad-1.1.4/FreeCAD_1.1.4-Windows-x86_64-py311/bin/dot.exe --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe'
```

Omitting AutoCAD in this standalone command produces editable DXF and CSV only; it does not establish DWG/PDF acceptance. Changed source/study artifacts and failed numerical/study targets are rejected before authoring. Hash association is not authentication or source-interpretation verification.

## One workflow invocation

```powershell
.venv/Scripts/python -m bsa.cli workflow examples/three-phase-network/drawing-plan.json --out runs/new-native-electrical-workflow --three-phase-python tools/pandapower-runtime/Scripts/python.exe --graphviz tools/freecad-1.1.4/FreeCAD_1.1.4-Windows-x86_64-py311/bin/dot.exe --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe' --review runs/new-native-electrical-review.json
```

Workflow kind `three_phase_drawing` requires `depends_on` naming an earlier `three_phase` task. The project and study are inherited; replacement project/settings and executable commands in plan data are rejected. Unlike the standalone command, this workflow task requires both Graphviz and AutoCAD because its scope includes native DWG and measured PDF. Missing tools or a nonpassing study leave it pending without calling the drawing adapter. Upstream artifact bytes are pinned when the study finishes and rechecked immediately before drawing; changed bytes fail the drawing task. Downstream `requires_pass` applies normally.

The actual three-requirement synthetic plan executed numerical study and native drawing successfully, with full visual/engineering review pending (CLI exit 2). The host then inspected the new PDF and recorded narrow R1 numerical/R2 schematic-format passes in a separate source-bound review, preserving R3 full engineering acceptance as pending. This is a reusable execution chain, not proof of automatic raw-brief interpretation, complete installation design or whole-project conformity. Positive native execution and negative missing-tool/failed-target/changed-artifact tests are separate evidence.

The evaluated Graphviz 13.1.2 executable is from the already checksum-verified official FreeCAD 1.1.4 portable distribution, SHA256 `ff1ce5f13caf4ed7dddb7327b94781e751e4a7e693b4655287b6647d959c879a`. Its documented `dot -c` plugin registration was executed inside the ignored repository-local portable directory after `-Tjson` initially reported no formats; no security policy was changed. Executable/plugin/config hashes are retained in drawing inputs. This working standalone CLI does not change the earlier blocked FreeCAD Part geometry result. Graphviz's [official license](https://graphviz.org/license/) is EPL-2.0; its external binaries are not redistributed here, and no upstream implementation is copied. A full bundled-library license audit is not claimed.

## Scope and checks

Graphviz lays out logical bus/line connectivity and labels. Its actual JSON output is checked for bus/edge identity, original endpoints and exact intended labels, then converted to editable LINE/TEXT entities through ezdxf. Cubic edges are flattened with the existing Bezier utility at 0.01 mm paper tolerance. IDs currently require at most 40 printable ASCII characters. An overlarge layout fails instead of dropping nodes or compressing labels silently; pagination, bigger sheets and arbitrary-layout visual acceptance remain pending.

The output contains:

- `schematic.dxf`: phase A/B/C bus volts and line amps rounded to two decimals, plus source-declared route lengths, scope notes and a 50 mm paper reference.
- `loads.csv`: complete per-load, per-phase electrical kW/reactive kvar and source IDs.
- `lines.csv`: complete per-line, per-phase current, source route length and declared current target/source IDs.
- `drawing.json`: exact input/artifact hashes, counts, identity checks and optional native/plot evidence.

Schematic positions and paper units are explicitly unrelated to real installation coordinates or route geometry. Drawing millimetres are paper layout; labelled route metres come from the project, not diagram line measurements. The 100 A example target is not verified cable ampacity. No breakers, protective devices, cable specifications or physical neutral are invented. These are calculation schematics, not full installation single-line diagrams.

With AutoCAD supplied, only a generated copy is writable. A full-path guard precedes SAVEAS; the saved DWG is independently reopened/exported. Native comparison retains geometry, layers, text attributes, actual alignment anchors and electrical XDATA/counts. Baseline centre/right TEXT has a derived group-10 insertion point that AutoCAD recomputes; its actual group-11 anchor is compared instead. Shifted anchors and altered heights remain rejected. The existing PDF checker measures the known reference at fixed 1:1 paper layout, separately from visual review.

On 2026-11-10, the three-bus synthetic fixture reached native DWG reopen, A4 landscape PDF and inspected page rendering. All three voltage boxes and both line labels were readable, uncut and linked to the expected source/results; the paper reference was separately measured. The parser reported duplicate `/PageMode` catalog keys in AutoCAD's PDF; the warning is retained and no general PDF conformance claim is made. Earlier unsuccessful layout/native checks remain in local run directories. Four targeted tests pass, including changed/failed study rejection, swapped layout endpoints and text-anchor controls. This does not establish the complete engineering, Hong Kong, protection or CAD/BIM assignment requirements.
