"""Bounded SQLite FTS5 index with source reconstruction, not an authority oracle."""
import json
from pathlib import Path
import re
import sqlite3
import _sqlite3
import sys
import time
from contextlib import contextmanager

from ..module_contract import read_json
from ..source_refs import file_hash, reference, resolve_reference
from ..workspace import ROOT, intake_output
from .manifest import load, ROLES
from .sources import canonical, records, search_text, project_context

MAX_DB = 32*1024*1024
MAX_RESPONSE_BYTES = 1_000_000
DDL = (
    'CREATE TABLE sources (id TEXT PRIMARY KEY,role TEXT,discipline TEXT,jurisdiction TEXT,metadata TEXT NOT NULL)',
    'CREATE TABLE records (id TEXT UNIQUE NOT NULL,source_id TEXT NOT NULL,locator TEXT NOT NULL,body TEXT NOT NULL,project_id TEXT,scenario_id TEXT)',
    "CREATE VIRTUAL TABLE search USING fts5(body,tokenize='unicode61')",
)


def runtime():
    return dict(sqlite=sqlite3.sqlite_version, python=sys.version,
                binary_sha256=file_hash(_sqlite3.__file__))


def methods():
    files = [*Path(__file__).parent.glob('*.py'),
             *[ROOT/'src/bsa'/n for n in ('source_refs.py','workspace.py','module_contract.py',
                                        'documents.py','reference_library.py','engineering_data/context.py')]]
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(files)}


@contextmanager
def connect(path=None, *, writable=False):
    target = ':memory:' if path is None else str(path) if writable else Path(path).resolve().as_uri()+'?mode=ro'
    db = sqlite3.connect(target, uri=path is not None and not writable)
    try:
        if hasattr(db, 'enable_load_extension'):
            db.enable_load_extension(False)
        db.execute('PRAGMA trusted_schema=OFF')
        db.execute('PRAGMA cache_size=-2048')
        if writable:
            db.execute('PRAGMA page_size=4096')
            db.execute('PRAGMA max_page_count=8192')
        ticks = [0]
        def progress():
            ticks[0] += 1
            return int(ticks[0] > 100000)
        db.set_progress_handler(progress, 1000)
        yield db
        if writable:
            db.commit()
    finally:
        db.close()


def schema(db):
    return db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name").fetchall()


def initialize(db):
    for statement in DDL:
        db.execute(statement)


def row_tuple(row):
    return (row['id'], row['source_id'], canonical(row['locator']), row['text'], row['project_id'], row['scenario_id'])


def build(manifest_path, out):
    manifest_path, out = Path(manifest_path).resolve(), Path(out).resolve()
    if not intake_output(out) or out.exists() or out in manifest_path.parents:
        raise ValueError('Fresh index directory in selected project/tool runs required')
    source_ref = reference(manifest_path)
    manifest = load(manifest_path)
    pins, engine = methods(), runtime()
    out.mkdir(parents=True)
    request = dict(schema='bsa.knowledge-build/1', manifest=source_ref, methods=pins,
                   runtime=engine, design_accepted=False)
    (out/'request.json').write_text(json.dumps(request, indent=2)+'\n', encoding='utf-8')
    started = time.perf_counter()
    summaries, count = {}, 0
    try:
        with connect(out/'index.sqlite', writable=True) as db:
            initialize(db)
            for row in records(manifest, summaries):
                count += 1
                db.execute('INSERT INTO records VALUES (?,?,?,?,?,?)', row_tuple(row))
                db.execute('INSERT INTO search(rowid,body) VALUES (?,?)', (count, search_text(row)))
                if count % 100 == 0 and (out/'index.sqlite').stat().st_size > MAX_DB:
                    raise ValueError('Knowledge index size limit exceeded')
            if not count:
                raise ValueError('No extractable knowledge records; missing sources are not successful knowledge')
            for key, meta in summaries.items():
                db.execute('INSERT INTO sources VALUES (?,?,?,?,?)', (key, meta['role'], meta['discipline'].casefold(),
                            meta['jurisdiction'].casefold(), canonical(meta)))
    except sqlite3.Error as exc:
        raise ValueError('SQLite knowledge build failed: '+str(exc)) from exc
    if (out/'index.sqlite').stat().st_size > MAX_DB:
        raise ValueError('Knowledge index size limit exceeded')
    if methods() != pins or runtime() != engine or file_hash(manifest_path) != source_ref['sha256']:
        raise ValueError('Knowledge build inputs or runtime changed')
    receipt = dict(schema='bsa.knowledge-index/1', manifest=source_ref, methods=pins, runtime=engine,
                   records=count, sources=len(summaries), database_sha256=file_hash(out/'index.sqlite'),
                   request_sha256=file_hash(out/'request.json'), build_seconds=time.perf_counter()-started,
                   design_accepted=False)
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    verify(out)
    return receipt


