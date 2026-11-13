# Source-connected coordination work list

The radius selector proves a finite known-elbow geometry combination, not full
coordination. Raw clash records can also report the same physical pair through
both native intersection and independent material-overlap checks. The new
`bsa.duct_coordination_diagnosis` groups those records without changing either
engine's failure, the policy or the source model.

```powershell
$env:BSA_PROJECT_ROOT='C:/ABSOLUTE/COURSEWORK'
python -m bsa.duct_coordination_diagnosis SELECTED_RADIUS_RUN RAW_CLASH_JSON --out FRESH_DIAGNOSIS
```

The adapter verifies the selected native IFC and original source ancestry, binds
the exact raw clash IFC/policy hashes, and executes the existing clash engine
again. Its semantic comparison preserves pair/type/overlap/distance and coverage
checks; witness positions come from fresh native analysis rather than being
accepted from the file. Unknown distance/volume fields remain unknown, not zero.
The source/model/policy hashes must remain unchanged throughout. This reuses
existing IfcOpenShell/Manifold native checks, radius verification and source
junction incidents. No new geometry or collision engine is introduced.

Pairs resolve through actual saved IFC GUID/name identity. For each unique pair,
the diagnostic records every engine record type and whether its elements have an
actual IFC port link, share an unresolved source node, share another source node,
or have no common source node. These are associations, not proof of an underlying
engineering cause. Linked interfaces remain failed when the raw policy says so;
no contacts are waived and no tolerances are relaxed.

The output retains all original requirement IDs and creates one pending action
per unresolved source connection with exact source incidents/section sizes/flows.
For unequal-section tees it names the existing rectangular_tee_transitions
composer as a possible building block; source-specific authoring is explicitly
not executed. Multi-branch design remains an unresolved authoring task. Review
[the composer's scope](RECTANGULAR_TEE_TRANSITIONS.md) before choosing explicit
geometry/products/trims. The work list does not supply missing construction data.

## Executed actual model

The selected 47-straight/10-bend model's 76 intersection records represent 38
unique pairs: 38 native piercing records plus 38 independent material-overlap
records. All pairs associate with unfinished source connections: 30 pairs across
15 unequal-section tee nodes, and eight pairs across two multi-branch nodes.
There are no intersection pairs involving the authored bends in this represented
model. This says nothing about architecture/equipment absent from the model.

The 31 unique clearance violations comprise 20 actual linked-interface pairs and
11 pairs at unfinished source nodes. All remain failed under the original policy.
No native geometry is missing/invalid and no solid pair is unverified. A real
raw-record deletion control rejects before creating a diagnosis output. Twelve
related tests pass, covering deduplication, source/native identity, nonadjacent
interference, linked overlap and nullable engine metrics.

Status remains coordination_failed and all 17 actions remain pending. This is a
source-bound repair work list, not a repaired or installation-ready model. The
original IFC, source plan, coursework DWG/PDF and collision policy are unchanged.
See [aggregate evidence](evidence/duct-coordination-diagnosis.json). Reexecute the
diagnostic against a newly verified model after actual source-bound authoring;
do not edit the result to clear a failure.
