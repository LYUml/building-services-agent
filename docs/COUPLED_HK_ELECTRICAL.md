# Hong Kong electrical gate in the shared-model handoff

The authored water/pump/electrical handoff now optionally checks the unchanged
electrical baseline against the existing Hong Kong whole-path voltage-drop pack
before coupled IFC revision and drawing release. The optional native extension
inherits the same gate; a supplied AutoCAD executable cannot clear a pending rule.

```
python scripts/run_coupled_handoff_demo.py --out runs/NEW_PROJECT --hk-sources OFFICIAL_CACHE
python scripts/run_coupled_handoff_demo.py --out runs/NEW_NATIVE --hk-sources OFFICIAL_CACHE --native --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
```

Use `--hk-control long-feeder` or `--hk-control unknown-scope` in a fresh project
to retain explicit negative scenarios. Originals are archived separately. The
host cache must contain the exact pinned official source before intake. Source
paths and executable paths remain host configuration, never document commands.

## Source and applicability

The existing pack encodes only the normal-service Code 13A(3)(v) selected
deemed-to-satisfy voltage-drop path (4 percent), not complete electrical approval.
The [official EMSD PDF](https://www.emsd.gov.hk/filemanager/en/content_443/COP_E_2025.pdf)
was freshly retrieved, matched the existing SHA256
`d69ae0c53972cc583de64b8e83ca7428460419b7f06ffa2f4f3db79e7b165c3b`,
and its PDF page 116 / printed page 115 inspected in extracted source text.
No threshold or clause was invented or changed.

The [official index](https://www.emsd.gov.hk/en/electricity_safety/publications/codes_of_practice/index.html)
states publication on 31 December 2025 and the separate 2020-edition grace path
for installations completed and connected by 31 December 2026. This synthetic
trial explicitly selects the 2025 path. Actual works dates, equipment standards
and statutory applicability are not established by the current calendar date.
The per-project edition decision and normal-service/fixed-equipment/full-path
assertions remain source-backed declarations, not independently authenticated
site facts. Missing assertions remain pending.

## Independent phase radials

The baseline has L1 pump and L2 lighting circuits. Their phase labels and hardware
are retained. A new explicit topology method, `independent_single_phase_radials`,
partitions the original project by phase and calls the unchanged existing
`single_phase_scalar_radial` calculator for each group. It adds no solver or
external dependency. Every original circuit/device is included once; each feeder
aggregates only its declared same-phase downstream current.

The strict topology declares a common installation origin, explicit dedicated
per-radial returns and one exact-coverage radial per original phase. Shared
non-origin nodes/feeder IDs, mixed-phase attachments, missing groups, changed
origins and recursive groups reject. The old default still rejects mixed phases.
Coefficients already include each full single-phase return convention; no extra
factor of two or feeder diversity is applied.

This is not a shared-neutral, phasor or three-phase load-flow model. Actual
dedicated-return applicability, route lengths and coefficient validity remain
engineering evidence requirements. The 20 m / 4 mV/A/m feeder choices are explicit
synthetic assumptions, not measurements or manufacturer tables.

## Baseline and release correspondence

The existing electrical regulation adapter freshly recalculates complete feeder
plus branch drop from the original 0.75 kW baseline, then supplies that metric to
the selected pack. Basis-supplied numeric totals do not override calculation.
The lower pump operating estimate cannot replace the baseline project beneath
the gate: `regulatory_source_bindings` now explicitly binds the pump/electrical
consumer's original project bytes, preserving inherited hydraulic roles too.
Changed project bytes reject before execution. New source/method pins cover the
electrical path, regulation and branch engines.

[Executed evidence](evidence/coupled-hk-electrical.json) retains the actual native
positive, long-feeder and unknown-scope runs. All eleven original source passages
and fourteen bound requirement rows survive. The positive baseline yields
approximately 0.493717 percent pump and 0.030548 percent lighting whole-path drop.
The selected rule passes, followed by coupled IFC checks, native DWG save/reopen,
GUID/entity reconciliation and actual one-page visual review. The 2.5 m reference
again measures approximately 49.996 mm at 1:50.

The 1000 m L1 feeder control keeps original branch checks passing but exceeds the
selected deemed-to-satisfy path; it is `review_required`, not an assertion of
statutory noncompliance. Removing the fixed-equipment applicability fact stays
pending even with low computed drops. Both retain `hk-rules=pending` and create no
coupled IFC, drawing or native output. Forty-eight related tests pass, including
phase grouping, existing common rule providers, original branch checks, source
replacement, original handoff and pump/IFC unit regressions.

Only the selected voltage-drop path is checked. Full Hong Kong compliance remains
`not_established`; real topology/returns, feeder protection/ampacity, motor starting,
earthing, WSD plumbing, equipment, physical installation and other disciplines
remain pending. The drawing is still a two-segment pipe schematic without the
remaining electrical system. The authored interpretation is not arbitrary-brief
semantic understanding. Existing upstream attribution and licenses are unchanged.
