"""Finite declared fan screening on one exact source-bound circular local path."""
import argparse
import json
from pathlib import Path

from . import circular_fan,rectangular_fan_selection as shared,fan_mechanical_limits
from .cli import digest
from .engine import ProjectError
from .module_contract import read_json
from .workspace import allowed


def method_pins():
    modules=(shared,circular_fan,circular_fan.network,circular_fan.pump,circular_fan.rectangular_fan,circular_fan.route_pressure,fan_mechanical_limits)
    return {str(Path(p).resolve()):digest(Path(p)) for p in (__file__,*(m.__file__ for m in modules))}


def context(pressure,catalogue):
    pressure,catalogue=Path(pressure).resolve(),Path(catalogue).resolve()
    if not all(allowed(p) for p in (pressure,catalogue)):raise ProjectError('Selected source workspace required')
    project,baseline,inputs,versions=circular_fan.source_project(pressure)
    data=read_json(catalogue);options=shared.candidates(data);files,mechanical=shared.mechanical_context(catalogue,data)
    inputs.update({str(p):digest(p) for p in [catalogue,*files]})
    return project,baseline,inputs,versions,options,mechanical


def run(pressure,catalogue,out):
    pressure,catalogue,out=[Path(p).resolve() for p in (pressure,catalogue,out)]
    if out.exists() or not allowed(out) or pressure==out or pressure in out.parents or out in pressure.parents or catalogue==out or out in catalogue.parents:
        raise ProjectError('Fresh selection output outside native source and catalogue required')
    _,baseline,inputs,versions,options,mechanical=context(pressure,catalogue)
    methods=method_pins()
    def unchanged():
        if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in {**inputs,**methods}.items()):raise ProjectError('Fan selection source or method changed')
    out.mkdir(parents=True)
    def evaluate(row,name):
        unchanged();folder=out/name;folder.mkdir();curve=folder/'curve.json';curve.write_text(json.dumps(row['curve'],indent=2),encoding='utf-8')
        try:
            result=circular_fan.run(pressure,curve,folder/'operating')
        except ProjectError as exc:
            unchanged()
            return shared.eligibility(dict(status='unsupported',calculated_checks_pass=False,reason=str(exc),curve_sha256=digest(curve)),mechanical.get(row['id']))
        unchanged()
        return shared.eligibility(dict(status=result['status'],calculated_checks_pass=result['calculated_checks_pass'],checks=result.get('checks'),operating_point=result.get('operating_point'),curve_sha256=digest(curve),report_sha256=digest(folder/'operating/fan.json')),mechanical.get(row['id']))
    result=shared.screen(options,evaluate)
    unchanged()
    result.update(inputs=inputs,method_inputs=methods,runtime_versions=versions,pressure_producer=str(pressure),catalogue=str(catalogue),inputs_unchanged=True,native_path_correspondence_pass=True,
        boundary_ports=baseline['boundary_ports'],scope='Finite declared numerical fan preference screening on an exact checked circular path; product applicability and full engineering remain pending',
        pending=['Actual vendor curve/installation/stable-region and mechanical identity','Native fan body/ports and updated airflow metadata','Motor electrical input, Hong Kong and whole-system acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'fan-selection.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def selected_input(producer,pressure,catalogue):
    """Reconstruct source candidates, eligibility and ranking before handing off a curve."""
    producer,pressure,catalogue=[Path(p).resolve() for p in (producer,pressure,catalogue)]
    if not allowed(producer):raise ProjectError('Selected source workspace required')
    path=producer/'fan-selection.json';before=digest(path);result=read_json(path)
    project,_,inputs,_,options,mechanical=context(pressure,catalogue)
    if result.get('inputs')!=inputs or result.get('pressure_producer')!=str(pressure) or result.get('catalogue')!=str(catalogue):raise ProjectError('Selection original input identity changed')
    if result.get('method_inputs')!=method_pins():raise ProjectError('Selection method changed; regenerate selection')
    if not all(result.get(k) is True for k in ('calculated_checks_pass','selected_rerun_pass','native_path_correspondence_pass')) or not isinstance(result.get('selected'),dict):raise ProjectError('No passing selected circular fan available')
    artifacts=result.get('artifacts',{});required={'selected/curve.json','selected/operating/fan.json','selected/operating/operating-network.json','selected/operating/analysis/network.json'}
    if not required<=set(artifacts):raise ProjectError('Selected fan artifact coverage missing')
    for name,sha in artifacts.items():
        target=(producer/name).resolve()
        if not target.is_relative_to(producer) or not target.is_file() or digest(target)!=sha:raise ProjectError('Selected fan artifact changed')
    records=result.get('candidates')
    if not isinstance(records,list) or len(records)!=len(options):raise ProjectError('Selected catalogue coverage changed')
    passing=[];solutions={}
    for index,(row,record) in enumerate(zip(options,records)):
        directory=f'candidate-{index:03d}';curve=producer/directory/'curve.json'
        if any(record.get(k)!=row[k] for k in ('id','source','preference')) or record.get('directory')!=directory or f'{directory}/curve.json' not in artifacts or read_json(curve)!=row['curve']:
            raise ProjectError('Original candidate identity, preference or curve changed')
        try:
            fresh,data=circular_fan.solve(project,row['curve']);expected={k:fresh.get(k) for k in ('status','calculated_checks_pass','checks','operating_point')}
        except ProjectError as exc:
            expected=dict(status='unsupported',calculated_checks_pass=False,reason=str(exc));data=None
        expected=shared.eligibility(expected,mechanical.get(row['id']))
        if any(record.get(k)!=v for k,v in expected.items()):raise ProjectError('Candidate result differs from fresh source solve')
        if expected['calculated_checks_pass']:passing.append(row);solutions[row['id']]=(fresh,data)
    if shared.unresolved_preference(records,passing) or not passing:raise ProjectError('No confirmed preferred fan reconstructed')
    chosen=min(passing,key=lambda row:(row['preference'],row['id']));selection=result['selected']
    if result.get('objective')!=shared.OBJECTIVE or result.get('tie_break')!='lexical candidate ID' or any(selection.get(k)!=chosen[k] for k in ('id','source','preference')):
        raise ProjectError('Selected fan is not the original preferred eligible candidate')
    curve=producer/'selected/curve.json';fresh,data=solutions[chosen['id']];saved=read_json(producer/'selected/operating/fan.json')
    if read_json(curve)!=chosen['curve'] or read_json(producer/'selected/operating/operating-network.json')!=data or any(saved.get(k)!=fresh.get(k) for k in ('status','checks','operating_point','calculated_checks_pass')):
        raise ProjectError('Selected curve or operating scenario differs from reconstruction')
    analysis=read_json(producer/'selected/operating/analysis/network.json')
    if any(analysis.get(k)!=fresh['network_analysis'].get(k) for k in ('segments','nodes','supply_flow_m3_s','calculated_checks_pass')):
        raise ProjectError('Selected saved network analysis differs from fresh solve')
    if selection.get('rerun',{}).get('operating_point')!=fresh['operating_point'] or selection.get('rerun',{}).get('calculated_checks_pass') is not True:
        raise ProjectError('Selected rerun summary changed')
    if digest(path)!=before or any(digest(Path(p))!=sha for p,sha in {**inputs,**result['method_inputs']}.items()) or any(digest(producer/name)!=sha for name,sha in artifacts.items()):
        raise ProjectError('Selection source or artifact changed during handoff')
    return curve


def run_selected(producer,pressure,catalogue,out):
    producer,pressure,catalogue,out=[Path(p).resolve() for p in (producer,pressure,catalogue,out)]
    if not allowed(out) or producer==out or producer in out.parents or out in producer.parents:
        raise ProjectError('Independent consumer must stay outside immutable selection folder')
    curve=selected_input(producer,pressure,catalogue);report_path=producer/'fan-selection.json';selection=read_json(report_path)
    pins={**selection['inputs'],**selection['method_inputs'],str(report_path):digest(report_path)}
    result=circular_fan.run(pressure,curve,out)
    if selected_input(producer,pressure,catalogue)!=curve or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ProjectError('Selected fan lineage changed during independent consumer')
    for path,sha in selection['inputs'].items():
        if path in result['inputs'] and result['inputs'][path]!=sha:raise ProjectError('Selected fan source hash conflict')
        result['inputs'][path]=sha
    result['inputs'][str(report_path)]=pins[str(report_path)]
    result['method_inputs'].update(selection['method_inputs'])
    result['selection']=dict(producer=str(producer),id=selection['selected']['id'],preference=selection['selected']['preference'],catalogue=str(catalogue))
    (out/'fan.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('pressure',type=Path);parser.add_argument('--catalogue',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();r=run(args.pressure,args.catalogue,args.out);print(json.dumps({k:r[k] for k in ('status','selected','calculated_checks_pass','design_accepted')},indent=2));raise SystemExit(0 if r['calculated_checks_pass'] else 2)
