# Inherited VAV connection schedule

`bsa.vav_schedule` turns the existing verified native HVAC connections into an
editable A4 table, calculation CSV and a source-bound JSON record. It adds group
minimum flows, outlet IDs and minimum/maximum straight planar connection lengths
beside the inherited maximum flows. It does not change the supply layout or
select hardware.

```powershell
python -m bsa.vav_schedule run PLAN WORKFLOW native-sheet --supply-layer BSA_SUPPLY --vav-layer BSA_VAV --terminal-layer BSA_DIFFUSER --flex-layer BSA_FLEX --out NEW_DIRECTORY --autocad HOST_ACCORECONSOLE
python -m bsa.vav_schedule verify NEW_DIRECTORY
```

Select external project data through host `BSA_PROJECT_ROOT`. Output must be fresh
and outside the immutable workflow. The native→sheet→schedule→allocation ancestry
must pass existing verification. Saved native symbols, group membership and all
straight flex endpoints are reconstructed through `air_terminal_drawing`.
Minimum flows are summed from the exact inherited terminal allocation, rather
than assuming a turndown or equipment rating. Duplicate/uncovered terminals,
nonfinite/nonpositive flows or lengths and inconsistent group flows reject.

The current single-sheet layout supports 1–20 groups and bounded ASCII labels;
long labels or additional groups require a different layout rather than silent
clipping. Without the explicit AutoCAD argument it produces a DXF/CSV study only.
With it, the existing isolated native adapter saves DWG, independently reopens it,
compares generated entities and measures the 100 mm PDF reference at 1:1. This is
paper table scale, not independent building geometry scale. Actual visual review
remains separate.

Verification reconstructs source connections, rows, aggregates and deterministic
table entities, compares saved and native-reopened DXFs and checks saved artifact,
source and own-generator hashes. This is local correspondence evidence, not
authenticated provenance or comprehensive third-party dependency certification.
The native receipt retains actual executable and print-reference evidence.

Actual project execution retains 20 groups and 80 terminals. Independent Decimal
arithmetic checks group and total maximum/minimum flows, the inherited 40% factor,
all 80 native flex endpoint distances and 140 native table cells by position.
The DWG retains 185 generated entities. A4 reference measures 100.034 mm against
100 mm, within the declared 0.2 mm tolerance. The actual plot is inspected: all
rows, units and limitations are readable without clipping or overlapping cells.
Twelve targeted tests pass with an independently verified receipt. See
[aggregate evidence](evidence/vav-connection-schedule.json).

Lengths are straight XY centre-to-centre lower bounds, not installed flexible
duct lengths. Elevation, bend/slack allowance, equipment/ports, detailed room load,
ADPI, source scale and applicable regulations remain unresolved. No original
requirement, input gap, execution gate or review acceptance was changed. Full
engineering acceptance remains unestablished.

Reuse: existing ezdxf 1.4.5 (MIT), `air_terminal_drawing`, `duct_sheet_native`,
`cad_intake`, `cad_sheet` and the installed AutoCAD 2027 runtime. No new upstream
dependency, numerical solver or transport engine is added. Private source data,
raw execution records and detailed review remain in the coursework workspace.
