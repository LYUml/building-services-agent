"""Source-calculated duct schedules written with a pinned upstream DXF backend."""
import argparse
import json
import importlib.metadata
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import ezdxf
from . import air_allocation,duct_schedule,duct_sheet,duct_sheet_native,duct_equivalent,air_load,service_areas,air_tree_flow,native_cad,cad_sheet
from .autocad_source import local,UPSTREAM,COMMIT
from . import autocad_source,cad_intake,workspace
from .cli import digest
from .workspace import ROOT,project_root

WORKER=ROOT/'scripts/write_uc4n_schedule.py'
SCOPE='Fresh source calculations and bounded table/flow-arrow writing; original assignment and engineering/visual gaps remain'
CONTROLS=[air_allocation,duct_schedule,duct_sheet,duct_sheet_native,duct_equivalent,air_load,service_areas,air_tree_flow,native_cad,cad_sheet,autocad_source,cad_intake,workspace]


def blocks(doc):
    from ezdxf.lldxf.tagwriter import TagCollector
    return {b.name:[repr(TagCollector.dxftags(e)) for e in b] for b in doc.blocks if not b.name.upper().startswith(('*MODEL_SPACE','*PAPER_SPACE'))}


def source_files(source,project,binding,allocation_project,native_settings,autocad,original_plan):
    files=[Path(p).resolve() for p in [source,project,binding,allocation_project,native_settings,original_plan] if p is not None]
    if allocation_project:
        path=Path(allocation_project).resolve();data=json.loads(path.read_text())
        files.extend([local(path.parent/data['boundary']),*map(local,air_allocation.reference_files(path,data))])
    files.extend([Path(__file__),WORKER,*[Path(m.__file__) for m in CONTROLS]])
    if autocad is not None:files.append(Path(autocad).resolve())
    return set(p.resolve() for p in files)


def papers(doc):
    from ezdxf.lldxf.tagwriter import TagCollector
    return {p.name:[repr(TagCollector.dxftags(e)) for e in p] for p in doc.layouts if p.name!='Model'}


def correspondence(source,expected,target,layers):
    original,reference,saved=[ezdxf.readfile(p) for p in (source,expected,target)]
    old=duct_sheet.snapshot(original);wanted=duct_sheet.snapshot(reference);actual=duct_sheet.snapshot(saved)
    if len(actual)!=len(wanted) or any(actual.get(h)!=wanted[h] for h in old) or blocks(original)!=blocks(saved) or papers(original)!=papers(saved):raise ValueError('Original drawing or approved edit inventory differs')
    return duct_sheet_native.compare(expected,target,layers)


