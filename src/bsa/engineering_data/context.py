"""Explicit persisted project identity, independent of mutable engineering values."""
from pathlib import Path
from uuid import UUID, uuid4

from ..module_contract import read_json
from ..workspace import allowed, intake_output


def validate(data):
    if not isinstance(data, dict) or set(data) != {'schema', 'project_id', 'name', 'scenario_id'} or data['schema'] != 'bsa.project-context/1':
        raise ValueError('Exact versioned project context required')
    for key in ('project_id', 'name', 'scenario_id'):
        if not isinstance(data[key], str) or not data[key].strip() or len(data[key]) > 200:
            raise ValueError('Explicit bounded project identity/name/scenario required')
    identity = UUID(data['project_id'])
    if identity.version != 4 or str(identity) != data['project_id']:
        raise ValueError('Canonical persisted UUID4 project identity required')
    return data


def load(path):
    path = Path(path).resolve()
    if not allowed(path) or not path.is_file():
        raise ValueError('Project context outside selected workspace or missing')
    return validate(read_json(path))


def create(name, scenario_id, out):
    import json
    out = Path(out).resolve()
    if not intake_output(out) or out.exists():
        raise ValueError('Fresh project context in selected project or tool runs required')
    data = validate(dict(schema='bsa.project-context/1', project_id=str(uuid4()),
                         name=name, scenario_id=scenario_id))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
    return data
