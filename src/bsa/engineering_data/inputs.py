"""Read-only source parameter ownership; never edit calculated results as inputs."""
import hashlib
import json
from pathlib import Path

from ..cli import digest
from ..module_contract import read_json
from ..workspace import ROOT
from .model import entity_id, validate_schema, validate_reference
from .quantities import quantity, validate_quantity

SCHEMA_PATH = ROOT/'contracts/engineering-inputs-v1.json'
SCOPE = ('Declared primary-project input values and source notes only; source assertions are not '
         'independently authenticated and this catalogue grants no modification authority')


def pointer_part(value):
    return str(value).replace('~', '~0').replace('/', '~1')


def numeric_leaves(data, pointer=''):
    if type(data) in (int, float):
        return {pointer: data}
    if isinstance(data, dict):
        return {p: v for key, item in data.items()
                for p, v in numeric_leaves(item, pointer+'/'+pointer_part(key)).items()}
    if isinstance(data, list):
        return {p: v for i, item in enumerate(data)
                for p, v in numeric_leaves(item, pointer+'/'+str(i)).items()}
    return {}


def parameter_id(owner, name):
    key = json.dumps([owner, name], separators=(',', ':')).encode('utf-8')
    return 'bsa-parameter:'+hashlib.sha256(key).hexdigest()[:32]


def project_parameters(project, project_id, payload_schema):
    """Extract declared primary inputs only; does not establish current producer execution."""
    if payload_schema == 'bsa.air-allocation/1':
        from ..air_load import calculate
        calculate(project['load_inputs'])  # reuse exact units/classifications, no new thermal parser
        if any(not isinstance(t['center_m'],list) or len(t['center_m'])!=2 for t in project['terminals']):
            raise ValueError('Two source planar coordinates required')
    elif payload_schema == 'bsa.electrical-circuits/1':
        from ..providers.electrical_circuits import validate_project
        validate_project(project)
    elif payload_schema == 'bsa.lighting-source-audit/1':
        from ..lighting_audit.calculate import validate_project
        validate_project(project)
    else:
        raise ValueError('Supported primary source parameter mapping required')
    rows = []

    def add(kind, source_id, name, value, unit, pointer, *, source_unit=None,
            classification='declared', note=None, note_pointer=None):
        owner = entity_id(project_id, kind, source_id)
        text=note or 'No per-value source/classification supplied in the original project'
        if not isinstance(text,str) or not text.strip():raise ValueError('Source parameter note must be explicit text')
        rows.append(dict(id=parameter_id(owner, name), entity_id=owner, name=name,
            quantity=quantity(value, unit, pointer, classification),
            source_unit=source_unit or unit, source_text=text,
            source_note_pointer=note_pointer, role='source_input', review_required=True))

    if payload_schema == 'bsa.air-allocation/1':
        for name, row in project['load_inputs'].items():
            # The source's bare W/m2 gains thermal semantics from air_load's
            # cooling_allowance field. Preserve the original label separately.
            unit = 'W thermal/m2' if name == 'cooling_allowance' else row['unit']
            add('air_system', 'allocation', 'load.'+name, row['value'], unit,
                '/load_inputs/'+pointer_part(name)+'/value', source_unit=row['unit'],
                classification=row['classification'], note=row['source'],
                note_pointer='/load_inputs/'+pointer_part(name)+'/source')
        add('air_system', 'allocation', 'turndown', project['turndown'], '1', '/turndown')
        for i, terminal in enumerate(project['terminals']):
            for axis, value in zip(('x', 'y'), terminal['center_m']):
                add('air_terminal', terminal['id'], 'center_'+axis, value, 'm',
                    '/terminals/'+str(i)+'/center_m/'+str(('x', 'y').index(axis)),
                    note=project['geometry_basis'], note_pointer='/geometry_basis')
    elif payload_schema == 'bsa.lighting-source-audit/1':
        facts=[('lighting_system',project['room_id'],key,project[key],'/'+key)
               for key in ('fixture_count','auxiliary_allowance','annotation_area')]
        facts += [('lighting_product',p['id'],'input_power',p['input_power'],'/products/'+str(i)+'/input_power')
                  for i,p in enumerate(project['products'])]
        for kind,owner,name,fact,path in facts:
            note=fact['basis']+'; original role '+fact['source']['role']+' pointer '+fact['source']['pointer']
            add(kind,owner,name,fact['value'],fact['unit'],path+'/value',
                classification=fact['classification'],note=note,note_pointer=path+'/basis')
    else:
        add('electrical_system', 'supply', 'supply_voltage', project['supply_voltage_v'], 'V', '/supply_voltage_v')
        fields = {'demand_factor': '1', 'breaker_a': 'A', 'tabulated_ampacity_a': 'A',
                  'correction_factor': '1', 'route_length_m': 'm',
                  'vd_mv_a_m': 'mV/(A m)', 'max_vd_percent': '%'}
        devices = {'electrical_kw': 'kW electrical', 'power_factor': '1', 'x_m': 'm', 'y_m': 'm'}
        for group, kind, mapping in (('circuits', 'electrical_circuit', fields), ('devices', 'electrical_device', devices)):
            for i, row in enumerate(project[group]):
                note = project['sources'].get(row['source'], row['source'])
                note_pointer = ('/sources/'+pointer_part(row['source']) if row['source'] in project['sources']
                                else '/'+group+'/'+str(i)+'/source')
                for name, unit in mapping.items():
                    add(kind, row['id'], name, row[name], unit, '/'+group+'/'+str(i)+'/'+name,
                        note=note, note_pointer=note_pointer)
    mapped = {row['quantity']['source_pointer'] for row in rows}
    if len({row['id'] for row in rows})!=len(rows):raise ValueError('Duplicate source parameter identity')
    leaves = numeric_leaves(project)
    if len(mapped) != len(rows) or any(leaves.get(row['quantity']['source_pointer']) != row['quantity']['value'] for row in rows):
        raise ValueError('Parameter ownership or exact source location differs')
    return rows, dict(scope='Primary project JSON numeric leaves only; referenced geometry/documents remain in verified producer evidence',
        numeric_leaf_count=len(leaves), mapped_count=len(mapped), unmapped_numeric_pointers=sorted(set(leaves)-mapped))


