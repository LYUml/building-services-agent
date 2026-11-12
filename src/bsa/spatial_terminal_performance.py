"""Query pinned terminal catalogues using exact inherited maximum/minimum flows."""
import argparse
import importlib.metadata
import json
from pathlib import Path
from .cli import digest
from .module_contract import read_json
from . import spatial_air_allocation,terminal_performance
from .workspace import allowed


def selections(path):
    path=Path(path).resolve();before=digest(path);data=read_json(path);pins={str(path):before};selected={}
    if not isinstance(data,dict) or not data:raise ValueError('Nonempty exact terminal selection mapping required')
    for terminal,row in data.items():
        if not isinstance(row,dict) or set(row)!={'settings','source','classification'} or not isinstance(row['source'],str) or not row['source'].strip() or row['classification'] not in ('given','measured','assumed','secondary_transcription','design_choice'):
            raise ValueError('Explicit source-classified terminal product selections required;replacement flows forbidden')
        relative=row['settings']
        if not isinstance(relative,str) or not relative.strip() or Path(relative).is_absolute():raise ValueError('Relative catalogue settings path required')
        setting=(path.parent/relative).resolve()
        if not allowed(setting):raise ValueError('Product settings outside selected source workspace')
        spec,source_pins=terminal_performance.settings_inputs(setting);pins.update(source_pins)
        catalogue=read_json(setting.parent/spec['catalogue'])
        if catalogue.get('source_sha256')!=spec['source_sha256'] or not isinstance(catalogue.get('model'),str) or not catalogue['model'].strip() or not isinstance(catalogue.get('locator'),str) or not catalogue['locator'].strip() or type(catalogue.get('damper')) is not bool:
            raise ValueError('Source-bound product model,locator and explicit damper state required')
        if not isinstance(catalogue.get('rows'),list) or len(catalogue['rows'])<2:raise ValueError('At least two source performance rows required')
        terminal_performance.calculate(catalogue['rows'],catalogue['rows'][0]['flow_L_s'])
        selected[terminal]=dict(selection=row,settings=spec,catalogue=catalogue)
    return selected,pins


def prepare(allocation,selected):
    terminals={t['id']:t for room in allocation['calculation']['rooms'].values() for t in room['allocation']['terminals']}
    if set(terminals)!=set(selected):raise ValueError('Product selections must cover every allocated terminal exactly')
    rows={};requests=[]
    for name,terminal in terminals.items():
        selection=selected[name];catalogue=selection['catalogue'];cases={}
        for label,key in [('maximum','maximum_flow_L_s'),('minimum','minimum_flow_L_s')]:
            point=terminal_performance.calculate(catalogue['rows'],terminal[key]);cases[label]=point
            if point['status']=='outside_catalogue':
                requests.append(dict(code='operating_flow_outside_catalogue',terminal=name,condition=label,flow_L_s=point['flow_L_s'],source_range_L_s=[catalogue['rows'][0]['flow_L_s'],catalogue['rows'][-1]['flow_L_s']],action='Review sourced product selection or declared terminal count/positions;rerun inherited allocation,never clamp or override its flows'))
        rows[name]=dict(product={k:catalogue[k] for k in ('model','locator','damper','source_sha256')},conditions=selection['settings']['conditions'],selection_basis=selection['selection'],cases=cases)
    return dict(schema='bsa.spatial-terminal-performance/1',units=dict(flow='L/s',pressure='Pa',throw='m'),terminals=rows,outside_catalogue_cases=len(requests),data_requests=requests,status='pending' if requests else 'calculated',
        product_applicability_verified=False,ADPI_verified=False,fan_pressure_complete=False,room_acoustics_verified=False,design_accepted=False,
        scope='Bounded source-table T0.25/static/total pressure interpolation only;NC retained at exact catalogue flow or as adjacent qualified references,never interpolated. No characteristic L,ADPI,room acoustics,installation or complete fan duty acceptance')


def method_pins():
    if importlib.metadata.version('fluids')!='1.3.1':raise ValueError('Pinned fluids1.3.1 required')
    return {str(Path(p).resolve()):digest(Path(p)) for p in (__file__,terminal_performance.__file__,spatial_air_allocation.__file__,terminal_performance.interp.__code__.co_filename)}


def run(allocation,basis,out):
    allocation,basis,out=[Path(p).resolve() for p in (allocation,basis,out)]
    if not all(allowed(p) for p in (allocation,basis,out)) or out.exists() or allocation.name!='terminal-allocation.json':raise ValueError('Verified allocation,selected source workspace and new output required')
    before=digest(allocation);record=spatial_air_allocation.verify(allocation.parent);selected,pins=selections(basis)
    pins.update(record['inputs']);pins[str(allocation)]=before;pins.update(method_pins())
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Performance output must be separate from sources')
    calculation=prepare(record,selected);spatial_air_allocation.verify(allocation.parent)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Performance source or method changed')
    result=dict(allocation_result=str(allocation),basis=str(basis),inputs=pins,calculation=calculation,design_accepted=False)
    out.mkdir(parents=True);(out/'terminal-performance.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected performance workspace required')
    result=read_json(folder/'terminal-performance.json')
    if set(result)!={'allocation_result','basis','inputs','calculation','design_accepted'} or result['design_accepted'] is not False:raise ValueError('Exact scoped performance report required')
    source=Path(result['allocation_result']);basis=Path(result['basis'])
    if not allowed(source) or not allowed(basis) or source.name!='terminal-allocation.json':raise ValueError('Selected verified terminal source required')
    before=digest(source);record=spatial_air_allocation.verify(source.parent);selected,pins=selections(basis)
    pins.update(record['inputs']);pins[str(source)]=before;pins.update(method_pins())
    if pins!=result['inputs'] or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Performance source/method pins differ')
    if prepare(record,selected)!=result['calculation']:raise ValueError('Terminal performance differs from source replay')
    return result


def verify_workflow(tasks,root,plan_root,record):
    for task in tasks:
        if task['kind']!='spatial_terminal_performance':continue
        folder=Path(root)/task['id']
        if not (folder/'terminal-performance.json').is_file():
            if record[task['id']]['status']=='pass':raise ValueError('Passing terminal performance lacks report')
            continue
        report=verify(folder);expected='pass' if report['calculation']['status']=='calculated' else 'pending'
        if Path(report['allocation_result'])!=(Path(root)/task['depends_on']/'terminal-allocation.json').resolve() or Path(report['basis'])!=(Path(plan_root)/task['basis']).resolve():raise ValueError('Performance replaced declared allocation/basis')
        if record[task['id']]['status']!=expected or record[task['depends_on']]['status']!='pass':raise ValueError('Performance execution dependency differs')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('allocation');parser.add_argument('--basis',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.allocation,args.basis,args.out)
