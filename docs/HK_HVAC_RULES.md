# Hong Kong HVAC load-design conditions

The explicitly selected `hk-hvac-design-2026.11.08` pack implements the human-comfort indoor and corresponding outdoor limits in [EMSD BEC 2024](https://www.emsd.gov.hk/beeo/en/pee/BEC_2024_ENG.pdf), clause 6.4.2 / Table 6.4, printed page 23 / PDF page 29. The table was rendered and visually checked; the official source hash is pinned. Previous electrical and lighting packs are unchanged.

```powershell
.venv/Scripts/python -m bsa.regulations examples/regulations-hk-hvac/project.json --pack regulations/hk/hvac-design-2026.11.08/pack.json --sources runs/hk-regulation-sources --out runs/new-hvac-design-check
```

`load_design_conditions` requires sourced season, application, indoor dry-bulb temperature and relative humidity, outdoor dry-bulb temperature, plus outdoor wet-bulb temperature for summer. Exact units are `degC` and `percent`. The named applications are office, classroom, hotel and explicitly classified other human-comfort applications. Boolean scope and edition decisions remain required. No operating thermostat, annual weather series or inferred climate default substitutes for missing load-design inputs.

The pack holds the seasonal indoor minima/maxima and outdoor limits. Summer outdoor comparison retains the table's two alternatives: the combined dry-bulb/wet-bulb maximum corner is not accepted. Inconsistent wet-bulb above dry-bulb, invalid humidity, wrong units or missing evidence remain pending. Selected-limit violations are retained as review_required; process applications are outside the implemented indoor path. The output lists each comparison and preserves complete compliance as not_established.

This is a design-basis check, not a heating/cooling load simulation or proof of the recognized method required by 6.4.1. [Explicit sizing humidity](SIZING_HUMIDITY.md) authors and audits sizing RH schedules and sensible/latent mode. The [saved IDF adapter](HVAC_IDF_RULES.md) now binds supported static sizing controls and design-day inputs directly to this pack, including winter minimum temperature and conservative RH-band checks. Arbitrary model controls and automatic workflow-to-executed-model correspondence remain pending. Do not claim engine conformity from checking a separate JSON file. Equipment efficiency, fan/pump limits, duct leakage, insulation, controls and full HVAC conformity remain pending. Evidence is retained in `docs/evidence/hk-hvac-design` and `docs/evidence/hvac-idf-rules`.