def build(source):
    from .module_bridge import project_result, reference
    source = Path(source).resolve()
    model = project_result(source)  # Independently replay original provider first.
    result = read_json(source)
    request_path = Path(result['request']['path']).resolve()
    request = read_json(request_path)
    project_path = (request_path.parent/request['sources']['project']['path']).resolve()
    project_ref = reference(project_path)
    request_ref = reference(request_path)
    if result['inputs'].get(str(project_path)) != project_ref['sha256'] or request_ref['sha256'] != result['request']['sha256']:
        raise ValueError('Primary source/request identity differs from verified producer')
    project = read_json(project_path)
    rows, coverage = project_parameters(project, model['project_id'], model['payload_schema'])
    owner_ids = {entity['id'] for entity in model['entities']}
    if any(row['entity_id'] not in owner_ids for row in rows):
        raise ValueError('Source parameter has no common entity owner')
    data = dict(schema='bsa.engineering-inputs/1', project_id=model['project_id'], scenario_id=model['scenario_id'],
        source_result=model['source_result'], source_request=request_ref, project_source=project_ref,
        parameters=rows, coverage=coverage,
        scope=SCOPE, source_assertions_authenticated=False, design_accepted=False)
    validate(data)
    if digest(source) != model['source_result']['sha256'] or digest(project_path) != project_ref['sha256'] or digest(request_path) != request_ref['sha256']:
        raise ValueError('Source changed during parameter extraction')
    return data


def validate(data):
    validate_schema(data, SCHEMA_PATH, 'Engineering inputs contract')
    for key in ('source_result', 'source_request', 'project_source'):
        validate_reference(data[key])
    seen, pointers = set(), set()
    for row in data['parameters']:
        validate_quantity(row['quantity'])
        if row['id'] != parameter_id(row['entity_id'], row['name']) or row['id'] in seen or row['quantity']['source_pointer'] in pointers:
            raise ValueError('Duplicate or inconsistent source parameter identity')
        seen.add(row['id'])
        pointers.add(row['quantity']['source_pointer'])
    coverage = data['coverage']
    missing = coverage['unmapped_numeric_pointers']
    if coverage['mapped_count'] != len(seen) or len(set(missing)) != len(missing) or pointers.intersection(missing) or coverage['numeric_leaf_count'] != len(seen)+len(missing) or data['scope'] != SCOPE:
        raise ValueError('Source parameter coverage differs')
    return data
