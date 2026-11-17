"""Project existing independently verified module results into common data."""
import json
from pathlib import Path

from ..cli import digest
from ..module_contract import read_json
from ..workspace import ROOT, intake_output
from ..source_refs import reference, resolve_reference
from .model import SCHEMA_PATH, entity_id, validate
from .quantities import quantity
from .report import render

SCOPE = 'Verified derived data view only; original sources, numerical failures and engineering review remain authoritative'


def project_result(path):
    # Lazy boundary: importing the common model loads no domain solver.
    from ..modules import verify_result
    path = Path(path).resolve()
    ref = reference(path)
    result = verify_result(path)
    if result['project_id'] == 'workflow-allocation':
        raise ValueError('Legacy placeholder identity cannot be a common project; use an explicit source-bound project request')
    if result['execution']['status'] != 'completed' or result['payload'] is None:
        raise ValueError('Completed verified producer required; unavailable is not empty engineering data')
    payload = result['payload']
    if payload['schema'] not in ('bsa.air-allocation/1', 'bsa.electrical-circuits/1', 'bsa.lighting-source-audit/1'):
        raise ValueError('No executed common-data mapping for this producer payload')
    entities, edges = [], []

    def entity(kind, source_id, quantities=None, attributes=None):
        item = dict(id=entity_id(result['project_id'], kind, source_id), kind=kind,
                    source_id=source_id, quantities=quantities or {}, attributes=attributes or {})
        entities.append(item)
        return item['id']

    def q(data, key, unit, pointer, classification='calculated'):
        return quantity(data[key], unit, pointer+'/'+key, classification)

    if payload['schema'] == 'bsa.air-allocation/1':
        system = entity('air_system', 'allocation', {
            'total_cooling': q(payload, 'total_cooling_kW_thermal', 'kW thermal', '/payload'),
            'sensible_trial': q(payload, 'sensible_trial_kW_thermal', 'kW thermal', '/payload'),
            'supply_flow': q(payload, 'supply_flow_L_s', 'L/s', '/payload'),
            'turndown': q(payload, 'turndown', '1', '/payload', 'declared')})
        for index, row in enumerate(payload['terminals']):
            pointer = '/payload/terminals/'+str(index)
            terminal = entity('air_terminal', row['id'], {
                'maximum_flow': q(row, 'maximum_flow_L_s', 'L/s', pointer),
                'minimum_flow': q(row, 'minimum_flow_L_s', 'L/s', pointer),
                'allocated_load_area': q(row, 'allocated_load_area_m2', 'm2', pointer)})
            edges.append(dict(kind='serves', **{'from': system, 'to': terminal}))
    elif payload['schema'] == 'bsa.lighting-source-audit/1':
        totals=payload['totals']
        units={'fixture_count':'count','luminaire_input_W':'W electrical',
               'auxiliary_allowance_W':'W electrical','budget_input_W':'W electrical',
               'reported_floor_area_m2':'m2','annotation_area_m2':'m2',
               'calculated_lpd_W_m2':'W electrical/m2','budget_density_W_m2':'W electrical/m2',
               'annotation_budget_density_W_m2':'W electrical/m2','native_reported_lpd_W_m2':'W electrical/m2'}
        declared={'auxiliary_allowance_W','annotation_area_m2','reported_floor_area_m2','native_reported_lpd_W_m2'}
        system=entity('lighting_system',payload['room_id'],{k:q(totals,k,u,'/payload/totals',
                      'declared' if k in declared else 'calculated') for k,u in units.items()})
        for i,row in enumerate(payload['products']):
            entity('lighting_product',row['id'],{'input_power':q(row,'input_power_W','W electrical',
                '/payload/products/'+str(i),row['classification'])})
        for i,row in enumerate(payload['fixtures']):
            fixture=entity('lighting_fixture',row['id'],{'input_power':q(row,'input_power_W',
                'W electrical','/payload/fixtures/'+str(i))},dict(product_id=row['product_id']))
            edges.append(dict(kind='supplies',**{'from':system,'to':fixture}))
    else:
        quantities = {'supply_voltage': q(payload, 'supply_voltage_v', 'V', '/payload', 'declared')}
        for phase, value in payload['phase_demand_va'].items():
            quantities['phase_'+phase+'_demand'] = quantity(value, 'VA', '/payload/phase_demand_va/'+phase)
        system = entity('electrical_system', 'supply', quantities)
        mapping = {'connected_electrical_kw': 'kW electrical', 'connected_va': 'VA',
                   'demand_va': 'VA', 'design_current_a': 'A', 'effective_ampacity_a': 'A',
                   'voltage_drop_v': 'V', 'voltage_drop_percent': '%'}
        for index, row in enumerate(payload['circuits']):
            pointer = '/payload/circuits/'+str(index)
            quantities = {name: q(row, name, unit, pointer) for name, unit in mapping.items()}
            circuit = entity('electrical_circuit', row['id'], quantities,
                             dict(phase=row['phase'], source=row['source']))
            edges.append(dict(kind='supplies', **{'from': system, 'to': circuit}))
            for name in row['device_ids']:
                device = entity('electrical_device', name)
                edges.append(dict(kind='supplies', **{'from': circuit, 'to': device}))
    data = dict(schema='bsa.engineering-data/1', project_id=result['project_id'],
                scenario_id=result['scenario_id'], coordinate_frame=payload['coordinate_frame'],
                source_result=ref, provider=result['provider'], payload_schema=result['payload_schema'],
                source_acceptance=result['acceptance'],
                source_flags={k: payload[k] for k in ('status', 'checks', 'pending', 'geometry_bound',
                              'room_sensible_load_verified', 'native_calculation_executed', 'source_assertions_authenticated',
                              'regulatory_compliance', 'design_accepted') if k in payload},
                entities=entities, relationships=edges, design_accepted=False)
    if digest(path) != ref['sha256']:
        raise ValueError('Source result changed during projection')
    return validate(data)


