"""Bind declared terminal choices to verified per-space thermal/air balances."""
import argparse
import json
import math
from pathlib import Path
from shapely.geometry import Polygon,box,mapping
from .cli import digest
from .module_contract import read_json,validate
from .modules import verify_result
from . import spatial_air_balance,air_allocation,air_load,service_areas
from .workspace import allowed


def prepare(balance,producer,bases):
    if producer['execution']['status']!='completed' or producer['payload_schema'] not in ('bsa.spatial-boxes/1','bsa.spatial-polygons/1'):raise ValueError('Verified supported source spaces required')
    validate(producer['payload'])
    calculated=balance['calculation']['room_balances']
    spaces={s['id']:s for s in producer['payload']['spaces']}
    if set(calculated)!=set(spaces) or not isinstance(bases,dict) or set(bases)!=set(spaces):raise ValueError('Terminal choices must cover every balanced space exactly')
    allocations={};ids=set()
    classes={'given','measured','assumed','secondary_transcription','design_choice'}
    def sourced(row):
        return isinstance(row.get('source'),str) and bool(row['source'].strip()) and isinstance(row.get('classification'),str) and row['classification'] in classes
    for guid,space in spaces.items():
        basis=bases[guid]
        if not isinstance(basis,dict) or set(basis)!={'terminals','turndown'}:raise ValueError('Exact terminal choices and sourced turndown required;replacement flows/areas forbidden')
        turn=basis['turndown']
        if not isinstance(turn,dict) or set(turn)!={'value','unit','source','classification'} or turn['unit']!='1' or not sourced(turn):raise ValueError('Source-classified dimensionless turndown required')
        if not isinstance(basis['terminals'],list) or not basis['terminals']:raise ValueError('At least one declared terminal required per space')
        for terminal in basis['terminals']:
            if not isinstance(terminal,dict) or set(terminal)!={'id','center_m','unit','source','classification'} or terminal['unit']!='m' or not sourced(terminal) or not isinstance(terminal['id'],str) or not terminal['id'].strip() or terminal['id'] in ids:raise ValueError('Unique source-classified metre terminal IDs/centres required across spaces')
            ids.add(terminal['id'])
        boundary=Polygon(space['boundary_vertices']) if producer['payload_schema']=='bsa.spatial-polygons/1' else box(space['origin_m'][0],space['origin_m'][1],space['origin_m'][0]+space['size_m'][0],space['origin_m'][1]+space['size_m'][1])
        boundary=boundary.normalize()
        result=air_allocation.prepare(mapping(boundary),[{k:t[k] for k in ('id','center_m')} for t in basis['terminals']],calculated[guid]['inputs'],turn['value'])
        if result['load']!=calculated[guid]:raise ValueError('Terminal allocation changed inherited room thermal/flow inputs')
        allocations[guid]=dict(allocation=result,design_basis=basis,floor_elevation_m=space['floor_elevation_m'] if producer['payload_schema']=='bsa.spatial-polygons/1' else space['origin_m'][2])
    maximum=math.fsum(t['maximum_flow_L_s'] for r in allocations.values() for t in r['allocation']['terminals'])
    minimum=math.fsum(t['minimum_flow_L_s'] for r in allocations.values() for t in r['allocation']['terminals'])
    if not math.isclose(maximum,balance['calculation']['totals']['supply_flow_L_s'],rel_tol=1e-10):raise ValueError('Whole-space terminal maximum flows do not conserve inherited total')
    return dict(schema='bsa.spatial-air-allocation/1',coordinate_frame=producer['payload']['coordinate_frame'],units=dict(length='m',area='m2',flow='L/s'),rooms=allocations,maximum_flow_L_s=maximum,minimum_flow_L_s=minimum,terminal_count=len(ids),simulation_executed=False,
        ADPI_verified=False,installed_geometry_verified=False,design_accepted=False,
        scope='Declared planar terminal design choices and nearest-centre area/flow allocation only;not air coverage,ADPI,flex/duct routing or installed design acceptance')


def run(balance,basis,out):
    balance,basis,out=[Path(p).resolve() for p in (balance,basis,out)]
    if not all(allowed(p) for p in (balance,basis,out)) or out.exists():raise ValueError('Selected workspace and new terminal allocation output required')
    report=spatial_air_balance.verify(balance.parent)
    if balance.name!='air-balance.json':raise ValueError('Exact verified spatial air balance report required')
    producer=verify_result(report['producer_result']);pins=dict(report['inputs']);pins[str(balance)]=digest(balance);pins[str(basis)]=digest(basis)
    for method in (__file__,air_allocation.__file__,air_load.__file__,service_areas.__file__,spatial_air_balance.__file__):pins[str(Path(method).resolve())]=digest(Path(method))
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Terminal allocation output must be separate from sources')
    calculation=prepare(report,producer,read_json(basis));spatial_air_balance.verify(balance.parent)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Terminal allocation source/method changed')
    result=dict(balance_result=str(balance),basis=str(basis),inputs=pins,calculation=calculation,design_accepted=False)
    out.mkdir(parents=True);(out/'terminal-allocation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected terminal allocation workspace required')
    result=read_json(folder/'terminal-allocation.json')
    if set(result)!={'balance_result','basis','inputs','calculation','design_accepted'} or result['design_accepted'] is not False:raise ValueError('Exact scoped terminal allocation report required')
    balance=Path(result['balance_result']);basis=Path(result['basis'])
    if not allowed(balance) or not allowed(basis) or balance.name!='air-balance.json':raise ValueError('Selected verified balance/basis sources required')
    report=spatial_air_balance.verify(balance.parent);producer=verify_result(report['producer_result'])
    pins=dict(report['inputs']);pins[str(balance)]=digest(balance);pins[str(basis)]=digest(basis)
    for method in (__file__,air_allocation.__file__,air_load.__file__,service_areas.__file__,spatial_air_balance.__file__):pins[str(Path(method).resolve())]=digest(Path(method))
    if pins!=result['inputs'] or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Terminal allocation source/method pins differ')
    if result['calculation']!=json.loads(json.dumps(prepare(report,producer,read_json(basis)))):raise ValueError('Terminal allocation differs from source replay')
    return result


def verify_workflow(tasks,root,plan_root,record):
    for task in tasks:
        if task['kind']!='spatial_air_allocation':continue
        folder=Path(root)/task['id']
        if not (folder/'terminal-allocation.json').is_file():
            if record[task['id']]['status']=='pass':raise ValueError('Passing terminal allocation lacks its report')
            continue
        report=verify(folder)
        if Path(report['balance_result'])!=(Path(root)/task['depends_on']/'air-balance.json').resolve() or Path(report['basis'])!=(Path(plan_root)/task['basis']).resolve():raise ValueError('Terminal allocation replaced declared balance/basis')
        if record[task['id']]['status']!='pass' or record[task['depends_on']]['status']!='pass':raise ValueError('Terminal allocation dependency status differs')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('balance');parser.add_argument('--basis',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.balance,args.basis,args.out)
