# Hong Kong office lighting power density

The separately pinned `hk-lighting-2026.11.08` pack adds office LPD to the existing jurisdiction framework without changing the previous electrical pack or its evidence. Select this pack explicitly for the lighting task; the generic `regulations` workflow adapter and `requires_pass` gates can execute it.

```powershell
.venv/Scripts/python scripts/fetch_regulation_sources.py regulations/hk/lighting-2026.11.08/pack.json --out runs/new-bec-sources
.venv/Scripts/python -m bsa.regulations examples/regulations-hk-lighting/project.json --pack regulations/hk/lighting-2026.11.08/pack.json --sources runs/new-bec-sources --out runs/new-office-lpd
```

Source: [EMSD BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/BEC_2024_ENG.pdf), Section 2, clauses 5.1 and 5.4, Table 5.4. Office table PDF page 22 / printed page 16 was visually checked. The numeric rule data uses enclosed office area at or below 15 m2, office area above 15 through 200 m2, and above 200 m2. Their respective limits are 9, 8.5 and 7.2 W/m2. The 70 W low-power exception is scoped only to clause 5.4.1; it never establishes complete lighting compliance. A small non-enclosed office is not assigned an invented table row.

The project supplies a sourced positive internal floor area and unique luminaire IDs with full-output circuit watts including applicable lamp controlgear, driver and transformer losses. The adapter sums those watts, divides by area and selects the pack's area band. Prefilled LPD or demand/dimming factors cannot override this computation. Explicit assertions establish office function, fixed-lighting inventory completeness, included-lighting scope, space boundaries and edition/prescriptive-route applicability. These assertions are not independently verified building facts. This first implementation supports all-in-scope single-function offices; it does not implement exclusions, multifunction spaces or trade-offs.

At or below the low-power threshold the selected path is `not_applicable`, not whole-project pass. Missing sources/classification stay pending, and exceeded limits require review of design or the applicable alternative compliance route. Automatic/daylight controls, control-point counts, photometry and the broader BEC/BEEO requirements remain pending. Official source files are hash-pinned, cached locally and not redistributed. Source inspection, actual execution and regression evidence are in `docs/evidence/hk-lighting-lpd`.

## Shared electrical and geometry binding

`python -m bsa.lighting_regulations <electrical.json> --geometry <geometry.json> --basis <space-bases.json> --pack <lighting-pack.json> --sources <official-cache> --out <new-run>`

The `lighting_regulations` workflow adapter uses those same fields. Space bases map every light-containing shared space ID to its jurisdiction/edition/fact basis, without repeated `lighting_space` quantities. See `examples/regulations-hk-lighting/shared-space-basis.json`. Common geometry must cover every electrical device exactly once. Each `IfcLightFixture` takes its watts from electrical kW × 1000, with no demand-factor reduction; each rectangular space takes area from its shared X/Y dimensions. Separate rooms remain separate checks. Non-light classes are reported explicitly with their source descriptions. Classification and completeness in the actual building remain review assertions, not automatically discovered facts.

Shared geometry validation precedes the calculation; this adapter does not reopen saved IFC. It does not establish that a room envelope equals statutory internal floor area or that a supplied electrical rating includes driver/controlgear losses. Those applicability assertions remain mandatory. Passing LPD cannot clear failed branch calculations. Gates can require this task before `electrical_coordination` using the same project/geometry sources. Actual official-source execution through coordinated DXF/IFC generation is retained in `docs/evidence/shared-lighting-regulations`; native DWG, visual/photometric and full compliance acceptance remain pending.

## Reproducible LPD and photometric workflow

```powershell
.venv/Scripts/python scripts/run_hk_lighting_demo.py --out runs/new-hk-lighting --official runs/hk-regulation-sources/emsd-bec-2024.pdf --radiance-bin tools/radiance-6/bin
```

This synthetic demonstration stages hash-checked source copies in a new repository directory and executes `lighting_regulations` before the existing `electrical_lighting` CAD/IFC/Radiance adapter. The latter uses original IES data rather than deriving brightness from watts. A separate manual review remains pending, so the CLI returns 2 even for the baseline's passing automated checks. Use a different output folder and `--high-target` for the explicit 1000 lx sensor-mean failure control. The altered target is marked as a synthetic assumption; it is not a statutory office lighting target. Existing source files stay unchanged and staging records every original hash and the control change.

Actual baseline and high-target results are retained in `docs/evidence/hk-lighting-radiance`, including native Radiance commands/results, parameter-stability evidence, shared DXF/IFC and dependency diagnosis. The high-target run has passing LPD but failed illuminance, retaining a blocked downstream review. This demonstrates distinct checks; it does not establish measured photometry, actual obstructions, glare/daylight, lighting controls, native DWG or complete acceptance.
