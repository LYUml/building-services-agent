# Hong Kong emergency lighting: source review

Reviewed 2026-11-09. This is a research and implementation contract, not an executable rule pack or design approval. Existing ordinary-lighting Radiance and office LPD results do not establish emergency-lighting performance.

## Official sources and edition decisions

Source bytes and review locations are recorded in `sources/regulations/hk-emergency-lighting-research.json`. Original PDFs remain in the ignored local research directory. Review the [FSD code index](https://www.hkfsd.gov.hk/eng/fire_protection/notices/code.html) and [circular index](https://www.hkfsd.gov.hk/eng/fire_protection/notices/circular.html) for the actual project; this review is not an exhaustive amendment audit.

- FSD Circular 4/2021 adopts BS 5266-1:2016 and BS EN 1838:2013 with local modifications. PDF page 2 makes this applicable to initial building-plan submissions received by FSD on or after 2022-01-01. Unmodified parts of the standards still apply; their complete texts have not been reviewed here.
- Circular 5/2021 concerns licensed/registered premises and separate central-supply and self-contained requirements. PDF page 2 specifies applications received by the respective licensing authority or FSD from 2022-06-01. Do not substitute the building-plan date for this application date.
- Circular 2/2022 PDF page 1 puts the September 2022 CoP into general use from 2022-09-01. Its building-plan rule covers new submissions for new buildings and specified existing-building works: at least half the volume rebuilt, alterations necessitating reconstruction of at least half the main-wall superficial area, or a new occupation permit. Voluntary adoption is also allowed. Neither lighting-standard date above establishes this separate edition decision.
- Circular 4/2024's corrigendum was text-reviewed across all seven PDF pages. No section 5.9 amendment is listed. Its cited Circulars 5/2022, 1/2023 and 3/2023 have now been text-reviewed, including appendices; see the dependency register below. This is not a complete review of all later FSD instruments.

### Reviewed dependency register

| Circular | Reviewed scope and consequence |
|---|---|
| 5/2022 | Calibration requirements and specified inspection-code amendments; immediately effective. Its instrument table must not be generalized into an invented lux-meter calibration requirement. |
| 1/2023 | Car-port sprinkler requirement and building-plan transition from 2023-04-01; no replacement accommodation lighting threshold identified. |
| 3/2023 | Battery-room/charging-facility gas extraction, replacing paragraph 8 of Part XI of Circular 4/96; initial building plans from 2023-09-01, with voluntary earlier adoption. Relevant to central battery arrangements when its scope applies; not a blanket ventilation rule for every luminaire. |
| 1/2025 | Obsolete-letter register; the reviewed English table does not list 4/2021 or 5/2021 as withdrawn. |
| 6/2025 | Confirms emergency-lighting Circular 1/2006 was superseded by 5/2021, and calibration Circular 1/2016 by 5/2022. Neither 4/2021 nor 5/2021 is listed as withdrawn in this register. |
| 3/2025 | Adds water-based fixed installation requirements for battery rooms/charging facilities, including a lithium-ion capacity condition at fire-compartment level. Building-plan transition starts 2025-08-01 for the stated new/existing-building categories. Treat central-battery fire protection as an independent applicability question. |

The 3/2025 appendix is text-reviewed; its non-extractable page 2 was rendered and visually reviewed. It encourages voluntary compliance and retains formal approval procedures for additions/alterations in existing buildings. Absence from two obsolete-letter tables does not establish that no other amendment exists. Machine-readable dates and relations are research findings, not an automatic project edition selector.

## Candidate checks and essential limits

The 2022 CoP section 5.9 (printed page 58, PDF page 66) and May 2021 technical guidance's modification to BS 5266-1 clause 5.2.6 (printed page 7, PDF page 8) support these accommodation checks, subject to sourced applicability:

| Candidate | Boundary | Required evidence |
|---|---|---|
| Floor horizontal illuminance | At least 2 lx | Emergency-mode photometry and a justified assessment of the floor throughout rated duration |
| Emergency luminaire count | Gross area strictly greater than 8 m² requires at least two | Sourced gross area, space identity and distinct emergency luminaires |

Exactly 8 m² does not trigger the second check; it does not remove emergency-lighting obligations. Do not use average illuminance or a workplane result as floor minimum. A finite sensor grid alone does not prove the continuous floor minimum.

The same guidance's modification to clause 5.2.2 requires the minimum to hold through rated duration, accounting for voltage reduction, wiring drop, battery/lamp ageing and dirt. Normal-mode IES output or an invented universal derating factor is insufficient. Reflection treatment and the complete assessment method still require review of the applicable base standards.

The guidance (printed page 19, PDF page 20) marks BS EN 1838 clauses 4.2.1–4.2.7, 4.3.1–4.3.9 and 4.4.1–4.4.7 as not locally applied. Do not import generic UK escape-route/open-area lux defaults.

Licensed-premises appendices, supply arrangement, rated duration, activation, wiring, exit signs, commissioning and maintenance need separate applicability and checks. Circular 5/2021 PDF page 4 already distinguishes central-supply entertainment-premises duration by occupancy and generator backup; do not assert a universal two-hour rule.

## Implementation sequence

1. Complete the outstanding circular/edition and licensed-premises review; retain explicit unresolved decisions.
2. Add a versioned FSD module with source hashes, per-space applicability, numeric units and separate check statuses. Unknown applicability or duration evidence must remain pending.
3. Bind emergency-mode fixtures, stable space IDs, gross-area evidence and floor sensors to freshly executed photometry. Reuse the existing Radiance engine, with a reviewed method and sourced end-of-duration inputs.
4. Exercise threshold boundaries, failed/pending states, source changes and ordinary-mode substitution. Gate drawing release on the same model/results; retain installation and statutory acceptance separately.

No executable emergency rule or workflow coverage is claimed by this document. Full regulatory compliance remains not established.
