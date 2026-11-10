"""Author explicit design-decision concept volumes; no invented MEP or simulation claims."""
import argparse
import json
from pathlib import Path
import uuid
from bsa.bim import run as author,CONCEPT_SCOPE
from bsa.cli import digest
ROOT=Path(__file__).resolve().parents[1]


def stage(decisions,variant):
    height=decisions['floor_to_floor_height_m']
    namespace=str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/LYUml/building-services-agent/benchmarks/mit-4401-2018/concept'))
    source='Explicit concept design decisions, not site measurements: '+decisions['frame']+'; '+decisions['height_basis']+'; gross footprint only. Course source SHA256 '+decisions['source']['sha256']
    rows=[dict(id=f'Level{i+1}',elevation_m=i*height,height_m=height,source='design') for i in range(variant['storeys'])]
    return dict(name='Unapproved public-brief concept: '+variant['id'],project_uuid=namespace,geometry_scope=CONCEPT_SCOPE,sources=dict(design=source),floor_area_basis='gross concept footprint; no deductions',storeys=rows,spaces=[dict(id='Space_'+r['id'],storey=r['id'],origin_m=[0,0,r['elevation_m']],size_m=[variant['width_m'],variant['depth_m'],height],source='design') for r in rows],systems=[],devices=[],connections=[])


from bsa.concept_layout import geometry_handoff


