"""Explicit source roles, publication metadata and declared applicability."""
from ..module_contract import read_json
from ..source_refs import resolve_reference
from ..workspace import allowed

ROLES = {'normative_source', 'manufacturer_source', 'course_source', 'method_reference',
         'agent_guide', 'rule_pack_snapshot', 'example', 'project_input'}
KINDS = {'document', 'git_reference', 'project_inputs'}
FIELDS = {'id', 'kind', 'role', 'source', 'title', 'publisher', 'edition', 'url',
          'discipline', 'jurisdiction', 'conditions'}


def validate(data):
    if not isinstance(data, dict) or set(data) != {'schema', 'project_context', 'sources'} or data['schema'] != 'bsa.knowledge-manifest/1':
        raise ValueError('Exact versioned knowledge manifest required')
    if data['project_context'] is not None:
        resolve_reference(data['project_context'])
    sources = data['sources']
    if not isinstance(sources, list) or not 1 <= len(sources) <= 40:
        raise ValueError('One to forty explicitly selected knowledge sources required')
    ids = set()
    for row in sources:
        if not isinstance(row, dict) or set(row)-{'pages'} != FIELDS or not isinstance(row['kind'], str) or not isinstance(row['role'], str) or row['kind'] not in KINDS or row['role'] not in ROLES:
            raise ValueError('Exact supported source descriptor required')
        if 'pages' in row and (row['kind'] != 'document' or not isinstance(row['pages'], list) or not 1<=len(row['pages'])<=50 or any(type(p) is not int or p<1 for p in row['pages']) or len(set(row['pages']))!=len(row['pages'])):
            raise ValueError('Unique positive selected document pages required')
        for key in ('id', 'title', 'discipline', 'jurisdiction', 'conditions'):
            if not isinstance(row[key], str) or not row[key].strip() or len(row[key]) > (4000 if key == 'conditions' else 300):
                raise ValueError('Explicit bounded source metadata required: '+key)
        for key in ('publisher', 'edition', 'url'):
            if row[key] is not None and (not isinstance(row[key], str) or not row[key].strip() or len(row[key]) > 2000):
                raise ValueError('Unknown metadata must be null, not invented')
        if row['id'] in ids:
            raise ValueError('Duplicate source identity')
        ids.add(row['id'])
        if (row['role'] == 'project_input') != (row['kind'] == 'project_inputs'):
            raise ValueError('Project facts require the verified project-input adapter')
        if row['kind'] == 'project_inputs' and data['project_context'] is None:
            raise ValueError('Project input sources require explicit project context')
    return data


def load(path):
    from pathlib import Path
    path = Path(path).resolve()
    if not allowed(path):
        raise ValueError('Manifest outside selected workspace')
    return validate(read_json(path))
