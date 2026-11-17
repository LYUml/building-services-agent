"""Versioned common identity/data view, retaining a verified original producer."""
import hashlib
import importlib.metadata
import json
from pathlib import PurePosixPath

from ..module_contract import read_json
from ..workspace import ROOT
from .quantities import validate_quantity

SCHEMA_PATH = ROOT/'contracts/engineering-data-v1.json'


def entity_id(project_id, kind, source_id):
    key = json.dumps([project_id, kind, source_id], ensure_ascii=False,
                     separators=(',', ':')).encode('utf-8')
    return 'bsa:'+hashlib.sha256(key).hexdigest()[:32]


def validate(data):
    import jsonschema
    if importlib.metadata.version('jsonschema') != '4.26.0':
        raise ValueError('Pinned jsonschema4.26.0 required')
    schema = read_json(SCHEMA_PATH)
    jsonschema.Draft202012Validator.check_schema(schema)
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(data))
    if errors:
        raise ValueError('Engineering data contract: '+errors[0].message)
    reference = data['source_result']
    name = reference['path']
    if '\\' in name or ':' in name or PurePosixPath(name).is_absolute() or any(
            part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('Normalized workspace-relative source reference required')
    ids, identities = set(), set()
    for entity in data['entities']:
        key = (entity['kind'], entity['source_id'])
        expected = entity_id(data['project_id'], *key)
        if key in identities or entity['id'] in ids or entity['id'] != expected:
            raise ValueError('Duplicate or inconsistent common entity identity')
        identities.add(key)
        ids.add(entity['id'])
        for row in entity['quantities'].values():
            validate_quantity(row)
    edges = set()
    for edge in data['relationships']:
        key = (edge['kind'], edge['from'], edge['to'])
        if edge['from'] not in ids or edge['to'] not in ids or edge['from'] == edge['to'] or key in edges:
            raise ValueError('Invalid or duplicate common relationship')
        edges.add(key)
    return data

