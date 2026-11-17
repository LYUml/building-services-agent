"""Reuse source extractors/reference reads and retain exact locators/review gaps."""
import hashlib
import json
from pathlib import Path

from .. import documents, reference_library
from ..module_contract import read_json
from ..source_refs import file_hash, resolve_reference

MAX_TEXT = 8_000_000
CHUNK = 2000


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest_value(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def project_context(manifest):
    if manifest['project_context'] is None:
        return None
    from ..engineering_data.context import load
    return load(resolve_reference(manifest['project_context']))


def passages(descriptor, context):
    kind, spec = descriptor['kind'], descriptor['source']
    if kind == 'git_reference':
        if not isinstance(spec, dict) or set(spec) != {'revision', 'reference_id', 'sha256'}:
            raise ValueError('Immutable listed Git reference required')
        ref = reference_library.read(spec['revision'], spec['reference_id'])
        if ref['sha256'] != spec['sha256']:
            raise ValueError('Committed reference hash differs')
        required_role = {'example': 'example', 'regulation': 'rule_pack_snapshot',
                         'schema': 'agent_guide', 'docs': 'agent_guide'}[ref['kind']]
        if descriptor['role'] != required_role:
            raise ValueError('Committed guide/example/pack cannot be promoted to a primary publication')
        return documents.text_rows(ref['content_utf8']), dict(coverage_status='committed text', issues=[]), ref['immutable_reference']
    path = resolve_reference(spec)
    if path.stat().st_size > 100*1024*1024:
        raise ValueError('Source exceeds bounded document size')
    if kind == 'project_inputs':
        from ..engineering_data.module_bridge import verify
        if path.name != 'inputs.json' or not context:
            raise ValueError('Verified project input bundle required')
        verify(path.parent)
        data = read_json(path)
        if any(data[k] != context[k] for k in ('project_id', 'scenario_id')):
            raise ValueError('Project facts do not belong to declared project/scenario')
        rows = []
        for row in data['parameters']:
            q = row['quantity']
            rows.append(dict(text=row['name']+' = '+str(q['value'])+' '+row['source_unit']+'; '+
                             q['classification']+'; '+row['source_text'],
                             parameter_id=row['id'], entity_id=row['entity_id'],
                             json_pointer='/parameters/'+str(len(rows)),
                             original_project_source=data['project_source'], original_pointer=q['source_pointer'],
                             source_classification=q['classification']))
        if file_hash(path) != spec['sha256']:
            raise ValueError('Project input source changed during indexing')
        return rows, dict(coverage_status='declared source inputs; not authenticated', issues=[],
                          source_assertions_authenticated=False), 'sha256:'+spec['sha256']
    if path.suffix.lower() not in ('.pdf', '.md', '.txt', '.docx'):
        raise ValueError('Use an existing supported document extractor')
    extracted = documents.extract(path, pages=descriptor.get('pages'))
    if file_hash(path) != spec['sha256']:
        raise ValueError('Document changed during indexing')
    return extracted['passages'], {k: extracted[k] for k in ('coverage_status','issues','selected_pages','page_count','coverage_scope') if k in extracted}, 'sha256:'+spec['sha256']


def records(manifest, summaries=None):
    context = project_context(manifest)
    total = 0
    for descriptor in manifest['sources']:
        rows, review, immutable = passages(descriptor, context)
        if sum(len(r['text']) for r in rows) > MAX_TEXT:
            raise ValueError('Extracted source text exceeds bounded size')
        metadata = {k: descriptor[k] for k in ('id', 'role', 'title', 'publisher', 'edition', 'url',
                                               'discipline', 'jurisdiction', 'conditions')}
        metadata.update(source=descriptor['source'], immutable_source=immutable,
                        publication_metadata_state='declared_not_authenticated',
                        applicability_assessment='not_assessed', extraction_review=review,
                        missing_metadata=[k for k in ('publisher', 'edition', 'url') if metadata[k] is None])
        if len(canonical(metadata).encode('utf-8')) > 256*1024:
            raise ValueError('Source review metadata too large; explicitly select relevant PDF pages')
        if summaries is not None:
            summaries[descriptor['id']] = metadata
        for passage in rows:
            location = {k: v for k, v in passage.items() if k != 'text'}
            for start in range(0, len(passage['text']), CHUNK):
                text = passage['text'][start:start+CHUNK]
                locator = dict(**location, character_start=start, character_end=start+len(text))
                row = dict(source_id=descriptor['id'], metadata=metadata, locator=locator,
                           text=text, project_id=context['project_id'] if descriptor['role']=='project_input' else None,
                           scenario_id=context['scenario_id'] if descriptor['role']=='project_input' else None,
                           design_accepted=False)
                row['id'] = digest_value(row)
                total += 1
                if total > 10000:
                    raise ValueError('Knowledge record limit exceeded')
                yield row


def search_text(row):
    # A source-wide condition/title must not make every page look like a citation
    # for that term. Declared metadata remains available through explicit filters.
    return row['text']
