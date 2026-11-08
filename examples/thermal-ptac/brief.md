# Synthetic actual PTAC annual analysis

Author thermal-ifc/bim.json as editable IFC with stable identities and preserve synthetic scope and all source bytes.

Bind saved spaces using thermal-ifc/binding.json and thermal-ptac/project.json, including explicit opaque layers, weekly internal gains/outdoor air and one fixed-size DX PTAC per zone with sourced capacities, flow, COP/SHR, electric heat efficiency, fan/motor inputs and five explicit performance curves. Run both lighting cases through the complete 2025 calendar with actual EnergyPlus. Reconcile thermal delivery and PTAC electricity separately; check component electricity sums, exact hourly identities, monthly/annual totals and the declared finite-capacity unmet-time target. No real product/curve applicability, routed HVAC/duct geometry, plant or engineering acceptance is claimed.
