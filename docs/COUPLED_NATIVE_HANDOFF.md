# Native drawing delivery from the shared-model handoff

The existing coupled source handoff now optionally consumes a separate native
drawing supplement. It preserves all seven original paragraphs and the two new
paragraphs, adding a dependency-gated `ifc_native` task after the same-model pipe
drawing. The final manual review depends on that native task as well.

```
python scripts/run_coupled_handoff_demo.py --out runs/NEW_PROJECT --native --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
```

The executable is explicit host configuration, not a path selected by a brief.
Without it, the native task stays pending. A failed pump identity blocks the
coupled model, downstream drawing and native output even when an executable was
supplied. The existing isolated Core Console adapter saves generated copies,
independently reopens the DWG, reconciles every entity/IFC XDATA value and plots
the original fixed-scale window. No user GUI document is attached or closed.

No CAD engine or new external package is added. Reuse is through existing
`ifc_native`, `native_cad`, `cad_intake`, `cad_overlay` and `cad_sheet`. These method
files now enter validation/source pins for the native task. The actually used
AutoCAD executable is pinned lazily after prerequisite checks, and checked again
after execution. Runtime replacement invalidates verification; blocked upstream
tasks do not attempt to hash or launch an unavailable executable.

## Executed evidence

[Evidence](evidence/coupled-native-handoff.json) records three actual full source
handoffs: native positive, no-runtime, and wrong-identity with an explicit runtime.
The positive preserves nine source requirements (eleven bound rows) and passes
eight scoped engineering tasks; final review remains pending. AutoCAD reopens
the saved DWG with eight model entities and six IFC-linked entities unchanged.
The A4 1:50 plot's 2.5 m reference measures 49.9957 mm against a 50 mm target and
declared 0.2 mm tolerance.

The only PDF page was rendered and actually inspected: both RISE-HIGH / RISE-LOW
32 mm bore / 40 mm OD / 2.5 m labels, leader lines, source-unit and non-installation
notes are legible without clipping or text overlap. Scoped review of the native
supplement is recorded separately through the existing delivery review adapter.
Three corresponding bound review rows pass; the overall assessment remains
`needs_review`, with full engineering acceptance false. Generated workflow and
handoff receipts are left unchanged; rendered evidence/review records live outside
the immutable run directory.

Thirty-eight tests pass, with one optional standalone AutoCAD unit test skipped
because its opt-in environment flag was absent. Actual AutoCAD execution is proven
by the separate positive full workflow, not by that skipped test or by the mocked
runtime-pin test. The suite covers source supplement preservation, missing runtime,
failed upstream blocking, executable replacement, native method pins and prior
cross-discipline/unit checks. A Windows short-path assertion was corrected to use
the same resolved path as production. IfcOpenShell reports its existing unclosed
schema-file warning and an ignored cleanup KeyError; the completed suite passes.

## Remaining scope

This is a synthetic, two-segment projected pipe schematic. It omits pump/electrical
equipment detail and does not deliver electrical IFC port topology, installed
fittings, insulation, access, motor protection or complete Hong Kong checks. DWG
reopen and visual plot evidence apply only to this actual sheet. They do not clear
all source obligations or establish a completed building-services assignment.

The AutoCAD PDF uses vector-stroke text and has no extracted searchable text.
The parser also reports duplicate PageMode metadata; the actual rendered page was
checked. The editable native DWG retains its TEXT entities. The native adapter's
automatic result still records visual review pending; the separate actual host
inspection supplies the scoped visual evidence without rewriting old statuses.
