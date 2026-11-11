"""Inherit verified neutral box geometry into the existing annual thermal input."""
import copy
import json
from pathlib import Path
from .cli import digest
from .module_contract import read_json
from .modules import verify_result
from .thermal_binding import validate_contract
from .annual_energy import validate
from .thermal_geometry import boxes,adjacency


def prepare(module_result,template,binding):
    if module_result['execution']['status']!='completed' or module_result['payload_schema']!='bsa.spatial-boxes/1':raise ValueError('Completed neutral box-space producer required')
    if set(binding)!={'source','spaces','north_axis_deg'}:raise ValueError('Thermal mapping requires explicit source,space IDs and north axis;equipment binding unsupported')
    validate_contract(template,binding)
    payload=module_result['payload'];source={row['id']:row for row in payload['spaces']}
    if len(source)!=len(binding['spaces']) or set(source)!={r['guid'] for r in binding['spaces']}:raise ValueError('Thermal mapping must cover every neutral space exactly')
    rows=[dict(id=r['id'],source=r['source']+'; inherited neutral space '+r['guid'],origin_m=source[r['guid']]['origin_m'],size_m=source[r['guid']]['size_m']) for r in binding['spaces']]
    boxes(dict(spaces=rows))
    guids={r['id']:r['guid'] for r in binding['spaces']}
    def contacts(values,mapping):return sorted((tuple(sorted(mapping[v] for v in r['spaces'])),r['axis'],round(r['area_m2'],9)) for r in values)
    if contacts(adjacency(rows),guids)!=contacts(payload['contacts'],{k:k for k in source}):raise ValueError('Inherited contact geometry differs')
    project=copy.deepcopy(template);project['building']['spaces']=rows;project['building']['north_axis_deg']=binding['north_axis_deg'];validate(project)
    return project


def run(result_path,template_path,binding_path,out):
    result_path,template_path,binding_path,out=[Path(p).resolve() for p in (result_path,template_path,binding_path,out)]
    result=verify_result(result_path)
    paths=[result_path,template_path,binding_path,Path(__file__),Path(__file__).with_name('thermal_binding.py'),Path(__file__).with_name('thermal_geometry.py'),Path(__file__).with_name('annual_energy.py')]
    pins={str(p):digest(p) for p in paths};pins.update(result['inputs'])
    if out.exists() or any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('New thermal output separate from sources required')
    project=prepare(result,read_json(template_path),read_json(binding_path))
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Thermal inheritance source changed')
    out.mkdir(parents=True)
    (out/'bound-project.json').write_text(json.dumps(project,indent=2),encoding='utf-8')
    report=dict(inputs=pins,producer_result=str(result_path),template=str(template_path),binding=str(binding_path),producer_result_sha256=digest(result_path),coordinate_frame=result['payload']['coordinate_frame'],
        mapping=read_json(binding_path)['spaces'],space_count=len(project['building']['spaces']),geometry_inherited=True,
        preparation_pass=True,simulation_executed=False,design_accepted=False,
        scope='Annual input preparation only;actual thermal boundaries,construction,weather,systems and simulation acceptance remain separate')
    verify_result(result_path)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Thermal inheritance source changed during write')
    report['artifacts']={'bound-project.json':digest(out/'bound-project.json')}
    (out/'inheritance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def verify(folder):
    folder=Path(folder);report=read_json(folder/'inheritance.json')
    for name,sha in report['inputs'].items():
        if digest(Path(name))!=sha:raise ValueError('Inherited thermal source changed')
    if report['artifacts']!={'bound-project.json':digest(folder/'bound-project.json')}:raise ValueError('Inherited thermal project changed')
    expected=prepare(verify_result(report['producer_result']),read_json(report['template']),read_json(report['binding']))
    if read_json(folder/'bound-project.json')!=expected:raise ValueError('Inherited thermal project correspondence differs')
    return report
