"""Inherit neutral space areas into the existing classified thermal/air balance."""
import argparse
import json
import math
from pathlib import Path
from .cli import digest
from .module_contract import read_json,validate
from .modules import verify_result
from . import air_load
from .workspace import allowed


def prepare(producer,bases):
    if producer['execution']['status']!='completed' or producer['payload_schema'] not in ('bsa.spatial-boxes/1','bsa.spatial-polygons/1'):
        raise ValueError('Completed supported neutral space producer required')
    validate(producer['payload'])
    spaces=producer['payload']['spaces']
    if not isinstance(bases,dict) or set(bases)!={s['id'] for s in spaces}:raise ValueError('Air balance basis must cover every source space exactly')
    balances={}
    for space in spaces:
        basis=bases[space['id']]
        if not isinstance(basis,dict) or set(basis)!=set(air_load.UNITS)-{'area'}:
            raise ValueError('Five classified load inputs required;replacement area forbidden')
        inputs=dict(basis,area=dict(value=space['floor_area_m2'],unit='m2',classification='geometry-derived',source='Neutral saved-space '+space['id']+' geometry;not surveyed/statutory area or verified detailed room load'))
        balances[space['id']]=air_load.calculate(inputs)
    totals={key:math.fsum(r[key] for r in balances.values()) for key in ('total_cooling_kW_thermal','sensible_trial_kW_thermal','supply_flow_L_s')}
    if any(not math.isfinite(v) or v<=0 for v in totals.values()):raise ValueError('Finite positive aggregate thermal/flow values required')
    return dict(schema='bsa.spatial-air-balance/1',coordinate_frame=producer['payload']['coordinate_frame'],units=dict(power='kW thermal',flow='L/s',area='m2'),
        room_balances=balances,totals=totals,status='calculated',room_sensible_load_verified=False,simulation_executed=False,design_accepted=False,
        scope='Geometry-bound uniform cooling allowance and constant-property supply-air balance only;not detailed room load,ADPI,plant electricity or physical HVAC acceptance')


def run(producer,basis,out):
    producer,basis,out=[Path(p).resolve() for p in (producer,basis,out)]
    if not all(allowed(p) for p in (producer,basis,out)) or out.exists():raise ValueError('Selected workspace and new air balance output required')
    result=verify_result(producer)
    paths=[producer,basis,Path(__file__).resolve(),Path(air_load.__file__).resolve()]
    pins={str(p):digest(p) for p in paths};pins.update(result['inputs'])
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Air balance output must be separate from sources')
    calculation=prepare(result,read_json(basis));verify_result(producer)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Air balance source or method changed')
    report=dict(producer_result=str(producer),basis=str(basis),inputs=pins,calculation=calculation,design_accepted=False)
    out.mkdir(parents=True);(out/'air-balance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def verify(folder):
    if not allowed(folder):raise ValueError('Spatial air balance requires selected workspace')
    report=read_json(Path(folder)/'air-balance.json')
    if set(report)!={'producer_result','basis','inputs','calculation','design_accepted'} or report['design_accepted'] is not False:raise ValueError('Exact scoped spatial air balance report required')
    if not allowed(report['producer_result']) or not allowed(report['basis']):raise ValueError('Spatial air balance sources require selected workspace')
    if any(digest(Path(p))!=sha for p,sha in report['inputs'].items()):raise ValueError('Spatial air balance inputs changed')
    result=verify_result(report['producer_result'])
    expected={str(p):digest(p) for p in (Path(report['producer_result']),Path(report['basis']),Path(__file__).resolve(),Path(air_load.__file__).resolve())};expected.update(result['inputs'])
    if expected!=report['inputs']:raise ValueError('Complete spatial air balance source/method pins required')
    if report['calculation']!=prepare(result,read_json(report['basis'])):raise ValueError('Spatial air balance differs from source replay')
    return report


def verify_workflow(tasks,run_root,plan_root,record):
    from .workflow_modules import result_path
    for task in tasks:
        if task['kind']!='spatial_air_balance':continue
        folder=Path(run_root)/task['id']
        if not (folder/'air-balance.json').is_file():
            if record[task['id']]['status']=='pass':raise ValueError('Passing spatial air balance lacks its report')
            continue
        report=verify(folder);parent=next(t for t in tasks if t['id']==task['depends_on'])
        if Path(report['producer_result'])!=result_path(run_root,parent).resolve() or Path(report['basis'])!=(Path(plan_root)/task['basis']).resolve():raise ValueError('Spatial air balance replaced its declared producer/basis')
        if record[task['id']]['status']!='pass' or record[parent['id']]['status']!='pass':raise ValueError('Spatial air balance execution dependency differs')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('producer');parser.add_argument('--basis',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.producer,args.basis,args.out)
