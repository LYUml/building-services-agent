"""Bridge the common allocation provider into existing downstream file contracts."""
import json
import os
from pathlib import Path
from .cli import digest
from .modules import run as run_module, verify_result

PROVIDER='bsa.classified-air-allocation'


def request(project, destination):
    project=Path(project).resolve()
    return dict(schema='bsa.module-request/1',project_id='workflow-allocation',scenario_id='declared-planar-design',
        capability='analysis.air.classified-allocation',
        coordinate_frame=dict(id='declared-allocation-planar-metres',kind='source-world-si',length_unit='m',georeferenced=False),
        sources=dict(project=dict(path=os.path.relpath(project,Path(destination).parent),sha256=digest(project))))


def run(project, folder, *, disabled=False):
    folder=Path(folder).resolve()
    if folder.exists():raise ValueError('New allocation module task directory required')
    folder.mkdir(parents=True)
    path=folder/'request.json'
    path.write_text(json.dumps(request(project,path),indent=2),encoding='utf-8')
    result=run_module(path,PROVIDER,folder/'module',disabled=disabled)
    verify_result(folder/'module/result.json')
    if result['execution']['status']=='completed':
        source=folder/'module'/result['payload']['report']['path']
        (folder/'allocation.json').write_bytes(source.read_bytes())
    return result


def verify(project, folder, disabled, status=None):
    folder=Path(folder).resolve()
    if json.loads((folder/'request.json').read_text(encoding='utf-8'))!=request(project,folder/'request.json'):
        raise ValueError('Allocation module request differs from original workflow project')
    result=verify_result(folder/'module/result.json')
    if result['provider']['id']!=PROVIDER:raise ValueError('Allocation provider identity differs')
    recorded=any(d['code']=='provider_disabled' for d in result['execution']['diagnostics'])
    if recorded!=disabled:raise ValueError('Allocation provider disable state differs')
    expected={'completed':'pass','failed':'fail','unavailable':'pending','pending':'pending'}[result['execution']['status']]
    if status is not None and status!=expected:raise ValueError('Allocation workflow status differs from module result')
    exported=folder/'allocation.json'
    if expected=='pass':
        if exported.read_bytes()!=(folder/'module'/result['payload']['report']['path']).read_bytes():
            raise ValueError('Downstream allocation export differs from verified module artifact')
    elif exported.exists():raise ValueError('Unexecuted allocation cannot export downstream evidence')
    return result
