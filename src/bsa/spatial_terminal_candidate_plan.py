"""Materialize an explicitly studied terminal candidate as a new full workflow plan."""
import argparse
import copy
import json
from pathlib import Path
import shutil
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from . import spatial_terminal_revision as revision
from . import spatial_terminal_performance as performance
from .workflow import validate_plan
from .delivery import context


def geometry_transfer(original,root,study,candidate,task,policy):
    """Explicitly reuse declared geometry as new design choices, never measurements."""
    if policy is None:return {},{},{}
    policy=Path(policy).resolve()
    if not allowed(policy):raise ValueError('Selected geometry transfer policy required')
    spec=read_json(policy)
    if not isinstance(spec,dict) or set(spec)!={'source','classification','from_terminal_by_room'} or not isinstance(spec['source'],str) or not spec['source'].strip() or spec['classification']!='design_choice' or not isinstance(spec['from_terminal_by_room'],dict):raise ValueError('Explicit source-classified geometry transfer design choice required')
    before=read_json(Path(study['original']));old=read_json(Path(before['allocation_result']))['calculation']['rooms']
    current_path=Path(candidate)/'allocation/terminal-allocation.json';current=read_json(current_path)['calculation']['rooms']
    if set(old)!=set(current) or set(spec['from_terminal_by_room'])!=set(current):raise ValueError('Geometry policy must cover exact source rooms')
    for guid,terminal in spec['from_terminal_by_room'].items():
        if terminal not in {row['id'] for row in old[guid]['allocation']['terminals']}:raise ValueError('Geometry template must belong to the same original room')
    pins={str(policy):digest(policy),str(current_path.resolve()):digest(current_path)};transfers={};bindings={};chain={task}
    for row in original['tasks']:
        if row.get('depends_on') not in chain:continue
        chain.add(row['id'])
        if row['kind'] not in ('spatial_terminal_ifc','spatial_terminal_inlets','spatial_terminal_stubs'):continue
        source=(Path(root)/row['basis']).resolve()
        if not allowed(source):raise ValueError('Selected original geometry basis required')
        basis=read_json(source);pins[str(source)]=digest(source);new={};links={}
        for guid,room in current.items():
            ancestor=spec['from_terminal_by_room'][guid]
            if ancestor not in basis:raise ValueError('Original geometry template is missing')
            record=basis[ancestor]
            if not isinstance(record,dict) or not record:raise ValueError('Nonempty declared geometry record required')
            for terminal in room['allocation']['terminals']:
                values={}
                for key,quantity in record.items():
                    if not isinstance(quantity,dict) or not isinstance(quantity.get('source'),str) or not quantity['source'].strip() or quantity.get('classification') not in ('given','measured','assumed','secondary_transcription','design_choice'):raise ValueError('Original geometry quantity must retain source/classification')
                    anchor='shared system '+quantity['id'] if key=='system' else ancestor
                    values[key]=dict(copy.deepcopy(quantity),classification='design_choice',source=spec['source']+'; explicit reuse from '+anchor+'; original '+quantity['classification']+': '+quantity['source'])
                new[terminal['id']]=values;links[terminal['id']]=dict(from_terminal=ancestor,original_basis=copy.deepcopy(record))
        transfers[row['id']]=dict(filename='geometry-'+str(len(transfers)+1)+'.json',basis=new);bindings[row['id']]=links
    if not transfers:raise ValueError('Geometry transfer policy has no supported downstream tasks')
    return transfers,bindings,pins


