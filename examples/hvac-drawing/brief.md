# Synthetic HVAC model, analysis and native equipment plan

Author hvac-equipment/bim.json with stable thermal-space and generic PTAC equipment identities. Preserve source geometry/rating assumptions and all source bytes.

Run actual annual PTAC baseline/variant analysis using hvac-equipment/project.json, hvac-equipment/binding.json and the attributed Chicago weather. Require saved device/space/system GUID and rating binding and preserve property-only analysis IFC results with false engineering acceptance.

Read that checked analysis IFC and the complete producer artifact inventory. Use hvac-drawing/settings.json to produce a complete selected HVAC equipment table and GUID-linked metre DXF plan from verified rectangular device/space solids. Keep thermal capacities, volume flow, simulated electricity and modeled hourly peaks separately labelled; list omitted IFC elements. Installation/product details remain pending.

Use hvac-drawing/sheet.json and isolated AutoCAD 2027 to save/reopen the equipment DWG, reconcile all geometry/text/layers/GUIDs, and plot the fixed-scale A4 PDF. Verify the physical 0.9 m source edge and inspect the actual rendered PDF separately before claiming any visual acceptance. This synthetic envelope plan is not a complete installation design.