def run(out):
    out=Path(out).resolve();decisions=ROOT/'benchmarks/mit-4401-2018/massing-decisions.json'
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('new repository-local concept output required')
    before=digest(decisions);data=json.loads(decisions.read_text(encoding='utf-8'));out.mkdir(parents=True);results={}
    for variant in data['variants']:
        file=out/(variant['id']+'.json');file.write_text(json.dumps(stage(data,variant),indent=2),encoding='utf-8')
        r=author(file,out/variant['id'])
        from bsa.ifc_preview import run as preview
        view=preview(out/variant['id']/'model.ifc',r['spaces'][0]['guid'],out/variant['id']/'preview',[s['guid'] for s in r['spaces'][1:]])
        handoff=geometry_handoff(out/variant['id']/'model.ifc',stage(data,variant),data['window_wall_ratio']['course_comparison_target'])
        (out/variant['id']/'geometry-handoff.json').write_text(json.dumps(handoff,indent=2),encoding='utf-8')
        results[variant['id']]=dict(model_checks_pass=r['model_checks_pass'],space_count=len(r['spaces']),gross_footprint_area_m2=r['total_gross_footprint_area_m2'],ifc_sha256=r['ifc_sha256'],preview_sha256=view['preview_sha256'],geometry_handoff_sha256=digest(out/variant['id']/'geometry-handoff.json'))
    if digest(decisions)!=before:raise ValueError('concept decisions changed')
    result=dict(decisions_sha256=before,variants=results,design_accepted=False,scope='Native storey/space concept volumes only; no site, facade/window geometry, net usable area, thermal boundary or performance proof')
    (out/'concepts.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result

def run_workflow(out,source_cache,apply_work_plan=False,honeybee_python=None):
    import runpy
    import subprocess
    import sys
    from bsa.workflow import plan_documents
    loader=runpy.run_path(str(ROOT/'scripts/stage_public_brief_benchmark.py'))
    loader['run'](out,source_cache,True);out=Path(out).resolve();path=out/'plan.json'
    plan=json.loads(path.read_text(encoding='utf-8'));decision_path=ROOT/'benchmarks/mit-4401-2018/massing-decisions.json';data=json.loads(decision_path.read_text(encoding='utf-8'));before=digest(decision_path)
    passage=next(r for r in plan_documents(out,plan)['passages'] if r['id']=='D002:P001')
    tasks=[]
    facade_basis=out/'facade-basis.json'
    facade_basis.write_bytes((ROOT/'benchmarks/mit-4401-2018/facade-decisions.json').read_bytes())
    for variant in data['variants']:
        file=out/(variant['id']+'.json');model=stage(data,variant);model['sources']['design']+=' Decision record SHA256 '+before
        file.write_text(json.dumps(model,indent=2),encoding='utf-8')
        settings=out/(variant['id']+'-layout.json')
        settings.write_text(json.dumps(dict(source='Course WWR assignment5 page1 SHA256 '+data['source']['sha256']+'; centered equal-fraction rectangles are unapproved design decisions',window_wall_ratio=data['window_wall_ratio']['course_comparison_target'],layout='centered-equal-fraction'),indent=2),encoding='utf-8')
        id='concept-'+variant['id'];tasks.append(dict(id=id,kind='bim',project=file.name,concept_layout=settings.name))
        plan['requirements'].append(dict(id='concept-'+variant['id'],passage=passage['id'],quote=passage['text'],task=id,acceptance='Unapproved source-defined gross concept space/storey geometry only; including sourced draft window layout; full site, facade/daylight/program acceptance remains in retained interpretation requirements'))
    if honeybee_python:
        (out/'scene-basis.json').write_bytes((ROOT/'benchmarks/mit-4401-2018/scene-decisions.json').read_bytes())
    model_tasks=list(tasks)
    for task in model_tasks:
        label=task['id'].removeprefix('concept-');fid='facade-'+label
        tasks.append(dict(id=fid,kind='concept_facade',depends_on=task['id'],basis=facade_basis.name))
        guid=__import__('ifcopenshell').guid.compress(uuid.uuid5(uuid.UUID(model['project_uuid']),'IfcWall_Space_Level1_XMinus').hex)
        tasks.append(dict(id='facade-view-'+label,kind='ifc_preview',depends_on=fid,guid=guid))
        plan['requirements'].append(dict(id=fid,passage=passage['id'],quote=passage['text'],task=fid,acceptance='Unapproved native facade geometry with explicit thickness decisions; no materials/performance or full architectural acceptance'))
        plan['requirements'].append(dict(id='facade-view-'+label,passage=passage['id'],quote=passage['text'],task='facade-view-'+label,acceptance='Single-wall saved-IFC diagnostic preview only; not course daylight visualization or approved drawing'))
        if honeybee_python:
            sid='scene-'+label
            tasks.append(dict(id=sid,kind='honeybee_scene',depends_on=fid,basis='scene-basis.json'))
            plan['requirements'].append(dict(id=sid,passage=passage['id'],quote=passage['text'],task=sid,acceptance='Partial native-source optical scene and sensor-grid conversion only; complete annual daylight work remains pending'))
    if honeybee_python:
        (out/'climate-weather.epw.gz').write_bytes((ROOT/'examples/annual-energy/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw.gz').read_bytes())
        (out/'climate-basis.json').write_bytes((ROOT/'benchmarks/mit-4401-2018/climate-decisions.json').read_bytes())
        tasks.insert(0,dict(id='climate-context',kind='climate_context',weather='climate-weather.epw.gz',basis='climate-basis.json'))
        plan['requirements'].append(dict(id='climate-context',passage=passage['id'],quote=passage['text'],task='climate-context',acceptance='Candidate weather-station statistics/solar paths only; original course-city/site/shading obligations remain pending'))
    plan['tasks']=tasks+plan['tasks'];path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    if apply_work_plan:
        from bsa.work_plan_review import apply
        review=out/'work-plan-review.json';review.write_bytes((ROOT/'benchmarks/mit-4401-2018/work-plan-review.json').read_bytes())
        apply(path,review)
    command=[sys.executable,'-m','bsa.cli','workflow',str(path),'--out',str(out/'workflow')]
    if honeybee_python:command+=['--honeybee-python',str(Path(honeybee_python).resolve())]
    worker=subprocess.run(command,capture_output=True,text=True)
    (out/'worker.log').write_text(worker.stdout+worker.stderr,encoding='utf-8')
    if worker.returncode!=2 or not (out/'workflow/diagnosis.json').is_file():raise ValueError('expected partial concept workflow with retained interpretation blockers')
    report=json.loads((out/'workflow/workflow.json').read_text(encoding='utf-8'))
    if any(report['tasks'][t['id']]['status']!='pass' for t in tasks) or digest(decision_path)!=before:raise ValueError('concept geometry failed or decisions changed')
    result=dict(concept_tasks={t['id']:report['tasks'][t['id']]['status'] for t in tasks},pending_interpretation_tasks=sum(t['status']=='pending' for t in report['tasks'].values()),design_accepted=False,scope='Partial real-brief workflow: concept geometry only; original technical obligations retained')
    if apply_work_plan:
        result['pending_work_packages']=result.pop('pending_interpretation_tasks')
        result['scope']='Reviewed source-complete work decomposition with partial concept execution; unmet engineering/delivery packages retained'
    (out/'concept-workflow.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--source-cache',type=Path,help='Stage reviewed public-brief workflow using this pinned source cache')
    p.add_argument('--apply-work-plan',action='store_true',help='Apply exact-source reviewed work decomposition; all unmet engineering work remains pending')
    p.add_argument('--honeybee-python',type=Path,help='Explicit isolated runtime; enables source-inherited scene conversion tasks, not annual solving')
    args=p.parse_args();r=run_workflow(args.out,args.source_cache,args.apply_work_plan,args.honeybee_python) if args.source_cache else run(args.out);print(json.dumps(r))