def verify(out):
    out = Path(out).resolve()
    if not intake_output(out) or {p.name for p in out.iterdir()} != {'index.sqlite','request.json','receipt.json'} or any(p.is_symlink() or not p.is_file() for p in out.iterdir()):
        raise ValueError('Exact regular-file knowledge bundle required')
    r = read_json(out/'receipt.json')
    keys = {'schema','manifest','methods','runtime','records','sources','database_sha256','request_sha256','build_seconds','design_accepted'}
    if set(r) != keys or r['schema'] != 'bsa.knowledge-index/1' or r['design_accepted'] is not False:
        raise ValueError('Versioned unaccepted knowledge receipt required')
    if r['methods'] != methods() or r['runtime'] != runtime() or (out/'index.sqlite').stat().st_size > MAX_DB or file_hash(out/'index.sqlite') != r['database_sha256'] or file_hash(out/'request.json') != r['request_sha256']:
        raise ValueError('Knowledge artifacts, methods or runtime changed; rebuild rather than rehash')
    request = read_json(out/'request.json')
    if request != dict(schema='bsa.knowledge-build/1', manifest=r['manifest'], methods=r['methods'], runtime=r['runtime'], design_accepted=False):
        raise ValueError('Knowledge build identity differs')
    manifest = load(resolve_reference(r['manifest']))
    summaries, count = {}, 0
    try:
        with connect(out/'index.sqlite') as db, connect() as expected_schema:
            initialize(expected_schema)
            if schema(db) != schema(expected_schema):
                raise ValueError('Knowledge database schema differs from fixed implementation')
            stored = iter(db.execute('SELECT id,source_id,locator,body,project_id,scenario_id FROM records ORDER BY rowid'))
            fts = iter(db.execute('SELECT rowid,body FROM search ORDER BY rowid'))
            for row in records(manifest, summaries):
                count += 1
                if next(stored, None) != row_tuple(row) or next(fts, None) != (count, search_text(row)):
                    raise ValueError('Indexed text/citation differs from original source reconstruction')
            if next(stored, None) is not None or next(fts, None) is not None:
                raise ValueError('Knowledge index contains unaccounted records')
            expected = sorted((key, m['role'], m['discipline'].casefold(), m['jurisdiction'].casefold(), canonical(m)) for key, m in summaries.items())
            if db.execute('SELECT * FROM sources ORDER BY id').fetchall() != expected or count != r['records'] or len(summaries) != r['sources']:
                raise ValueError('Knowledge source metadata/coverage differs')
            # Verify the FTS posting index without mutating the saved file.
            with connect() as audit:
                db.backup(audit)
                audit.execute("INSERT INTO search(search,rank) VALUES('integrity-check',1)")
    except sqlite3.Error as exc:
        raise ValueError('Knowledge database verification failed: '+str(exc)) from exc
    return dict(integrity_pass=True, records=count, sources=len(summaries),
                source_review_states={k: m['extraction_review']['coverage_status'] for k,m in summaries.items()},
                scope='Reconstructed declared corpus only; metadata/source applicability are not authenticated or accepted', design_accepted=False)


