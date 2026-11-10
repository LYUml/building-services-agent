# Hong Kong flexible connection length

Select `regulations/hk/flex-length-2026.11.10/pack.json` explicitly with the
existing `bsa.regulations` engine or `regulations` workflow task. No new engine
or dependency is introduced. The pack pins the FSD Circular 2/2023 official PDF;
the source was fetched again and matched the local reviewed bytes.

Clause 7.2 (PDF page 14, printed page 11) supplies the ordinary 4 m maximum.
The project must assert, with evidence, applicable mechanical-ventilation scope,
complete connection inventory, verified actual installed lengths and selection
of the ordinary limit path. The metric `maximum_complete_connection_length`
uses metres and represents the largest complete connection in that inventory.
Do not substitute straight plan distance or ignore vertical offsets and bends.

The ordinary-limit check does not implement the exceptional prior Director
agreement path. Exceeding 4 m returns review_required, not automatic approval.
Missing installed length remains pending. Product testing, main-duct restrictions,
fire-resisting penetrations, damper connections and full fire/HVAC conformity
remain explicitly outside this pack's implemented coverage. An inapplicable
ordinary path is not an approved exception.

Executed controls with the actual pinned PDF: 4 m passes the selected check,
4.01 m requires review, and missing installed length remains pending. Facts in
these controls are synthetic. The private coursework candidate was also evaluated
and remains pending because its available routes are planar design geometry.
See `docs/evidence/hk-flex-length/controls.json`.

The actual private candidate plan now executes this rule alongside terminal
and duct calculations. Both numerical tasks pass while the rule remains pending.
An isolated copied-plan control removed only the separate delivery-input blocker
and confirmed that `requires_pass` on the pending rule prevents delivery execution.
The actual plan retains all unresolved inputs; the diagnostic control is not
an acceptance record or a waiver.

Official source: https://www.hkfsd.gov.hk/eng/source/licensing/MECHANICAL_VS_EN_2_2023.pdf
