Synthetic spatial IFC water-ring adaptation. All equipment envelopes, profile dimensions, node idealizations, demand values and pump curves are declared test assumptions; actual products, junction geometry, clashes and domain acceptance remain unresolved.

Author model.json as editable IFC with explicit hollow pipe profiles and bidirectional water ports, preserving stable object/port GUIDs and verifying schema, native geometry and both connection directions.

Use project.json and binding.json with that saved IFC. Derive pipe lengths, bore diameters and node elevations from saved profiles/ports, require exact selected-system device/connection coverage, preserve source bytes and reverse flow, and execute EPANET with continuity, pipe-energy, boundary, pressure/delivery and pump checks. Retain the geometry-GUID trace and per-piece result schedule; keep product/fitting, K applicability, physical coordination, visual and full engineering gates pending.
