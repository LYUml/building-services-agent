"""Versioned module contracts validated by pinned upstream JSON Schema tooling."""
import importlib.metadata
import json
import math
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[2]
RULE_SCHEMA='bsa.rule-assessment/1'
SCHEMAS={'bsa.module-request/1':'request-v1.json','bsa.module-result/1':'result-v1.json','bsa.spatial-boxes/1':'spatial-boxes-v1.json','bsa.model-artifact/1':'model-artifact-v1.json','bsa.air-budget/1':'air-budget-v1.json','bsa.bound-air-budget/1':'bound-air-budget-v1.json','bsa.water-graph/1':'water-graph-v1.json','bsa.bound-water-graph/1':'bound-water-graph-v1.json'}


SCHEMAS['bsa.requirements-inventory/1']='requirements-inventory-v1.json'
SCHEMAS[RULE_SCHEMA]='rule-assessment-v1.json'
SCHEMAS['bsa.electrical-circuits/1']='electrical-circuits-v1.json'


def artifact_references(schema,data):
    if schema=='bsa.electrical-circuits/1':return ('report','schematic_dxf')
    if schema=='bsa.model-artifact/1':return ('model','verification')
    if schema=='bsa.air-budget/1':return ('report',)
    if schema=='bsa.water-graph/1':return ('report','raw')
    if schema=='bsa.bound-water-graph/1':return ('report','raw','network_input','model','binding')
    if schema=='bsa.bound-air-budget/1':return ('report','model','binding')+(('network_input',) if 'network_input' in data else ())
    return ()


def read_json(path):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate contract key: '+key)
            result[key]=value
        return result
    def invalid(value):raise ValueError('Nonfinite JSON number: '+value)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=pairs,parse_constant=invalid)


def spatial_projection(frame,geometry,contacts):
    """Project retained box audit fields;not an independent geometry extraction."""
    if geometry.get('complete_space_coverage') is not True:raise ValueError('Complete saved-space coverage required')
    return validate(dict(schema='bsa.spatial-boxes/1',coordinate_frame=frame,
        units=dict(length='m',area='m2'),classification='geometry-derived',
        spaces=[dict(id=r['guid'],origin_m=r['origin_m'],size_m=r['size_m'],floor_area_m2=r['floor_area_m2']) for r in geometry['spaces']],
        contacts=contacts,simulation_ready=False))


