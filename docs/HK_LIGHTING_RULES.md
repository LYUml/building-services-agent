# Hong Kong office lighting power density

The separately pinned `hk-lighting-2026.11.08` pack adds office LPD to the existing jurisdiction framework without changing the previous electrical pack or its evidence. Select this pack explicitly for the lighting task; the generic `regulations` workflow adapter and `requires_pass` gates can execute it.

```powershell
.venv/Scripts/python scripts/fetch_regulation_sources.py regulations/hk/lighting-2026.11.08/pack.json --out runs/new-bec-sources
.venv/Scripts/python -m bsa.regulations examples/regulations-hk-lighting/project.json --pack regulations/hk/lighting-2026.11.08/pack.json --sources runs/new-bec-sources --out runs/new-office-lpd
```

Source: [EMSD BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/BEC_2024_ENG.pdf), Section 2, clauses 5.1 and 5.4, Table 5.4. Office table PDF page 22 / printed page 16 was visually checked. The numeric rule data uses enclosed office area at or below 15 m2, office area above 15 through 200 m2, and above 200 m2. Their respective limits are 9, 8.5 and 7.2 W/m2. The 70 W low-power exception is scoped only to clause 5.4.1; it never establishes complete lighting compliance. A small non-enclosed office is not assigned an invented table row.

The project supplies a sourced positive internal floor area and unique luminaire IDs with full-output circuit watts including applicable lamp controlgear, driver and transformer losses. The adapter sums those watts, divides by area and selects the pack's area band. Prefilled LPD or demand/dimming factors cannot override this computation. Explicit assertions establish office function, fixed-lighting inventory completeness, included-lighting scope, space boundaries and edition/prescriptive-route applicability. These assertions are not independently verified building facts. This first implementation supports all-in-scope single-function offices; it does not implement exclusions, multifunction spaces or trade-offs.

At or below the low-power threshold the selected path is `not_applicable`, not whole-project pass. Missing sources/classification stay pending, and exceeded limits require review of design or the applicable alternative compliance route. Automatic/daylight controls, control-point counts, photometry and the broader BEC/BEEO requirements remain pending. Official source files are hash-pinned, cached locally and not redistributed. Source inspection, actual execution and regression evidence are in `docs/evidence/hk-lighting-lpd`.
