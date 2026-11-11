# Hong Kong flexible-duct routing restrictions

Select `regulations/hk/flex-routing-2026.11.11/pack.json` with the existing
`regulations` workflow task or `bsa.regulations` CLI. The separate
flex-length-2026.11.10 module remains available;length and routing restrictions
must be selected and reviewed independently.

The official [FSD Circular2/2023 source](https://www.hkfsd.gov.hk/eng/source/licensing/MECHANICAL_VS_EN_2_2023.pdf)
was fetched again and matched the existing SHA256 pin. PDF page14 / printed
page11 was rendered and inspected. Clause7.3 restricts main-distribution use;
clause7.4 restricts fire-resisting boundary penetrations and direct fire/fire-smoke
damper attachments. These selected prohibitions are separate from length limits.
Project date,works scope,amendments,product testing and full statutory applicability
remain subject to review.

## Individual assertion inventory

`flexible_duct_inventory` contains:

| Field | Contract |
|---|---|
| source | Nonempty evidence reference for the inventory |
| complete | true only for an explicitly complete inventory;false/null cannot establish a clear result |
| connections | Individually identified sourced records;unknown classifications remain null |

Each connection has a unique `id`,nonempty `source`,and these declaration fields:

- `role`: `main_distribution`,`connection`,`final_connection`,or null.
- `penetrations_complete`: true only for a complete crossing inventory.
- `penetrations`: records with unique `id`,evidence `source`,`kind`
  (`wall`,`floor`,`ceiling`,`partition`,or null),and Boolean/null `fire_resisting`.
- `ends`: exactly two records with evidence `source` and `kind`
  (`fire_damper`,`fire_smoke_damper`,`other`,or null).

`other` is an explicit sourced non-damper classification. It is not the default
for an unclassified endpoint. An empty penetration list cannot establish absence
of crossings without `penetrations_complete=true`. A declared complete empty
connection inventory is an assertion of no flexible connections,not discovery
from an absent file. Source strings are reviewer assertions;this adapter does not
authenticate evidence or infer these classifications from a plan line or label.

The method derives per-rule forbidden-connection counts from individual records.
It overrides any caller-supplied aggregate zero. Missing completeness or relevant
classifications retain pending status. A known forbidden condition stays
review_required even when other inventory information is missing;unknown details
remain in the record. Missing official source/edition evidence still prevents
evaluation. The result includes per-connection findings and unresolved conditions.

The pack still returns `regulatory_compliance=not_established` and
`design_accepted=false`. Its binding is `sourced_inventory_assertions_only`.
Neither a count nor a rule pass proves native/installed fire-boundary or product
identity. Intended downstream tasks use explicit `requires_pass` gates. A short
connection or a length-module pass cannot override these restrictions.

## Executed controls

```powershell
.venv/Scripts/python scripts/run_hk_flex_routing_demo.py --pdf runs/source/FSD_Mechanical_Ventilating_Systems_2023.pdf --out runs/new-flex-routing-controls
```

The runner requires the exact official PDF and creates synthetic clear,main-use,
boundary,damper,unknown and known-plus-unknown scenarios. It executes the existing
regulations engine,retains expected pass/review_required/pending states and keeps
whole-design acceptance false. No official PDF or private coursework is committed.

Twenty-four rule/regulation/fan-method regression tests pass. Controls include all
four boundary kinds,both damper classes,unknown/incomplete inventory,aggregate
zero substitution,source/edition mismatch,invalid identities/classes,workflow
release blocking,and additive method pins for mixed packs. The adapter reuses the
generic maximum/count machinery;no additional rule engine or dependency is added.

An actual saved-native design handoff identifies80 intended final-connection
lines. Complete inventory,fire-boundary crossings and actual attachment classes
are unverified. The three checks therefore remain pending;no absence of dampers
or fire boundaries is inferred. See evidence/hk-flex-routing.json. This check
extends agent capability without treating a line drawing as a complete fire
design or changing the coursework's existing review statuses.
