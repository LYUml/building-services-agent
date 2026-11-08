# Modular jurisdiction rules

The target agent must select applicable local requirements before design and carry them through calculations, authoring and delivery. Engineering solvers remain jurisdiction-neutral. Versioned data packs supply rule scope, official source, edition, clause/page, applicability conditions, units and supported check methods. A different jurisdiction is a different explicitly selected pack; changing region must not silently change numeric assumptions in an existing project.

The initial Hong Kong pack is `regulations/hk/2026.11.08/pack.json`. This is an initial partial implementation, not a complete Hong Kong compliance product. The full goal includes electrical, HVAC/energy, lighting, plumbing, drainage, fire services and applicable contract/utility requirements. Track missing rules instead of treating an empty or narrow check set as complete compliance.

## Reproduce the initial check

```powershell
.venv/Scripts/python scripts/fetch_regulation_sources.py regulations/hk/2026.11.08/pack.json --out runs/hk-regulation-sources
.venv/Scripts/python -m bsa.regulations examples/regulations-hk/project.json --pack regulations/hk/2026.11.08/pack.json --sources runs/hk-regulation-sources --out runs/new-hk-check
```

Downloads verify the recorded SHA256; changed official bytes are rejected for review rather than silently becoming a new edition. Full official PDFs remain in ignored local cache. The pack records URLs, edition and locator metadata; it does not redistribute the manuals or claim they are open-source software. Current source inventory was inspected on 8 November 2026. Recheck official publications and amendments when starting an actual project; the date label is a source snapshot, not guaranteed perpetual applicability.

Projects explicitly pin jurisdiction, pack ID, selected editions and the basis for each edition decision. A sourced fact includes its value and project evidence reference; quantities require the exact unit. Missing applicability or metric evidence is pending. Mismatched jurisdictions/packs and unsupported rule methods are rejected. Evidence references and edition decisions remain assertions for review; the initial engine does not authenticate their underlying engineering documents automatically.

The first executable rule is EMSD Wiring CoP 2025, **13A(3)(v), printed page 115 / PDF page 116**. The official PDF was downloaded, hash-pinned, text-inspected and rendered for visual confirmation. This rule supports the 4% deemed-to-satisfy path for normal-service voltage drop from the installation origin to fixed current-using equipment. A branch-only calculation cannot stand in for that total path. Above 4% triggers `review_required` for applicable standards/safe-function or relevant exception assessment; it is not automatically labelled statutory noncompliance. Starting-transient conditions are outside this implemented path.

Results separate `supported_checks_pass`, `regulatory_compliance: not_established` and `design_accepted: false`. A successful command only means this supported check passed. It never establishes all electrical checks or whole-building compliance. Existing electrical/network/thermal examples remain synthetic and are not retroactively certified by installing this pack.

## Workflow adapter

For computed full-path electrical metrics, see [electrical path binding](ELECTRICAL_PATHS.md). It supplies per-circuit total feeder/branch drops and report hashes while retaining explicit applicability assertions. Generated numeric inputs do not establish full building topology or complete regulatory conformity.

Register a task such as `{"id":"hk-rules","kind":"regulations","project":"project.json","pack":"pack.json","sources":"official-sources"}` in a source-linked workflow plan. Paths are relative to and contained within the plan directory. Download required official files before workflow execution; missing files fail workflow preflight. Standalone evaluation can instead record missing files as pending. Only sources referenced by executable rules require cached files; index-only catalog entries do not.

Both standalone and workflow reports track the actual official source bytes alongside pack/project inputs. A later source change invalidates workflow integrity; a source that differs from the pack hash leaves the check pending. Unsupported paths, missing evidence and alternative-path reviews cannot pass the task. A passing task concerns only its supported checks: requirement acceptance remains pending and whole-project regulatory compliance is not established. The generic adapter does not bind facts to upstream calculation outputs; use electrical_regulations for fresh supported electrical path calculations. Explicit requires_pass prerequisites can gate authoring tasks (see WORKFLOWS.md), but required gates and regulatory coverage are not inferred automatically. Actual official-file workflow evidence is in `docs/evidence/hk-regulation-workflow`.

## Hong Kong source coverage and applicability

| Source | Snapshot and current implementation |
|---|---|
| [EMSD electrical CoP](https://www.emsd.gov.hk/en/electricity_safety/publications/codes_of_practice/index.html) | 2025 edition PDF pinned; one clause implemented. Index provides a 2020-edition transition route for installations completed and connected by 31 December 2026; project decision required. |
| [EMSD BEC/EAC](https://www.emsd.gov.hk/beeo/en/mibec_beeo_codtechguidelines.html) | 2024 codes and EAC Addendum 1/2025 identified. Building categories, submission/works/audit dates, circulars and numerical clauses remain to be encoded. |
| [WSD plumbing](https://www.wsd.gov.hk/en/plumbing-engineering/requirements-for-plumbing-installation/technical-requirements-for-plumbing-works-in-bldgs/index.html) | Latest listing is April 2026. Technical requirements, figures, amendments and application conditions require clause-level implementation. |
| [FSD installations](https://www.hkfsd.gov.hk/eng/fire_protection/notices/code.html) | September 2022 current listing, with separate existing-building bases shown. Premises classification and relevant circulars must be reviewed; no automated fire compliance yet. |
| [BD drainage guidance](https://www.bd.gov.hk/en/resources/codes-and-references/epidemic-prevention-information/index-drainage-systems.html) | Guidance entry identified; governing legislation and technical clause extraction pending. |
| [ArchSD general specification](https://www.archsd.gov.hk/en/publications-publicity/general-specification-for-building-services.html) | 2022 edition with corrigenda listed through GSBS05-2022. This is a government-project specification; apply the actual contract edition, not a blanket statutory rule for every Hong Kong building. |

Next integration requires source-linked statutory scope decisions, clause-level rules across those disciplines, explicit applicable amendments, project-data adapters and dependency gates that retain pending compliance checks. Do not copy BS/IEC tables from memory or conflate utility requirements, statutory rules, project specifications and course assumptions.
