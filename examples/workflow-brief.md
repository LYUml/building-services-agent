# Synthetic building-services integration brief

Use office-electrical/project.json as the explicitly synthetic electrical scenario. Calculate the circuit design current and conditional ampacity/voltage-drop checks, and create an editable device overlay and calculation report.

Convert that overlay to native DWG in AutoCAD 2027, independently reopen it and reconcile the three device circles and labels. Generate a padded schematic PDF; this example does not require a fixed engineering scale.

Use two-zone-energy/project.json for the synthetic thermal scenario. Build two adjacent 20 m2 thermal zones, run the two given design days in EnergyPlus and compare the baseline 12 W/m2 lighting with the 6 W/m2 variant. Keep thermal loads separate from lighting electricity; do not report annual energy.

Review the PDF visually and check the complete requirement-to-artifact matrix. Electrical fault protection, real project code compliance and physical HVAC routing are outside this synthetic integration brief and must not be claimed as verified.
