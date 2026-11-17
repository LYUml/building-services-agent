# Actual-project revision propagation

Executed against agent commit `f16be239503f7d9ddbae1e578eead5476efc5253`.
This is an isolated acceptance scenario using historical actual-project inputs,
not a new coursework submission or adoption of an alternative design.
All 19 original project files matched their historical source hashes before
copying, and remained unchanged after execution. Current methods were pinned in
a fresh configuration rather than silently updating a historical receipt.

The only numerical input change was the straight-friction design target:
1.23 to 0.8 Pa/m on the existing finite dimension grid. The tighter target is a
declared study assumption, not a new regulation. Original geometry, identities,
load, flows, terminal data and unresolved engineering requirements were retained.

The existing HVAC project executor completed its seven package stages without
stage errors. Independent package inspection passed. Of 47 sections, 44 selected
different dimensions; maximum friction changed from 1.226100 to 0.798572 Pa/m.
Every section retained its flow and passed its selected numerical limits.
The drawing updated all 47 rows/235 bound text cells. AutoCAD saved and reopened
the native DWG, with correspondence for 718 generated entities. A 100 mm plotted
reference measured 99.9913 mm. The actual A1 overview was rendered and viewed;
the plan and revised schedule were present without gross clipping.

The report contains 47 revised duct rows and an unchanged 20-group VAV table.
The 23-page PDF passed complete numeric-row extraction correspondence for 388
rows. Actual report page 17 was rendered and viewed: revised sizes, velocity
and friction are readable and within page bounds. Other pages were not visually
re-reviewed in this scenario. The VAV table describes group flows; this does not
prove manufacturer equipment selection. The single-line drawing displays nominal
sizes in the schedule and does not become a fabrication geometry model.

Status remains `review_required`: no ADPI, full-pressure, installation, complete
regulatory or user acceptance is inferred. Raw private inputs and generated
project files stay in ignored runs. The public
[aggregate evidence](evidence/real-project-revision.json) records hashes and
measured results without distributing coursework source archives.