def validate(data,schema=None):
    import jsonschema
    if not isinstance(data,dict):raise ValueError('Contract object required')
    if importlib.metadata.version('jsonschema')!='4.26.0':raise ValueError('Pinned jsonschema4.26.0 required')
    schema=schema or data.get('schema')
    if schema not in SCHEMAS:raise ValueError('Unsupported module contract version')
    def finite(value):
        if type(value) is float and not math.isfinite(value):raise ValueError('Nonfinite contract number')
        if isinstance(value,dict):
            for item in value.values():finite(item)
        elif isinstance(value,list):
            for item in value:finite(item)
    finite(data)
    spec=read_json(ROOT/'contracts/modules'/SCHEMAS[schema]);jsonschema.Draft202012Validator.check_schema(spec)
    errors=list(jsonschema.Draft202012Validator(spec).iter_errors(data))
    if errors:raise ValueError('Contract violation: '+errors[0].message)
    if schema=='bsa.requirements-inventory/1':
        frame_spec=read_json(ROOT/'contracts/modules/request-v1.json')['properties']['coordinate_frame']
        if list(jsonschema.Draft202012Validator(frame_spec).iter_errors(data['coordinate_frame'])):raise ValueError('Invalid requirements coordinate frame')
        for key in ('documents','passages','requirements','tasks'):
            ids=[r['id'] for r in data[key]]
            if len(ids)!=len(set(ids)):raise ValueError('Duplicate requirements inventory identity')
        passages={r['id']:r for r in data['passages']};tasks={r['id'] for r in data['tasks']}
        for row in data['requirements']:
            if row['task'] not in tasks or row['passage'] not in passages or not row['quote'] or row['quote'] not in passages[row['passage']]['text']:raise ValueError('Requirements source/task correspondence differs')
        if {r['passage'] for r in data['requirements']}!={r['id'] for r in data['passages'] if r['disposition']=='requirement'}:raise ValueError('Requirements inventory loses source coverage')
    if schema=='bsa.electrical-circuits/1':
        frame_spec=read_json(ROOT/'contracts/modules/request-v1.json')['properties']['coordinate_frame']
        if list(jsonschema.Draft202012Validator(frame_spec).iter_errors(data['coordinate_frame'])):raise ValueError('Invalid electrical coordinate frame')
        ids=[r['id'] for r in data['circuits']]
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate common circuit ID')
        devices=[name for r in data['circuits'] for name in r['device_ids']]
        if len(devices)!=len(set(devices)):raise ValueError('Duplicate common electrical device ID')
        expected={k:all(r['checks'][k] for r in data['circuits']) for k in data['checks']}
        if data['checks']!=expected or (data['status']=='pass')!=all(expected.values()):raise ValueError('Electrical status/check aggregation differs')
        for phase,value in data['phase_demand_va'].items():
            if not math.isclose(value,sum(r['demand_va'] for r in data['circuits'] if r['phase']==phase),rel_tol=1e-10,abs_tol=1e-9):raise ValueError('Electrical phase apparent-power aggregation differs')
        for ref in artifact_references(schema,data):
            name=data[ref]['path']
            if '\\' in name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or ':' in name:raise ValueError('Electrical report must be local relative path')
    if schema==RULE_SCHEMA:
        frame_spec=read_json(ROOT/'contracts/modules/request-v1.json')['properties']['coordinate_frame']
        if list(jsonschema.Draft202012Validator(frame_spec).iter_errors(data['coordinate_frame'])):raise ValueError('Invalid common rule coordinate frame')
        identities=[(r['entity_id'],r['rule_id']) for r in data['checks']]
        if len(identities)!=len(set(identities)):raise ValueError('Duplicate entity/rule assessment')
        coverage_ids=[r['entity_id'] for r in data['coverage']]
        if len(coverage_ids)!=len(set(coverage_ids)) or set(coverage_ids)!={r['entity_id'] for r in data['checks']}:
            raise ValueError('Rule coverage must match assessed entities exactly')
        for row in data['checks']:
            original=row['original_status']
            expected_row='pass' if original=='pass' else 'fail' if original=='review_required' else 'pending'
            if row['status']!=expected_row:raise ValueError('Rule assessment changes original check meaning')
        states=[r['status'] for r in data['checks']]
        expected='fail' if 'fail' in states else 'pending' if 'pending' in states else 'pass'
        if data['status']!=expected:raise ValueError('Rule assessment status contradicts checks')
    if schema in ('bsa.spatial-boxes/1','bsa.model-artifact/1','bsa.air-budget/1','bsa.bound-air-budget/1','bsa.water-graph/1','bsa.bound-water-graph/1'):
        frame=data['coordinate_frame'];request_schema=read_json(ROOT/'contracts/modules/request-v1.json')
        if list(jsonschema.Draft202012Validator(request_schema['properties']['coordinate_frame']).iter_errors(frame)):raise ValueError('Invalid common coordinate frame')
    if schema in ('bsa.air-budget/1','bsa.bound-air-budget/1','bsa.water-graph/1','bsa.bound-water-graph/1'):
        if (data['status']=='pass')!=all(data['checks'].values()):raise ValueError('Analysis status differs from numerical checks')
    if schema in ('bsa.model-artifact/1','bsa.air-budget/1','bsa.bound-air-budget/1','bsa.water-graph/1','bsa.bound-water-graph/1'):
        for key in artifact_references(schema,data):
            name=data[key]['path']
            if '\\' in name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or ':' in name:raise ValueError('Model artifact references must be local relative paths')
    if schema in ('bsa.water-graph/1','bsa.bound-water-graph/1'):
        for kind in ('junctions','pipes','pumps'):
            ids=[r['id'] for r in data[kind]]
            if len(ids)!=len(set(ids)):raise ValueError('Duplicate common water graph IDs')
    if schema=='bsa.spatial-boxes/1':
        spaces={r['id']:r for r in data['spaces']}
        if len(spaces)!=len(data['spaces']):raise ValueError('Duplicate common space IDs')
        for row in spaces.values():
            if not math.isclose(row['floor_area_m2'],row['size_m'][0]*row['size_m'][1],rel_tol=1e-10,abs_tol=1e-9):raise ValueError('Common space area differs from box geometry')
        seen=set()
        for contact in data['contacts']:
            pair=tuple(sorted(contact['spaces']))
            if pair in seen or not set(pair)<=set(spaces):raise ValueError('Duplicate/unknown common contact identity')
            seen.add(pair)
    if schema=='bsa.module-result/1':
        if data['payload_schema'] not in SCHEMAS or data['payload_schema'] in ('bsa.module-request/1','bsa.module-result/1'):raise ValueError('Unsupported module payload contract')
        if data['execution']['status']=='completed':
            if data['payload'] is None:raise ValueError('Completed module needs validated payload')
            validate(data['payload'],data['payload_schema'])
            if data['payload_schema']=='bsa.electrical-circuits/1':
                for key in artifact_references(data['payload_schema'],data['payload']):
                    row=data['payload'][key]
                    if data['artifacts'].get(row['path'])!=row['sha256']:raise ValueError('Electrical artifact differs from module inventory')
            if data['payload_schema'] in ('bsa.model-artifact/1','bsa.air-budget/1','bsa.bound-air-budget/1','bsa.water-graph/1','bsa.bound-water-graph/1'):
                for key in artifact_references(data['payload_schema'],data['payload']):
                    row=data['payload'][key]
                    if data['artifacts'].get(row['path'])!=row['sha256']:raise ValueError('Model artifact payload differs from complete artifact inventory')
        elif data['payload'] is not None:raise ValueError('Unexecuted/failed module cannot expose a successful payload')
        if data['execution']['status']!='completed' and data['acceptance']['status']=='pass':raise ValueError('Unexecuted/failed module cannot pass acceptance')
        for name in data['artifacts']:
            if '\\' in name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or ':' in name:raise ValueError('Module artifact references must be local relative paths')
    return data
