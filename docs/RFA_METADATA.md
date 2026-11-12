# Read-only saved RFA metadata

Reuse [olefile 0.47](https://github.com/decalage2/olefile) to read existing
Compound File Binary storage and the saved PartAtom XML. It runs as a Python
file reader, without loading Revit, its native API or a vendor family into a
project. This does not remedy or bypass the documented native add-in policy
failure. No BIM geometry parser or authoring engine is implemented here.

Install optional `vendor-bim` dependencies (olefile==0.47), then run:

```powershell
.venv/Scripts/python -m bsa.rfa_metadata path/to/source.rfa --out runs/new-metadata
```

Sources/outputs must remain in the repository or an explicit host-selected
workspace. Output must be new and separate. The tool hashes the original RFA,
its own reader and the upstream implementation; it preserves PartAtom.xml and
emits metadata.json. `bsa.rfa_metadata.verify(folder)` rereads the unchanged RFA
and compares all output fields and original stream bytes. Original files are
never saved or upgraded by Revit. Manufacturer assets stay local-only.

Metadata retains family/type titles and each scalar parameter's raw text,
qualified name and attributes, including published type/unit labels. It does
not evaluate formulas, interpret arbitrary parameter names, convert units,
select a project type or infer a connection diameter from a radius parameter.
The bounded XML reader rejects DTD/entities, ambiguous types/parameters and
inconsistent declared type counts. Olefile handles structured-storage parsing.

Native Revit execution, geometry, connectors and parameter semantics all remain
unverified and design_accepted remains false. A family parameter named flow
containing zero is retained as text, not an accepted project load. Other
streams are inventoried by name and size but are not interpreted as geometry.
This CLI is not a registered common modelling provider or a complete native
MEP adapter. See TERMINAL_PRODUCT_GEOMETRY_SOURCES.md for the official product
source review and remaining submittal/connection gaps.

Attribution: Philippe Lagadec's olefile, including inherited PIL authors and
notices. The exact distributed license is retained in
third_party/olefile/LICENSE.txt; no upstream implementation is modified or
vendored. The optional dependency and executed wheel/source hashes pin reuse.

Executed evidence: evidence/rfa-metadata-review.json records the actual
manufacturer candidate read, two retained types, source/wheel/license hashes
and changed-parameter rejection. Twenty related tests pass. The candidate
was first obtained from the received prefix. The completed official archive
has now passed all245member CRC checks; the final selected RFA bytes match
the candidate exactly. Native Revit geometry verification remains pending. Stored
12-inch default connection parameters are not the requested 8-inch design.
