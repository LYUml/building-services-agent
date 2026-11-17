# Source-backed local knowledge retrieval

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
engineering confidence. Search includes declared title/conditions as well as
passage text. English uses literal FTS5 terms; CJK uses literal substring
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

## Executed local evidence

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

This slice is CLI-only. Knowledge workflow/MCP integration, modification impact,
safe reuse and a different real-project acceptance remain open. Existing MCP
common-data capabilities are unchanged. No coursework, native DWG acceptance,
formal release or user acceptance is changed by this milestone.
