"""Typed primary-input differences using the existing ownership/unit mapper."""
import shutil
import hashlib
import json
from pathlib import Path

from ..engineering_data.inputs import project_parameters,numeric_leaves
from ..module_contract import read_json,validate
from ..source_refs import file_hash,reference
from ..workspace import ROOT,allowed,project_root

PROVIDERS={'bsa.classified-air-allocation','bsa.single-phase-circuits'}


def view(row,notes):
    if row is None:return None
    result=dict(row)
    text=result['source_text']
    if len(text)>2000:
        if text not in notes:notes[text]=hashlib.sha256(text.encode('utf-8')).hexdigest()
        result.update(source_text=None,source_text_omitted=True,source_text_length=len(text),source_text_sha256=notes[text])
    return result


def paths(task_id):
    return 'request-'+task_id+'.json','project-'+task_id+'.json'


def primary(request_path,request):
    name=request['sources']['project']['path']
    if not isinstance(name,str) or Path(name).is_absolute():raise ValueError('Relative primary project source required')
    path=(Path(request_path).parent/name).resolve()
    if not allowed(path):raise ValueError('Primary parameter source outside selected workspace')
    return path


def capture(result,task_id,folder):
    request_path=Path(result['request']['path']).resolve()
    request=read_json(request_path);project=primary(request_path,request)
    if file_hash(request_path)!=result['request']['sha256'] or file_hash(project)!=request['sources']['project']['sha256'] or result['inputs'].get(str(project))!=file_hash(project):
        raise ValueError('Parameter snapshot differs from verified module source')
    for source,name in zip((request_path,project),paths(task_id)):
        shutil.copyfile(source,Path(folder)/name)


def archived(folder,task_id,result):
    request_name,project_name=paths(task_id)
    request_path=Path(folder)/request_name;project_path=Path(folder)/project_name
    request=read_json(request_path)
    if file_hash(request_path)!=result['request']['sha256']:
        raise ValueError('Archived parameter request differs from original module')
    original=primary(result['request']['path'],request)
    expected=request['sources']['project']['sha256']
    if file_hash(project_path)!=expected or result['inputs'].get(str(original))!=expected:
        raise ValueError('Archived parameters differ from original primary source')
    return request,read_json(project_path),original


def logical(path,sha):
    path=Path(path).resolve();project=project_root()
    if not allowed(path):raise ValueError('Declared source location outside selected workspace')
    root=project if project is not None and path.is_relative_to(project) else ROOT
    return dict(workspace='project' if root==project else 'tool',path=path.relative_to(root).as_posix(),sha256=sha)


def compare(folder,task_id,result,current_task,current_root,*,offset=0,limit=50):
    info=dict(scope='Primary declared source inputs only; not predicted performance or current producer execution',
              source_assertions_authenticated=False,current_producer_executed=False,design_accepted=False)
    try:
        old_request,before,old_path=archived(folder,task_id,result)
        if current_task.get('kind')!='module_analysis' or current_task.get('depends_on') or current_task.get('provider') not in PROVIDERS:
            return dict(info,status='not_comparable',reason='Current task lacks a supported direct primary-input adapter')
        from ..workflow import local_path
        request_path=local_path(current_root,current_task.get('request'))
        request=validate(read_json(request_path),'bsa.module-request/1')
        if request['project_id']!=result['project_id'] or request['capability']!=old_request['capability']:
            return dict(info,status='not_comparable',reason='Different project identity or input capability; values are not aligned')
        project=primary(request_path,request)
        after_ref=reference(project);request_ref=reference(request_path)
        if after_ref['sha256']!=request['sources']['project']['sha256']:
            raise ValueError('Current primary source no longer matches its request')
        after=read_json(project)
        old_rows,old_coverage=project_parameters(before,result['project_id'],result['payload_schema'])
        new_rows,new_coverage=project_parameters(after,request['project_id'],result['payload_schema'])
        a={r['id']:r for r in old_rows};b={r['id']:r for r in new_rows}
        if len(a)!=len(old_rows) or len(b)!=len(new_rows):raise ValueError('Duplicate source parameter identity')
        changes=[];notes={}
        for identity in sorted(set(a)|set(b),key=lambda key:((a.get(key) or b[key])['name'],key)):
            old,new=a.get(identity),b.get(identity)
            if old==new:continue
            kinds=[]
            if old is None:kinds=['added']
            elif new is None:kinds=['removed']
            else:
                for fields,label in ((('value',),'value_changed'),(('unit','dimension','si_unit'),'unit_changed'),(('classification',),'classification_changed'),(('source_pointer',),'location_changed')):
                    if any(old['quantity'][k]!=new['quantity'][k] for k in fields):kinds.append(label)
                if any(old[k]!=new[k] for k in ('source_text','source_note_pointer')):kinds.append('source_note_changed')
            comparable=old is not None and new is not None and all(old['quantity'][k]==new['quantity'][k] for k in ('dimension','si_unit'))
            changes.append(dict(id=identity,entity_id=(old or new)['entity_id'],name=(old or new)['name'],kinds=kinds,
                before=view(old,notes),after=view(new,notes),delta_si=new['quantity']['si_value']-old['quantity']['si_value'] if comparable else None,
                delta_si_unit=old['quantity']['si_unit'] if comparable else None))
        unmapped=set(old_coverage['unmapped_numeric_pointers'])|set(new_coverage['unmapped_numeric_pointers'])
        old_leaves,new_leaves=numeric_leaves(before),numeric_leaves(after)
        gaps=[dict(pointer=p,before=old_leaves.get(p),after=new_leaves.get(p),unit=None,classification='unmapped') for p in sorted(unmapped) if old_leaves.get(p)!=new_leaves.get(p)]
        if file_hash(project)!=after_ref['sha256'] or file_hash(request_path)!=request_ref['sha256']:
            raise ValueError('Current input changed during parameter comparison')
        response=dict(info,status='compared',before_source=logical(old_path,old_request['sources']['project']['sha256']),
            before_snapshot=reference(Path(folder)/paths(task_id)[1]),
            after_source=after_ref,current_request=request_ref,before_scenario=result['scenario_id'],after_scenario=request['scenario_id'],
            total_changes=len(changes),offset=offset,limit=limit,changes=changes[offset:offset+limit],has_more=offset+limit<len(changes),
            unmapped_numeric_change_count=len(gaps),unmapped_numeric_changes=gaps[offset:offset+limit],unmapped_has_more=offset+limit<len(gaps))
        if len(json.dumps(response,ensure_ascii=False,allow_nan=False).encode('utf-8'))>1_000_000:
            return dict(info,status='page_too_large',total_changes=len(changes),reason='Reduce parameter page size; full sources remain in the checkpoint and current project')
        return response
    except (ValueError,OSError,KeyError,TypeError) as exc:
        return dict(info,status='extraction_unavailable',reason=str(exc))
