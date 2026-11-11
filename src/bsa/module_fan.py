"""Reuse the existing native fan intersection with explicit common-budget inputs."""
import json
from pathlib import Path
from .cli import digest
from .workflow_modules import bound_air_context
from .module_contract import read_json


def run(producer,curve,out):
    from .rectangular_fan_binding import run as solve
    producer,curve,out=[Path(p).resolve() for p in (producer,curve,out)]
    files,result=bound_air_context(producer)
    methods=[Path(__file__),*[Path(__file__).with_name(n) for n in ('rectangular_fan_binding.py','rectangular_fan.py','pump.py','rectangular_binding.py','rectangular_network.py','network.py')]]
    pins={str(p):digest(p) for p in [producer,curve,*methods]};pins.update(result['inputs'])
    if out.exists() or any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('New fan output separate from source inputs required')
    payload=solve(*(files[k] for k in ('project','model','binding','ifc','analysis')),curve,out)
    after,verified=bound_air_context(producer)
    if after!=files or verified!=result or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Common budget/fan sources changed during solve')
    payload['inputs'].update(pins)
    payload['module_parent']=dict(path=str(producer),sha256=digest(producer),payload_schema=result['payload_schema'])
    payload['module_curve']=dict(path=str(curve),sha256=digest(curve))
    (out/'fan.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    verify(out)
    return payload


def verify(folder):
    from .rectangular_fan import solve
    from .rectangular_network import calculate
    folder=Path(folder);data=read_json(folder/'fan.json')
    try:
        parent=data['module_parent'];curve=data['module_curve']
        if any(digest(Path(p))!=sha for p,sha in data['inputs'].items()):raise ValueError('Fan source/method evidence changed')
        if data['inputs'].get(parent['path'])!=parent['sha256'] or data['inputs'].get(curve['path'])!=curve['sha256']:raise ValueError('Fan source identity differs')
        files,result=bound_air_context(parent['path'])
        if parent['payload_schema']!=result['payload_schema'] or digest(Path(parent['path']))!=parent['sha256']:raise ValueError('Fan producer correspondence differs')
        curve_data=read_json(curve['path'])
        if data['curve']!=curve_data:raise ValueError('Fan curve changed')
        if data.get('geometry_bound') is not True or data.get('native_path_correspondence_pass') is not True or data.get('design_accepted') is not False or data.get('ifc_sha256')!=digest(files['ifc']):raise ValueError('Fan native scope correspondence differs')
        expected,selected=solve(read_json(files['project']),curve_data)
        rerun=False
        if selected is not None:
            operating=folder/'operating-network.json'
            if read_json(operating)!=selected:raise ValueError('Fan operating network differs from inherited-source replay')
            fresh=calculate(selected);saved=read_json(folder/'analysis/network.json');rerun=fresh['calculated_checks_pass']
            if saved['input_sha256']!=digest(operating) or saved['calculated_checks']!=fresh['calculated_checks'] or any(saved[k]!=fresh[k] for k in ('supply_flow_m3_s','required_source_total_pressure_pa')):raise ValueError('Fan selected rerun differs')
        if any(data.get(k)!=expected.get(k) for k in ('status','operating_point','trace','checks','design_flow_m3_s','flow_bracket_m3_s')) or data['calculated_checks_pass']!=(expected['calculated_checks_pass'] and rerun) or data['selected_rerun_pass']!=rerun:raise ValueError('Fan result differs from inherited-source replay')
        return data
    except (OSError,KeyError,TypeError,ValueError) as exc:raise ValueError('Invalid module fan evidence: '+str(exc)) from exc