def run(source,project,binding,out,*,allocation_project=None,native_settings=None,autocad=None,original_plan=None):
    source,project,binding,out=local(source),local(project),local(binding),local(out,True)
    extra=[local(p) for p in [allocation_project,native_settings,original_plan] if p is not None]
    if out.exists() or any(out==p or out in p.parents for p in [source,project,binding,*extra]) or source.suffix.lower()!='.dxf':raise ValueError('Fresh output separate from project sources required')
    if (native_settings is None)!=(autocad is None):raise ValueError('Native settings and explicit host AutoCAD are paired')
    files=source_files(source,project,binding,allocation_project,native_settings,autocad,original_plan)
    pins={str(p):digest(p) for p in files};out.mkdir(parents=True)
    result=dict(schema='bsa.autocad-schedule/1',scope=SCOPE,source=str(source),project=str(project),binding=str(binding),allocation_project=str(Path(allocation_project).resolve()) if allocation_project else None,native_settings=str(Path(native_settings).resolve()) if native_settings else None,autocad=str(Path(autocad).resolve()) if autocad else None,original_plan=str(Path(original_plan).resolve()) if original_plan else None,inputs=pins,design_accepted=False,native_reopen_pass=False,plot_visual_review='pending',status='failed')
    try:
        allocation_path=None
        if allocation_project:
            air_allocation.run(allocation_project,out/'allocation');allocation_path=out/'allocation/allocation.json'
        options=dict(allocation_path=allocation_path,allocation_sha256=digest(allocation_path)) if allocation_path else {}
        schedule=duct_schedule.run(project,out/'schedule',**options)
        if schedule['status']!='pass':raise ValueError('Required original section checks failed')
        study=out/'schedule/results.json'
        checked=duct_sheet.run(source,study,binding,out/'reference',inherited_schedule_sha256=digest(study))
        expected=out/'reference/Supply Air Distribution.dxf';reference=ezdxf.readfile(expected);original=ezdxf.readfile(source)
        spec=json.loads(binding.read_text());edits=[dict(handle=c['handle'],before=c['expected_text'],text=reference.entitydb[c['handle']].dxf.text) for row in spec['sections'].values() for c in row['cells']]
        arrow_layer=spec.get('flow_arrows',{}).get('layer');arrows=[dict(start=list(e.dxf.start),end=list(e.dxf.end)) for e in reference.modelspace() if arrow_layer and e.dxf.layer==arrow_layer]
        target=out/'Supply Air Distribution.dxf'
        request=dict(source=str(source),source_sha256=digest(source),target=str(target),edits=edits,arrow_layer=arrow_layer,arrows=arrows)
        request_path=out/'writer-request.json';request_path.write_text(json.dumps(request,indent=2),encoding='utf-8')
        temp=out/'temp';temp.mkdir();env={**os.environ,'BSA_PROJECT_ROOT':str(project_root() or ROOT),'CAD_LAUNCH':'never','ALLOWED_PATHS':str(project_root() or ROOT),'TEMP':str(temp),'TMP':str(temp)}
        completed=subprocess.run([sys.executable,'-X','utf8',str(WORKER),str(request_path)],cwd=ROOT,env=env,text=True,encoding='utf-8',capture_output=True)
        (out/'writer.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
        result['worker_returncode']=completed.returncode
        if completed.returncode:raise ValueError('Pinned upstream writing failed; inspect writer.log')
        layers=json.loads(Path(native_settings).read_text())['layers'] if native_settings else sorted({original.entitydb[e['handle']].dxf.layer for e in edits}|({arrow_layer} if arrows else set()))
        comparison=correspondence(source,expected,target,layers)
        result.update(status='written',sections=len(schedule['sections']),bound_cells=len(edits),changed_cells=sum(e['before']!=e['text'] for e in edits),arrow_lines=len(arrows),upstream_commit=COMMIT,layers=layers,comparison=comparison,original_blocks_preserved=True,original_modelspace_preserved_except_bound_cells=True)
        if original_plan:
            plan=json.loads(Path(original_plan).read_text());result.update(original_requirements=plan['requirements'],original_unresolved_inputs=plan.get('unresolved_inputs',[]))
        if native_settings:
            native=duct_sheet_native.run(target,native_settings,out/'native',autocad,inherited_source_sha256=digest(target))
            result['native_reopen_pass']=native['native_reopen_pass'];result['native_plot']=native['plot']
    except Exception as exc:result.update(status='failed',error=type(exc).__name__+': '+str(exc))
    result['inputs_unchanged']=all(Path(p).is_file() and digest(Path(p))==sha for p,sha in pins.items())
    if not result['inputs_unchanged']:result['status']='source_changed'
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'schedule-drawing.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def verify(out):
    out=local(out);record=json.loads((out/'schedule-drawing.json').read_text())
    if record.get('schema')!='bsa.autocad-schedule/1' or record.get('scope')!=SCOPE or record.get('status')!='written' or record.get('worker_returncode')!=0 or record.get('inputs_unchanged') is not True or record.get('design_accepted') is not False:raise ValueError('Complete unaccepted schedule drawing required')
    for key in ['source','project','binding','allocation_project','native_settings','original_plan']:
        if record.get(key):local(record[key])
    files=source_files(*[record.get(k) for k in ['source','project','binding','allocation_project','native_settings','autocad','original_plan']])
    if record['inputs']!={str(p):digest(p) for p in files}:raise ValueError('Schedule source or method pins changed')
    for name,sha in record['artifacts'].items():
        path=(out/name).resolve()
        if not path.is_relative_to(out) or not path.is_file() or digest(path)!=sha:raise ValueError('Schedule drawing artifact changed')
    if subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()!=COMMIT or subprocess.check_output(['git','-C',str(UPSTREAM),'status','--porcelain'],text=True).strip():raise ValueError('Upstream source changed')
    writer=json.loads((out/'writer.json').read_text())
    if writer['upstream_commit']!=COMMIT or writer['versions']!={k:importlib.metadata.version(k) for k in ['ezdxf','pydantic','numpy']} or writer['source_unchanged'] is not True or writer['target_sha256']!=digest(out/'Supply Air Distribution.dxf'):raise ValueError('Upstream writer identity differs')
    # Reconstruct the numerical producer and expected edits separately from saved assertions.
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='schedule-audit-') as folder:
        temp=Path(folder);options={}
        if record['allocation_project']:
            air_allocation.run(record['allocation_project'],temp/'allocation')
            path=temp/'allocation/allocation.json';options=dict(allocation_path=path,allocation_sha256=digest(path))
            if path.read_bytes()!=(out/'allocation/allocation.json').read_bytes():raise ValueError('Allocation differs from source replay')
        fresh=duct_schedule.run(record['project'],temp/'schedule',**options)
        saved=json.loads((out/'schedule/results.json').read_text())
        lineage={str(out/'allocation/allocation.json'):digest(out/'allocation/allocation.json')} if record['allocation_project'] else None
        if (saved.get('allocation_input')!=lineage) or (lineage is None and 'allocation_input' in saved):raise ValueError('Allocation lineage differs from source producer')
        if {k:v for k,v in fresh.items() if k!='allocation_input'}!={k:v for k,v in saved.items() if k!='allocation_input'}:raise ValueError('Schedule differs from source replay')
        path=temp/'schedule/results.json'
        duct_sheet.run(record['source'],path,record['binding'],temp/'reference',inherited_schedule_sha256=digest(path))
        checked=correspondence(record['source'],temp/'reference/Supply Air Distribution.dxf',out/'Supply Air Distribution.dxf',record['layers'])
        spec=json.loads(Path(record['binding']).read_text());gold=ezdxf.readfile(temp/'reference/Supply Air Distribution.dxf')
        cells=[c for row in spec['sections'].values() for c in row['cells']]
        arrow_layer=spec.get('flow_arrows',{}).get('layer')
        counts=dict(sections=len(fresh['sections']),bound_cells=len(cells),changed_cells=sum(c['expected_text']!=gold.entitydb[c['handle']].dxf.text for c in cells),arrow_lines=sum(e.dxf.layer==arrow_layer for e in gold.modelspace()) if arrow_layer else 0)
        if any(record.get(k)!=v for k,v in counts.items()) or writer['edited_cells']!=counts['bound_cells'] or writer['arrow_lines']!=counts['arrow_lines']:raise ValueError('Drawing coverage counts differ from source replay')
        if checked!=record['comparison']:raise ValueError('Saved drawing comparison differs')
    if record['original_plan']:
        plan=json.loads(Path(record['original_plan']).read_text())
        if record['original_requirements']!=plan['requirements'] or record['original_unresolved_inputs']!=plan.get('unresolved_inputs',[]):raise ValueError('Original assignment context changed')
    if record['native_settings']:
        native=json.loads((out/'native/native-sheet.json').read_text())
        if not native['native_reopen_pass'] or not native['plot']['pdf_reference_pass'] or not record['native_reopen_pass']:raise ValueError('Native reopen or plot proof missing')
        wanted={str(out/'Supply Air Distribution.dxf'):digest(out/'Supply Air Distribution.dxf'),record['native_settings']:digest(Path(record['native_settings'])),record['autocad']:digest(Path(record['autocad']))}
        if native['inputs']!=wanted or record.get('native_plot')!=native['plot']:raise ValueError('Native producer source identity differs')
        if duct_sheet_native.compare(out/'Supply Air Distribution.dxf',out/'native/reopened/source-export.dxf',record['layers'])!=native['generated_geometry']:raise ValueError('Native reopened geometry differs')
    elif record['native_reopen_pass'] is not False:raise ValueError('Unexecuted native drawing cannot claim reopening')
    if record['inputs']!={str(p):digest(p) for p in files}:raise ValueError('Sources changed during verification')
    return dict(integrity_pass=True,sections=record['sections'],bound_cells=record['bound_cells'],changed_cells=record['changed_cells'],arrow_lines=record['arrow_lines'],native_reopen_pass=record['native_reopen_pass'],plot_visual_review='separate_required',design_accepted=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    command=sub.add_parser('run')
    for key in ['source','project','binding','out']:command.add_argument('--'+key,required=True)
    for key in ['allocation-project','native-settings','autocad','original-plan']:command.add_argument('--'+key)
    sub.add_parser('verify').add_argument('out');a=parser.parse_args()
    if a.command=='verify':result=verify(a.out);print(json.dumps(result,indent=2));return 0
    result=run(a.source,a.project,a.binding,a.out,allocation_project=a.allocation_project,native_settings=a.native_settings,autocad=a.autocad,original_plan=a.original_plan)
    print(json.dumps({k:result[k] for k in ['status','native_reopen_pass','inputs_unchanged','design_accepted']}|dict(error=result.get('error')),indent=2));return 0 if result['status']=='written' else 2

if __name__=='__main__':raise SystemExit(main())