def run(plan,candidate,task,target,geometry_policy=None):
    plan,candidate,target=[Path(p).resolve() for p in (plan,candidate,target)]
    folder=target.parent/(target.stem+'-inputs');manifest=target.with_suffix('.provenance.json')
    if not all(allowed(p) for p in (plan,candidate,target)) or target.parent!=plan.parent or target.suffix!='.json' or any(p.exists() for p in (target,folder,manifest)):raise ValueError('New same-directory plan and fresh candidate input/provenance paths required')
    before=digest(plan);original,_=validate_plan(plan);study=revision.verify(candidate)
    tasks={row['id']:row for row in original['tasks']}
    if task not in tasks or tasks[task]['kind']!='spatial_terminal_performance':raise ValueError('Explicit original spatial performance task required')
    source=Path(study['original'])
    if source!=source.parent.parent/task/'terminal-performance.json':raise ValueError('Candidate original does not match selected workflow task')
    context(plan,source.parent.parent)
    parent=tasks[task]['depends_on'];new=copy.deepcopy(original)
    pins=dict(study['inputs']);pins[str(plan)]=before;pins[str(candidate/'candidate-comparison.json')]=digest(candidate/'candidate-comparison.json');pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    transfers,bindings,extra=geometry_transfer(original,plan.parent,study,candidate,task,geometry_policy);pins.update(extra)
    folder.mkdir();basis=folder/'terminal-basis.json';shutil.copyfile(study['basis'],basis)
    selected,_=performance.selections(Path(study['products']));products={};copies={}
    for name,row in selected.items():
        old_setting=(Path(study['products']).parent/row['selection']['settings']).resolve()
        if old_setting not in copies:
            sub=folder/('product-'+str(len(copies)+1));sub.mkdir();spec=row['settings'];shutil.copyfile(old_setting,sub/'settings.json')
            for role in ('source','catalogue'):
                destination=sub/spec[role];destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old_setting.parent/spec[role],destination)
            copies[old_setting]=(sub/'settings.json').relative_to(folder).as_posix()
        products[name]=dict(row['selection'],settings=copies[old_setting])
    product_file=folder/'products.json';product_file.write_text(json.dumps(products,indent=2),encoding='utf-8')
    for row in new['tasks']:
        if row['id']==parent:row['basis']=basis.relative_to(target.parent).as_posix()
        if row['id']==task:row['basis']=product_file.relative_to(target.parent).as_posix()
        if row['id'] in transfers:
            item=transfers[row['id']];path=folder/item['filename'];path.write_text(json.dumps(item['basis'],indent=2),encoding='utf-8');row['basis']=path.relative_to(target.parent).as_posix()
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Original plan or candidate changed during materialization')
    target.write_text(json.dumps(new,indent=2),encoding='utf-8');validate_plan(target)
    result=dict(original_plan=str(plan),candidate=str(candidate),task=task,target=str(target),inputs=pins,
        outputs={str(p):digest(p) for p in [target,*folder.rglob('*')] if p.is_file()},
        requirements_preserved=new['requirements']==original['requirements'],design_accepted=False,
        scope='New complete workflow plan only;execute and review all original requirements. Prior manual acceptance is not transferred')
    if geometry_policy is not None:result.update(geometry_policy=str(Path(geometry_policy).resolve()),geometry_bindings=bindings)
    manifest.write_text(json.dumps(result,indent=2),encoding='utf-8');verify(target);return result


def verify(target):
    target=Path(target).resolve()
    if not allowed(target):raise ValueError('Selected candidate plan required')
    result=read_json(target.with_suffix('.provenance.json'))
    fields={'original_plan','candidate','task','target','inputs','outputs','requirements_preserved','design_accepted','scope'}
    if 'geometry_policy' in result:fields.update(('geometry_policy','geometry_bindings'))
    if set(result)!=fields or result['target']!=str(target) or result['design_accepted'] is not False or result['requirements_preserved'] is not True:raise ValueError('Exact unaccepted plan provenance required')
    plan=Path(result['original_plan']);candidate=Path(result['candidate'])
    if not all(allowed(p) for p in (plan,candidate)) or plan.parent!=target.parent:raise ValueError('Selected same-directory original plan required')
    study=revision.verify(candidate);original,_=validate_plan(plan);tasks={row['id']:row for row in original['tasks']};task=result['task']
    if task not in tasks or tasks[task]['kind']!='spatial_terminal_performance':raise ValueError('Original performance task differs')
    source=Path(study['original'])
    if source!=source.parent.parent/task/'terminal-performance.json':raise ValueError('Original workflow task differs')
    context(plan,source.parent.parent)
    pins=dict(study['inputs']);pins[str(plan)]=digest(plan);pins[str(candidate/'candidate-comparison.json')]=digest(candidate/'candidate-comparison.json');pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    transfers,bindings,extra=geometry_transfer(original,plan.parent,study,candidate,task,result.get('geometry_policy'));pins.update(extra)
    if result.get('geometry_bindings',{})!=bindings:raise ValueError('Geometry transfer provenance differs')
    folder=target.parent/(target.stem+'-inputs')
    outputs={str(p):digest(p) for p in [target,*folder.rglob('*')] if p.is_file()}
    if result['inputs']!=pins or result['outputs']!=outputs or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Candidate plan source/output pins differ')
    expected=copy.deepcopy(original)
    for row in expected['tasks']:
        if row['id']==tasks[task]['depends_on']:row['basis']=(folder/'terminal-basis.json').relative_to(target.parent).as_posix()
        if row['id']==task:row['basis']=(folder/'products.json').relative_to(target.parent).as_posix()
        if row['id'] in transfers:
            item=transfers[row['id']];path=folder/item['filename'];row['basis']=path.relative_to(target.parent).as_posix()
            if read_json(path)!=item['basis']:raise ValueError('Transferred geometry differs from declared source replay')
    if read_json(target)!=expected:raise ValueError('Candidate plan changed original requirements/tasks')
    if read_json(folder/'terminal-basis.json')!=read_json(Path(study['basis'])):raise ValueError('Candidate geometry basis differs')
    original_products,_=performance.selections(Path(study['products']));copied,_=performance.selections(folder/'products.json')
    def semantic(rows):
        return {name:dict(catalogue=row['catalogue'],settings={k:v for k,v in row['settings'].items() if k not in ('source','catalogue')},selection={k:v for k,v in row['selection'].items() if k!='settings'}) for name,row in rows.items()}
    if semantic(original_products)!=semantic(copied):raise ValueError('Candidate products differ from study')
    validate_plan(target);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan');parser.add_argument('candidate');parser.add_argument('--task',required=True);parser.add_argument('--target',required=True);parser.add_argument('--geometry-policy')
    args=parser.parse_args();run(args.plan,args.candidate,args.task,args.target,args.geometry_policy)
