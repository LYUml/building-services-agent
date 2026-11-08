Synthetic spatial IFC water-ring adaptation. All equipment envelopes, profile dimensions, node idealizations, demand values and pump curves are declared test assumptions; actual products, junction geometry, clashes and domain acceptance remain unresolved.

Author model.json as editable IFC with explicit hollow pipe profiles and bidirectional water ports, preserving stable object/port GUIDs and verifying schema, native geometry and both connection directions.

Use project.json and binding.json with that saved IFC. Derive pipe lengths, bore diameters and node elevations from saved profiles/ports, require exact selected-system device/connection coverage, preserve source bytes and reverse flow, and execute EPANET with continuity, pipe-energy, boundary, pressure/delivery and pump checks. Retain the geometry-GUID trace and per-piece result schedule; keep product/fitting, K applicability, physical coordination, visual and full engineering gates pending.

Generate plan, front and side pipe views from the saved water-model IFC using views-settings.json. Preserve every pipe GUID and its true/profile dimensions in the schedule; explicitly symbolize end-on pipes and require every pipe to have a nonzero axis in at least one view. Keep projection length distinct from true length and preserve model/source bytes.

Save and reopen each view as native DWG using isolated AutoCAD 2027, reconcile complete geometry/entity/GUID identity, plot the supplied A4 windows at 1:50 and verify each declared 5 m reference measures 100 mm within 0.2 mm. Retain three individual sheets and a merged three-page PDF; actual visual review, finite fittings, equipment, hidden lines and full installation/engineering acceptance remain separate gates.
