# Terminal product geometry source review

A direct manufacturer source review precedes any new product geometry adapter.
Krueger's official 2012 dimensional PDF was downloaded and page B1-4 rendered
and visually checked. Its hash, table locator, source classifications and
separate published inch/mm representations are recorded in
`evidence/krueger-terminal-dimensions.json`. Originals stay in ignored local
runs; no open-source licence or right to redistribute manufacturer assets is
assumed. This is source research and transcription, not native product authoring.

For the nominal 08 row in the 24-inch/600mm panel table, A is published as
7 7/8 inches (200mm). Exact conversion is 0.200025m; the published rounded
metric value is preserved separately. The nominal 8-inch designation converts
to 0.2032m. Neither quantity establishes hydraulic clear bore or sheet gauge.
B also differs by material/model group and is not a total-height substitute.
Do not silently replace assumed stub bore with A or treat 600mm as 24 inches.
The exact material, frame, accessories and metric/imperial product remain to
be selected against applicable product submittals.

The official Revit index offers a manufacturer model archive, but expressly
limits the models to generalized building design/layout. It directs accurate
dimensions/performance to product documentation. Availability and local bytes
are not verified native model geometry, ports or installation dimensions.
Existing Revit native access remains subject to the documented host policy;
this investigation neither changes loaders nor attempts a policy workaround.

The general retained-payload review now emits
`assumed_bore_requires_product_evidence` for each native stub whose inherited
bore classification is assumed or design_choice. It preserves the source and
value, asks for applicable actual clear-bore/joint evidence and changes no
calculation, model or acceptance. No vendor-specific dimension is hard-coded
into this diagnostic. Other flow-development/whole-network requests remain.

Official sources:
- [Dimensional PDF](https://www.krueger-hvac.com/file/3116/1400_51400_M1400_M51400_DimensionalData.pdf)
- [Revit index and model limitations](https://www.krueger-hvac.com/public/software/revit)

The prior synthetic study deliberately used nominal size as an explicit bore
assumption. The new review exposes that limitation; it is not a newly measured
error in the BSE3227 coursework. Six interface-clearance failures remain.

Executed verification: 24 related tests pass. A fresh source-bound diagnosis of
the saved native study retains six assumed-bore requests, fourteen engineering
requests in total, numerical completion and the original coordination failure.
The official archive is now complete:171001369bytes,245members, all ZIP CRC
checks pass. The selected final RFA matches the earlier candidate hash. Native
model fidelity remains unverified. The actual size differs from the index
download label; use retained byte evidence.

Normal Revit2027.3 startup was attempted for UI-only inspection. It stopped at
the existing BSA add-in unsigned-publisher security prompt. No prompt action,
family open, model change or new native geometry check occurred; no loader or
security-policy modification was attempted.
