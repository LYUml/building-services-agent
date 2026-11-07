# Native IFC-diagram delivery evidence

Actual five-task execution of `examples/water-riser/native-plan.json` from the staged-file snapshot in `runs/ifc-native-index/runs/native-delivery`, using the user's licensed local AutoCAD 2027 Core Console. It did not attach to a GUI session or use completed coursework files. Source/task-artifact integrity verification passed before archiving this selected evidence.

`segments.dwg` is the actual saved native diagram. `reopened.dxf` came from a separate AutoCAD process opening an isolated copy of that DWG. `native-verification.json` records matching supported geometry/render attributes, eight model entities, six GUID-linked entities, all model entity handles and IFC XDATA, and metre units. Conversion/reopen/plot logs are retained. The source and saved DWG bytes remained unchanged during inspection and plotting.

`sheet.pdf` is the actual A4 landscape 1:50 plot. Independent vector/page-transform parsing measured the supplied 2.5 m reference at approximately 49.9957 mm, against 50 mm expected and a 0.2 mm tolerance. `sheet-preview.png` is its real Poppler rendering, inspected for readable separated labels/legend, visible linework and unclipped content. `visual-review.json` binds those observations to PDF/image hashes. The adapter's original visual status stays pending; this separate review does not alter recorded workflow artifacts.

The PDF parser emitted a duplicate `/PageMode` dictionary-key warning during some actual runs; regression logs retain it. The evidence establishes the listed geometry/scale and rendered-page checks, not comprehensive PDF structural certification.

`workflow.json` references original ignored run paths and hashes. This selection is not a complete portable run archive. Reproduce with the source example plan and a licensed engine. Equipment/fittings/insulation, installation details, complete sheet standards, model-viewer review and professional engineering acceptance remain pending; design_accepted stays false.
