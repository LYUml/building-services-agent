# Source-base electrical overlay and explicit-scale plot

The `base_overlay` workflow extends drawing intake into authoring. It uses the same electrical device IDs/circuits/XY as the calculation tools and a reviewed, hash-bound source selection. Original files are never saved. DXF sources are copied; DWG sources go through isolated AutoCAD export before a new coordinated drawing is authored.

```powershell
python -m bsa.workflow execute examples/base-overlay/portable-plan.json --out runs/base-layout
python -m pip install -e ".[documents]"
python -m bsa.workflow execute examples/base-overlay/plan.json --out runs/base-native --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe'
python -m bsa.workflow verify runs/base-native
```

The workflow task takes `project`, `drawing`, `selection`, `settings` and optional `sheet` paths. Native DWG input or a requested sheet requires an explicit AutoCAD executable; missing it leaves the task pending. The direct CLI is `python -m bsa.cad_overlay <project> --drawing <source> --selection <selection.json> --settings <settings.json> --out <new-run>`, with optional `--autocad` and `--sheet`.

Settings supply a sourced XY translation in metres, rotation in degrees and positive symbol/text dimensions and label offset in metres. The rigid transform maps common project XY into source WCS; the proven INSUNITS factor then converts metres into drawing units. Source geometry is not rescaled. Labels rotate with the stated transform. Existing BSA_DEVICES/BSA_LABELS layers are rejected rather than overwritten.

The preservation snapshot covers LINE, LWPOLYLINE, CIRCLE, ARC, TEXT, MTEXT, INSERT and POINT in layouts and block contents, keyed by original handles. It compares defined geometry attributes, entity colour/linetype/lineweight/visibility, layer state and INSUNITS. Named/anonymous block contents are checked; xrefs and unsupported entity types block this adapter. Snapshot comparison after DXF save/reload protects existing entities. Native mode saves a new DWG, independently opens a copy in another AutoCAD process, exports it and compares original plus new overlay records. This validates the recorded attributes, not every possible DXF/DWG object, font/style table, proxy or custom property. Arbitrary-file fidelity remains unproven.

The optional sheet contract currently supports one A4 landscape WCS top-view model window, an explicit scale denominator and a nonzero planar LINE reference. Plot scale is computed from drawing units; an oversized window is rejected instead of silently using Fit. All CAD writes/settings are guarded by the isolated document's full path. Plot settings are discarded on exit and the DWG hash must remain unchanged.

Independent pypdf inspection reads the PDF's physical page dimensions and stroked vector paths with graphics-matrix stacking, excluding nonpainted clipping paths. It requires the reference line at its expected centred-window position and physical length within an explicit tolerance of at most 1 mm. A six-metre reference at 1:50 must measure 120 mm. Raster-only or differently encoded references may fail rather than receive unverified scale approval. PDF paths do not prove that all desired content fits or that text is legible: render and inspect the exact resulting page separately.

The synthetic example was iterated after actual rendering exposed base-text/annotation collisions. Revised synthetic placement and label offset preserve the base while separating text, symbols and boundaries. Both DXF-base and DWG-base runs were saved/reopened, plotted, measured and visually inspected. These are schematic verification fixtures, not commissioned room layouts, full title-block sheets, automatic collision avoidance or electrical design acceptance. Physical placement, circuit protection, equipment detail, full sheet standards and engineering review remain pending.

Code uses the existing attributed ezdxf and pypdf dependencies plus the local licensed AutoCAD installation. No new upstream source is copied.
