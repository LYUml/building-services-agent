# Source-backed AutoCAD schedule writing

The optional `bsa.autocad_schedule` host CLI reuses the MIT U-C4N/Autocad-MCP
EzdxfBackend at exact clean commit 6f6a538255ca9f885232e845ac32f10b4433fe3e.
Setup and dependencies are the same as [source intake](AUTOCAD_SOURCE_PROVIDER.md).
The fixed worker uses ezdxf 1.4.5, pydantic 2.14.3 and numpy 2.5.4, with
CAD_LAUNCH=never. It does not start the upstream MCP server or attach live COM.
Original license: third_party/licenses/uc4n-autocad-mcp-6f6a5382.txt.

## Execution

Set host BSA_PROJECT_ROOT explicitly to the selected coursework workspace.
Run from the editable agent checkout; source/project/binding paths must stay in
that workspace. The output directory must be fresh. Documents cannot choose roots.

```powershell
python -m bsa.autocad_schedule run --source ABS/source.dxf --project ABS/ducts.json --binding ABS/binding.json --allocation-project ABS/allocation.json --original-plan ABS/plan.json --native-settings ABS/native.json --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe" --out ABS/fresh-run
python -m bsa.autocad_schedule verify ABS/fresh-run
```

Native settings and executable are optional as a pair. Without them the result
has no native DWG acceptance. The source DXF must already contain bound table TEXT
and source-backed topology; this is not arbitrary drawing layout synthesis.

The adapter recalculates source allocation and duct sizing. Existing duct_sheet
produces a separately validated reference; the upstream backend independently
edits the bound TEXT cells and creates flow-arrow LINEs. Independent replay checks
numeric values, original entities, block definitions and paper-space entities.
The verifier binds producer lineage, actual method/runtime hashes and artifacts;
rehashing forged counts/cells does not substitute for source replay.
Existing native adapters check isolated active-document paths, save DWG, reopen,
compare generated layers and plot a reference-scaled PDF. Visual review is separate.

## Executed real task

BSE3227 replay covered 47 sections, 235 bound cells (70 changed values), and
94 lines representing 47 flow arrows. Native reopening reconciled 718 generated
entities across nine layers. All 33 original requirements and six unresolved
inputs remain. Final A1 PDF, enlarged table and notes were actually inspected:
47 rows readable, no observed table clipping or overlap. The PDF page content
matches the existing public drawing; public DWG/PDF bytes are preserved.
See [aggregate evidence](evidence/autocad-schedule-provider.json).

Fifteen related tests actually pass without skips, including failed design limits,
source/output confinement, rehashed forged cells/counts and fake allocation lineage.
This optional comparison establishes scoped upstream writer equivalence, without
claiming a speed benefit or replacing every existing drawing provider. It retains
the existing writer as a validation reference. Physical building scale, ADPI,
actual VAV dimensions, AHU interfaces and full engineering/Hong Kong acceptance
remain unresolved. No new numerical design targets or equipment facts were invented.
