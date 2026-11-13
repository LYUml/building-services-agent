"""Compose the verified upstream writer with an inherited workflow producer."""
import json
from pathlib import Path
from . import autocad_schedule
from .cli import digest


def semantic_schedule(value):
    return {k:v for k,v in value.items() if k!='allocation_input'}


def run(plan, task, inherited_schedule, inherited_sha256, out):
    plan=Path(plan).resolve();out=Path(out).resolve()
    data=json.loads(plan.read_text());tasks={t['id']:t for t in data['tasks']}
    producer=tasks[task['depends_on']];root=plan.parent
    inherited_schedule=Path(inherited_schedule).resolve()
    if digest(inherited_schedule)!=inherited_sha256:
        raise ValueError('Inherited schedule producer changed')
    inherited=json.loads(inherited_schedule.read_text())
    if inherited['status']!='pass':raise ValueError('Passing inherited schedule required')
    allocation=tasks[producer['depends_on']]['project'] if producer.get('depends_on') else None
    record=autocad_schedule.run(root/task['drawing'],root/producer['project'],root/task['binding'],out,
        allocation_project=root/allocation if allocation else None,original_plan=plan)
    if record['status']!='written':raise ValueError(record.get('error','Upstream writer failed'))
    if digest(inherited_schedule)!=inherited_sha256:raise ValueError('Inherited schedule producer changed')
    if semantic_schedule(inherited)!=semantic_schedule(json.loads((out/'schedule/results.json').read_text())):
        raise ValueError('Upstream writer calculation differs from inherited schedule')
    binding=dict(plan=str(plan),plan_sha256=digest(plan),task=task['id'],schedule=str(inherited_schedule),schedule_sha256=inherited_sha256)
    (out/'workflow-binding.json').write_text(json.dumps(binding,indent=2),encoding='utf-8')
    verify(out)
    return record


def verify(out):
    out=Path(out).resolve();binding=json.loads((out/'workflow-binding.json').read_text())
    plan=Path(binding['plan']);schedule=Path(binding['schedule'])
    if digest(plan)!=binding['plan_sha256'] or digest(schedule)!=binding['schedule_sha256']:
        raise ValueError('Inherited workflow source changed')
    data=json.loads(plan.read_text());tasks={t['id']:t for t in data['tasks']};task=tasks[binding['task']]
    if task['kind']!='duct_sheet' or task.get('writer')!='uc4n':raise ValueError('Upstream writer task differs')
    producer=tasks[task['depends_on']]
    if schedule!=out.parent/producer['id']/'results.json':raise ValueError('Inherited producer location differs')
    record=json.loads((out/'schedule-drawing.json').read_text());root=plan.parent
    allocation=tasks[producer['depends_on']]['project'] if producer.get('depends_on') else None
    wanted=dict(source=str((root/task['drawing']).resolve()),project=str((root/producer['project']).resolve()),
        binding=str((root/task['binding']).resolve()),original_plan=str(plan),
        allocation_project=str((root/allocation).resolve()) if allocation else None)
    if any(record.get(k)!=v for k,v in wanted.items()):raise ValueError('Writer sources differ from workflow')
    if semantic_schedule(json.loads(schedule.read_text()))!=semantic_schedule(json.loads((out/'schedule/results.json').read_text())):
        raise ValueError('Writer differs from inherited calculation')
    return autocad_schedule.verify(out)