def query(out, text, *, role=None, discipline=None, jurisdiction=None, limit=5,
          include_project_facts=False, expected_context=None):
    if not isinstance(text, str) or not text.strip() or len(text)>256 or type(limit) is not int or not 1<=limit<=20 or type(include_project_facts) is not bool:
        raise ValueError('Bounded literal query/limit and explicit project-fact selection required')
    if role is not None and role not in ROLES:
        raise ValueError('Known source role required')
    for value in (discipline, jurisdiction):
        if value is not None and (not isinstance(value, str) or not value.strip() or len(value)>300):
            raise ValueError('Bounded explicit metadata filter required')
    out = Path(out).resolve()
    index_ref = reference(out/'receipt.json')
    checked = verify(out)
    r = read_json(out/'receipt.json')
    manifest = load(resolve_reference(r['manifest']))
    context = project_context(manifest)
    if include_project_facts or role=='project_input':
        from ..engineering_data.context import load as load_context
        if not include_project_facts or expected_context is None or context is None:
            raise ValueError('Project facts require opt-in and expected project/scenario context')
        expected = load_context(expected_context)
        if any(expected[k] != context[k] for k in ('project_id','scenario_id')):
            raise ValueError('Project fact context differs from current project/scenario')
    terms = re.findall(r'\w+', text, flags=re.UNICODE)
    if not terms or len(terms)>20:
        raise ValueError('One to twenty literal search terms required')
    unicode_mode = bool(re.search('[\u3400-\u9fff]', text))
    clauses, args = [], []
    if not include_project_facts:
        clauses.append("s.role<>'project_input'")
    for field, value in (('role',role),('discipline',discipline),('jurisdiction',jurisdiction)):
        if value is not None:
            clauses.append('s.'+field+'=?')
            args.append(value.casefold())
    if unicode_mode:
        clauses += ['instr(lower(search.body),lower(?))>0' for _ in terms]
        args += terms
        rank = '0'
    else:
        clauses.append('search MATCH ?')
        args.append(' AND '.join('"'+term.replace('"','""')+'"' for term in terms))
        rank = 'bm25(search)'
    sql = ('SELECT r.id,r.source_id,r.locator,r.body,r.project_id,r.scenario_id,s.metadata,'+rank+
           ' AS score FROM records r JOIN sources s ON s.id=r.source_id JOIN search ON search.rowid=r.rowid WHERE '+
           ' AND '.join(clauses)+' ORDER BY score,r.id LIMIT ?')
    started = time.perf_counter()
    with connect(out/'index.sqlite') as db:
        rows = db.execute(sql, [*args,limit]).fetchall()
    hits = [dict(id=x[0], source_id=x[1], locator=json.loads(x[2]), text=x[3], project_id=x[4], scenario_id=x[5],
                 metadata=json.loads(x[6]), lexical_score=x[7], design_accepted=False) for x in rows]
    if file_hash(out/'index.sqlite') != r['database_sha256'] or file_hash(out/'receipt.json') != index_ref['sha256']:
        raise ValueError('Knowledge index changed during lookup')
    response = dict(query=text, index=index_ref, manifest=r['manifest'], hits=hits, retrieval='literal Unicode substring' if unicode_mode else 'SQLite FTS5 literal terms',
                matching_is_not_applicability=True, includes_project_facts=include_project_facts,
                validation=checked, sql_seconds=time.perf_counter()-started,
                limits='No semantic translation, source authentication, completeness or engineering applicability inferred from a lexical hit', design_accepted=False)
    if len(canonical(response).encode('utf-8')) > MAX_RESPONSE_BYTES:
        raise ValueError('Knowledge result exceeds bounded size; reduce query limit or select narrower sources')
    return response
