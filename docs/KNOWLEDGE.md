# Source-backed local knowledge retrieval

## Database scope

The database is implemented: each selected source bundle has a local SQLite
`index.sqlite` with FTS5 search, source metadata and original locators. It needs
no separate database server. It is a knowledge index, not a warehouse of old
development logs or a replacement for typed engineering JSON, DWG/IFC and reports.

The verified local acceptance corpus has4indexes,15records and160KiB total:
course8, code2, manufacturer1 and project-input4records. These are selected
source snapshots, not a comprehensive professional standards/equipment library.
Private source text/databases are not shipped in Git; a new project builds its
own explicitly selected corpus using the commands below. Historical development
notes are not automatically ingested. Publication version, applicability and
source review remain separate from database availability.

[Knowledge input ownership](KNOWLEDGE_OWNERSHIP.md) now records exact task
source sets in verified workflows/checkpoints and localizes supported knowledge
changes. Legacy/unknown tasks keep conservative fallback; cache eligibility
and manual engineering review are unchanged.

The new real recorded-lighting source-power adapter also executes this path;
see [lighting audit](LIGHTING_SOURCE_AUDIT.md) for188entities,4owned inputs,
actual typed10W change/report propagation and bounded project-knowledge proof.
Lighting has no result-cache eligibility or new photometric/geometry acceptance.
Earlier counts and domains below describe their historical checkpoints.

This first slice indexes explicitly selected existing documents, immutable Git
references and verified common-data input catalogues. It reuses document
extraction, reference_library, workspace guards and provider verification. No
new solver, vector service or third-party retrieval framework is introduced.
The existing root CLI loads the index engine only when dispatched.

```powershell
bsa knowledge build PATH_TO_MANIFEST --out runs/fresh-knowledge
bsa knowledge verify runs/fresh-knowledge
bsa knowledge query runs/fresh-knowledge --text ADPI --role course_source
```

The manifest has schema `bsa.knowledge-manifest/1`, `project_context` (null or a
logical hashed context reference), and 1–40 `sources`. Every source declares
id, kind, role, source, title, publisher, edition, url, discipline, jurisdiction
and conditions. Unknown publication fields must be null. Source file references
use the existing `{workspace,path,sha256}` convention. Optional `pages` selects
1–50 physical PDF pages explicitly; it does not assert whole-document coverage.
Supported kinds are document, git_reference and project_inputs. The latter
requires verified bundle2 inputs and matching project/scenario identity.

Source roles keep primary publications, course material, methods, internal
guides, rule-pack snapshots, examples and project facts separate. Git examples
and rule snapshots cannot be promoted to primary normative publications.
Project facts are excluded by default. To query them, explicitly supply both
`--include-project-facts` and `--expected-context CONTEXT_FILE`; the UUID and
scenario must match. Declared/given/assumed source labels are retained, not
authenticated by indexing.

Each hit carries source hash, declared edition/publisher/URL, applicability
conditions, extraction issues, and an original locator. PDF locators mean
physical PDF pages; text spans refer to extracted text, not printed coordinates.
Unresolved metadata and applicability stay explicit. Lexical score is not
engineering confidence. Search matches passage text; metadata remains attached and available through
explicit role/discipline/jurisdiction filters. Source-wide titles or conditions
do not turn unrelated pages into citations. English uses literal FTS5 terms; CJK uses literal substring
matching, without translation, semantic retrieval or character conversion.

The saved bundle contains request.json, index.sqlite and receipt.json. Verification
reconstructs every record and locator from original sources, checks the fixed
database schema, source metadata and FTS content/integrity. Source, method or
SQLite/Python runtime drift requires rebuilding a fresh index. Editing receipt
hashes cannot make altered text pass reconstruction. This is correspondence
checking, not authenticated publication provenance or statutory acceptance.

Bounds include 100 MiB per source file, 8 million extracted characters per source,
10,000 total records, 32 MiB database, a 2 MiB SQLite cache, bounded operations,
20 returned hits and a 1 MB response. Oversized responses fail instead of silently
discarding citations. Documents still require their existing extraction profile;
scanned/ambiguous pages retain review gaps. No implicit OCR is added.

## Workflow and existing MCP routes

