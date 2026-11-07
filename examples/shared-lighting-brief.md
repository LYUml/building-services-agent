# Shared electrical BIM and photometric example

Use office-electrical/project.json and office-electrical/geometry.json as the shared electrical and spatial sources. Bind exactly their light fixtures in the selected Office space to shared-lighting.json. Derive optical world positions from electrical XY centres, explicit envelope bottom Z and explicit photometric offsets, then transform to the selected room local frame. Check IES nominal power metadata against the electrical input using the supplied tolerance; do not derive brightness from watts. Generate and reconcile calculations, DXF and IFC, then run the prescribed Radiance illuminance and parameter-stability checks.

Convert the generated shared DXF to native DWG in AutoCAD 2027, reopen it and verify device geometry/labels, then plot a padded schematic PDF. Existing drawings are not modified by this synthetic example.

Review physical photometric origins, model/plot appearance and the full acceptance matrix. Source photometry, reflectances, offsets and targets are synthetic assumptions; these outputs do not certify actual manufacturer geometry, obstruction, glare, daylight, fault protection or code compliance.
