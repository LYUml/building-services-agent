# Native interface material and bounded clearance study

`bsa.interface_contacts` audits actual matching material end faces and separately
studies outside-interface distances on the source-bound compound network.

```
python -m bsa.interface_contacts run NETWORK_RUN RAW_CLASH_JSON STUDY_POLICY --out FRESH_RUN
python -m bsa.interface_contacts verify FRESH_RUN
```

Use explicit host BSA_PROJECT_ROOT for external projects. Output is fresh and
outside sources. This does not edit the model, original raw clash result or
original no-waiver policy. CLI exit 2 retains incomplete engineering acceptance.

## Physical identity and corrected historical counts

Pairs are identified by sorted native IFC body GUIDs. Display names can repeat
across different tees and transitions. Earlier safe summaries incorrectly
deduplicated some clearance records by display names. The corrected counts are:

| Study | Raw clearance records | Unique physical GUID pairs | Earlier name-based count |
|---|---:|---:|---:|
| Source tee network | 93 | 93 | 66 |
| Source cross network | 99 | 99 | 70 |
| Compound network | 101 | 101 | 72 |

Only summary counts change. Raw files/hashes, native geometry, source policy,
failed status and all failures are unchanged. Duplicate names must never merge
distinct physical pairs or serve as model identity.

## Native cap recovery and reuse

The adapter reuses pinned IfcOpenShell native meshes/owned port frames, the
existing clash engine and its conservative `contact_clearance.prove` routine.
The actual gap is independently deriving the material cap from native faces and
binding a numerical joint-region study to the verified source network. No new
geometry engine or dependency is introduced.

Actual coplanar cap triangles are grouped by native connectivity. The unique
component centred on a port is selected; this handles separated takeoffs that
share a plane. Boundary edges must form exactly two centred rectangular loops,
and triangle area must equal independent outer-minus-inner rectangle area.
Connected SOURCE/SINK ports need coincident opposing planes and matching inner/
outer material corners and area. A filled face, displaced port, changed hole or
ambiguous cap rejects. No cap dimensions come from duplicated display names.

## Explicit numerical study, not joint acceptance

Study policy has exact source, classification, radius_factor, radial_allowance_m
and sphere_segments fields. Classification is assumed. Radius is the actual
outer-cap half-diagonal times the explicit factor plus the explicit allowance.
Those values are numerical mask choices, not product-joint dimensions, a code
clearance or a manufacturing recommendation.

The source producer independently replays its complete ancestry first. The raw
result is freshly recomputed with the exact original no-contact policy; recorded
GUID inventories must agree. All raw violations remain in raw-replay.json.
The separately derived policy uses only actual native SOURCE-to-SINK links and
the existing outside_regions mode. Its conservative sphere masks are shrunk by
mesh deflection; both clipped-outside-to-other-full-body gap bounds must pass.

The report distinguishes nonvacuous passes, not-proven results and passes where
at least one entire outside-body part is empty. Empty outside parts remain
pending; the study does not turn them into a complete interface clearance claim.
The full contact-study.json retains existing engine findings/proofs. Numerical
study results do not replace the original raw failed result or establish product
joints, installation clearances, insulation, architecture/equipment coverage,
pressure, physical fabrication or complete regulatory/design acceptance.

The verifier freshly rebuilds source inputs, native cap matching, derived policy,
raw findings and both-direction outside-region proofs. Source code, numerical
policy files and saved artifacts are pinned. A count or recorded pass flag alone
cannot replace that replay; empty/outside-gap changes are included in proof
identity. Design acceptance remains false on successful integrity replay.

## Executed source study

The real 102-body/101-link compound network has 101 raw clearance records and
101 unique physical GUID pairs. All correspond to actual linked native
interfaces; no unlinked raw clearance pair was found at the original numerical
threshold. All 101 native material cap pairs match.

With the separately declared factor 1.1, 0.0001 m radial allowance and 64-segment
conservative sphere study, all 101 both-direction outside-region proofs pass.
Every outside-body part is nonempty: zero vacuous results and zero not-proven
results. The source minimum clearance is the existing 20 micrometre numerical
diagnostic, not an installation clearance. No new manufacturer/code allowance
is inferred. The original raw no-waiver result remains failed and unchanged.

Fifteen tests pass across native cap extraction (including separated caps in the
same plane), changed material/port/proof/vacuity controls, original conservative
outside-region checks and original clash coverage controls. Source-bound replay
and its saved artifacts remain distinct from full engineering acceptance. See
[safe aggregate evidence](evidence/interface-contacts.json).

The actual standalone verify CLI independently recomputes the original source
ancestry, native caps, raw findings and bounded-region proofs. Integrity passes
with all 101 nonvacuous results, zero not-proven/vacuous results, and design
acceptance still false. This is numerical evidence under the recorded study
assumptions, not authenticated certification or final project acceptance.
