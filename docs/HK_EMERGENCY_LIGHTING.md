# Hong Kong emergency lighting: source review

Reviewed 2026-11-09. This is a research and implementation contract, not an executable rule pack or design approval. Existing ordinary-lighting Radiance and office LPD results do not establish emergency-lighting performance.

## Official sources and edition decisions

Source bytes and review locations are recorded in `sources/regulations/hk-emergency-lighting-research.json`. Original PDFs remain in the ignored local research directory. Review the [FSD code index](https://www.hkfsd.gov.hk/eng/fire_protection/notices/code.html) and [circular index](https://www.hkfsd.gov.hk/eng/fire_protection/notices/circular.html) for the actual project; this review is not an exhaustive amendment audit.

- FSD Circular 4/2021 adopts BS 5266-1:2016 and BS EN 1838:2013 with local modifications. PDF page 2 makes this applicable to initial building-plan submissions received by FSD on or after 2022-01-01. Unmodified parts of the standards still apply; their complete texts have not been reviewed here.
- Circular 5/2021 concerns licensed/registered premises and separate central-supply and self-contained requirements. PDF page 2 specifies applications received by the respective licensing authority or FSD from 2022-06-01. Do not substitute the building-plan date for this application date.
- The September 2022 FSI CoP is a separate edition decision. Neither date above proves that edition applies to a given project, existing building or improvement works.
- Circular 4/2024's corrigendum was text-reviewed across all seven PDF pages. No section 5.9 amendment is listed. Its cover also requires reading Circulars 5/2022, 1/2023 and 3/2023; those dependencies and later withdrawal/amendment notices remain to be reviewed.

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