def methods():
    files = [*Path(__file__).parent.glob('*.py'), SCHEMA_PATH,
             ROOT/'src/bsa/source_refs.py',
             ROOT/'contracts/engineering-inputs-v1.json',
             ROOT/'src/bsa/workspace.py', ROOT/'src/bsa/module_contract.py',
             ROOT/'src/bsa/modules.py', ROOT/'src/bsa/cli.py']
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(files)}


def export(source, out, *, include_inputs=False):
    source, out = Path(source).resolve(), Path(out).resolve()
    if not intake_output(out) or out.exists() or out == source or out in source.parents:
        raise ValueError('Fresh output in project or tool runs, separate from source required')
    if type(include_inputs) is not bool:
        raise ValueError('Explicit boolean input-catalogue selection required')
    pins = methods()
    data = project_result(source)
    catalogue = None
    if include_inputs:
        from .inputs import build
        catalogue = build(source)
        if catalogue['source_result'] != data['source_result']:
            raise ValueError('Input catalogue and derived model have different sources')
    summary = render(data, catalogue)
    if pins != methods() or digest(source) != data['source_result']['sha256']:
        raise ValueError('Source or methods changed during projection')
    out.mkdir(parents=True)
    (out/'model.json').write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    (out/'summary.html').write_text(summary, encoding='utf-8')
    names = ['model.json', 'summary.html']
    if catalogue is not None:
        (out/'inputs.json').write_text(json.dumps(catalogue, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        names.append('inputs.json')
    receipt = dict(schema='bsa.engineering-data-export/2' if include_inputs else 'bsa.engineering-data-export/1', source_result=data['source_result'],
                   methods=pins, artifacts={n: digest(out/n) for n in names},
                   scope=SCOPE, design_accepted=False)
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    verify(out)
    return receipt


def verify(out):
    out = Path(out).resolve()
    if not intake_output(out):
        raise ValueError('Engineering data output outside selected workspace')
    inventory = {p.name for p in out.iterdir()}
    base = {'receipt.json', 'model.json', 'summary.html'}
    if inventory not in (base, base|{'inputs.json'}) or any(p.is_symlink() or not p.is_file() for p in out.iterdir()):
        raise ValueError('Exact regular-file engineering data inventory required')
    receipt = read_json(out/'receipt.json')
    if set(receipt) != {'schema', 'source_result', 'methods', 'artifacts', 'scope', 'design_accepted'} or receipt['schema'] not in ('bsa.engineering-data-export/1', 'bsa.engineering-data-export/2') or receipt['scope'] != SCOPE or receipt['design_accepted'] is not False:
        raise ValueError('Exact unaccepted common-data receipt required')
    includes_inputs = receipt['schema'] == 'bsa.engineering-data-export/2'
    names = base|{'inputs.json'} if includes_inputs else base
    if inventory != names:
        raise ValueError('Versioned data bundle inventory differs')
    if receipt['methods'] != methods() or receipt['artifacts'] != {n: digest(out/n) for n in sorted(names-{'receipt.json'})}:
        raise ValueError('Common-data artifacts or methods changed')
    source = resolve_reference(receipt['source_result'])
    data = validate(read_json(out/'model.json'))
    if data != project_result(source):
        raise ValueError('Common data differs from independently verified producer')
    catalogue = None
    if includes_inputs:
        from .inputs import build, validate as validate_inputs
        catalogue = validate_inputs(read_json(out/'inputs.json'))
        if catalogue != build(source):
            raise ValueError('Input parameters differ from verified original project')
    if (out/'summary.html').read_text(encoding='utf-8') != render(data, catalogue):
        raise ValueError('Common report differs from shared data')
    checked = dict(integrity_pass=True, entity_count=len(data['entities']),
                quantity_count=sum(len(e['quantities']) for e in data['entities']),
                source_result=data['source_result'], scope=SCOPE, design_accepted=False)
    if catalogue is not None:
        checked['input_parameter_count'] = len(catalogue['parameters'])
        checked['unmapped_numeric_input_count'] = len(catalogue['coverage']['unmapped_numeric_pointers'])
    return checked
