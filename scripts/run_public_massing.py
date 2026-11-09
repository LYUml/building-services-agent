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


def geometry_handoff(ifc,source,wwr):
    """Reuse saved-solid extraction and adjacency; do not infer thermal boundaries."""
    import ifcopenshell
    from bsa.concept_spaces import inspect_spaces
    from bsa.thermal_binding import extract
    from bsa.thermal_geometry import boxes,adjacency
    if not isinstance(wwr,(int,float)) or isinstance(wwr,bool) or not 0<wwr<1:
        raise ValueError('explicit fractional concept WWR target required')
    before=digest(ifc)
    inspected=inspect_spaces(ifcopenshell.open(str(ifc)),source)
    binding=dict(spaces=[dict(guid=r['guid'],id=r['id'],source='Concept geometry only; not established thermal boundary') for r in inspected])
    rows,audit=extract(ifc,binding)
    boxes(dict(spaces=rows));pairs=adjacency(rows)
    total_walls=sum(2*(r['size_m'][0]+r['size_m'][1])*r['size_m'][2] for r in rows)
    exterior_walls=total_walls-2*sum(r['area_m2'] for r in pairs if r['axis']!=2)
    horizontal=sum(r['size_m'][0]*r['size_m'][1] for r in rows)
    horizontal_contacts=sum(r['area_m2'] for r in pairs if r['axis']==2)
    if digest(ifc)!=before:raise ValueError('concept source changed during handoff')
    return dict(ifc_sha256=before,geometry=audit,adjacency=pairs,
        exterior_vertical_face_area_m2=exterior_walls,
        exposed_top_face_area_m2=horizontal-horizontal_contacts,
        exposed_bottom_face_area_m2=horizontal-horizontal_contacts,
        course_wwr_target=wwr,target_glazed_area_m2=exterior_walls*wwr,
        modeled_window_area_m2=0,thermal_model_ready=False,design_accepted=False,
        scope='Geometric exterior faces only; not surveyed facade or validated thermal boundaries. Glazed area is a comparison target, not authored windows.',
        pending=['site/weather and explicit orientation','actual thermal boundary and clear-height interpretation','window positions and sourced glazing','construction, gains, schedules and HVAC','native annual simulation and deliverable acceptance'])


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

def run_workflow(out,source_cache):
    import runpy
    import subprocess
    import sys
    from bsa.workflow import plan_documents
    loader=runpy.run_path(str(ROOT/'scripts/stage_public_brief_benchmark.py'))
    loader['run'](out,source_cache,True);out=Path(out).resolve();path=out/'plan.json'
    plan=json.loads(path.read_text(encoding='utf-8'));decision_path=ROOT/'benchmarks/mit-4401-2018/massing-decisions.json';data=json.loads(decision_path.read_text(encoding='utf-8'));before=digest(decision_path)
    passage=next(r for r in plan_documents(out,plan)['passages'] if r['id']=='D002:P001')
    tasks=[]
    for variant in data['variants']:
        file=out/(variant['id']+'.json');model=stage(data,variant);model['sources']['design']+=' Decision record SHA256 '+before
        file.write_text(json.dumps(model,indent=2),encoding='utf-8')
        id='concept-'+variant['id'];tasks.append(dict(id=id,kind='bim',project=file.name))
        plan['requirements'].append(dict(id='concept-'+variant['id'],passage=passage['id'],quote=passage['text'],task=id,acceptance='Unapproved source-defined gross concept space/storey geometry only; full site, facade/daylight/program acceptance remains in retained interpretation requirements'))
    plan['tasks']=tasks+plan['tasks'];path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    worker=subprocess.run([sys.executable,'-m','bsa.cli','workflow',str(path),'--out',str(out/'workflow')],capture_output=True,text=True)
    (out/'worker.log').write_text(worker.stdout+worker.stderr,encoding='utf-8')
    if worker.returncode!=2 or not (out/'workflow/diagnosis.json').is_file():raise ValueError('expected partial concept workflow with retained interpretation blockers')
    report=json.loads((out/'workflow/workflow.json').read_text(encoding='utf-8'))
    if any(report['tasks'][t['id']]['status']!='pass' for t in tasks) or digest(decision_path)!=before:raise ValueError('concept geometry failed or decisions changed')
    result=dict(concept_tasks={t['id']:report['tasks'][t['id']]['status'] for t in tasks},pending_interpretation_tasks=sum(t['status']=='pending' for t in report['tasks'].values()),design_accepted=False,scope='Partial real-brief workflow: concept geometry only; original technical obligations retained')
    (out/'concept-workflow.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--source-cache',type=Path,help='Stage reviewed public-brief workflow using this pinned source cache')
    args=p.parse_args();r=run_workflow(args.out,args.source_cache) if args.source_cache else run(args.out);print(json.dumps(r))
