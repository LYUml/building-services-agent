# Coordinated synthetic office example

Use project.json as the single source of electrical device IDs, XY centres, input kW, power factors and circuit assignments. Use geometry.json only for the explicit synthetic space, device classes, dimensions and elevations. Generate calculations, a DXF overlay and IFC4 envelopes. Reopen the artifacts and reconcile their device/circuit identities, coordinates and electrical values; do not maintain separate copies of those electrical fields in the geometry data.

Convert the generated DXF overlay to native DWG in AutoCAD 2027, reopen it and verify the device geometry and labels. Plot a padded schematic PDF. The example requires no fixed-scale architectural sheet and no existing building drawing is modified.

Inspect the plotted PDF and preserve unresolved engineering acceptance. These synthetic scenarios do not establish real photometry, fault protection, manufacturer geometry, routing or code compliance.