```json
{ "id": "library", "kind": "knowledge_index", "manifest": "manifest.json" }
{ "id": "lookup", "kind": "knowledge_query", "depends_on": "library",
  "query": { "text": "ADPI", "role": "course_source", "limit": 5 } }
```

These are task objects inside the existing complete source-bound plan, not a
standalone plan. Use existing bsa_execute_workflow, bsa_diagnose_workflow,
bsa_artifact_index, bsa_read_artifact and bsa_delivery_template. The tool catalogue
stays at40. The index and query outputs are ordinary auditable artifacts.
For a saved verified index, replace depends_on with an explicit plan-local
index_receipt path to receipt.json. This avoids rebuilding; verification still
checks sources and methods. An inherited query cannot override the manifest or
substitute a different index. A scoped corpus must match plan project_context;
project facts still require explicit opt-in.

Workflow input pins include selected sources/context, methods and nested verified
project-input provider evidence. Saved queries are regenerated and compared,
ignoring only observed SQL elapsed time. Rewriting outer artifact hashes cannot
hide dropped hits or invented citations. Failed index evidence remains visible,
dependent lookup stays pending and independent branches can still execute.
A zero-hit lookup passes execution only; applicability/design review remains
pending. New manifests currently refer to existing input catalogues; they do not
address not-yet-created same-run numerical outputs.

## Executed local evidence (first CLI slice, historical)

`runs/knowledge-milestone/index-current` indexes four existing sources: the course
air-distribution PDF, selected physical page116 from the pinned EMSD wiring2025
cache, page1 of an existing manufacturer fan document and 167 verified project
inputs. The wiring cache hash matches the existing rule pack; this does not
establish its present applicability. Manufacturer metadata remains unknown where
not established. All source review gaps remain visible.

There are 246 records in 434176 bytes. Actual queries found course ADPI passages,
normative voltage passages and the manufacturer identifier; project facts were
absent by default and returned only with the correct explicit context. Five
observed total query times were 0.406–0.694 seconds on this host, including deep
verification. They are observations, not a performance guarantee. SQLite SQL-only
timing and build timing must not be presented as whole-query latency.

Twelve knowledge controls pass in both the existing environment and a clean
documents/modules/spatial profile without Fluids, IfcOpenShell or Manifold.
They cover locators, English/CJK, publication gaps, source drift, coherently
rehashed record/metadata/FTS tampering, schema edits, role promotion, project
isolation, response bounds and root CLI. Cross-platform CI is configured;
configured checks are not executed evidence until their jobs complete.

## Executed workflow evidence

The same actual four-source corpus now runs through the real MCP SDK in
runs/knowledge-workflow-milestone/executed-body-text. Five saved queries retrieve
course ADPI (physical pages4/5), wiring (physical116), manufacturer (physical1)
and an explicitly opted-in project parameter; default reference lookup returns
no project facts. Every ADPI hit contains the term in its own passage. The
manufacturer publisher/edition are transcribed from the actual selected cover;
its download URL remains unknown. All extraction/applicability gaps remain.

Source-only indexing keeps246records in360448bytes, compared with434176bytes in
the historical metadata-plus-text index (storage reduction, not a RAM claim).
The old index/queries remain historical evidence and fail current method pins;
receipts are never patched. The real SDK executes the workflow and reads its results through40listed tools.
A final old-review-file guard required a fresh template name;8successful
recovery/audit tool calls and one catalogue call reused the saved workflow
without recalculation, with final review pending. No new server operation or
computer use is needed. Full deep workflow audits repeat source reconstruction;
this is slower than a raw FTS lookup and still needs profiling before performance
acceptance. The earlier0.406–0.694second CLI observations do not describe whole
MCP workflow latency.

Current knowledge13 + workflow8 + realMCP1 controls pass. A minimal documents/
modules/spatial profile passes the first21 without Fluids/IFC/Manifold. The durable
compatibility group runs105cases:104pass,1existing offline-OCR fixture skip,
zero failures/errors; all_tests_pass=false remains explicit. Receipt independently
verified. Prior CLI commit df48b26 passed all9core-profile CI jobs, including
knowledge on Windows/Ubuntu; it is not CI evidence for the later workflow implementation.
See evidence/knowledge-workflow.json for source-bound aggregate evidence.

Modification impact/safe reuse and a different real-project acceptance remain
open. No coursework, native DWG acceptance, formal release or user acceptance
is changed by this milestone.
