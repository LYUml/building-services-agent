"""Stage public source data for the common electrical-to-rule workflow."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.workflow import passages

ROOT=Path(__file__).resolve().parents[2]


def build(out,sources,drawings=False,registered=False):
    out,sources=Path(out).resolve(),Path(sources).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('New repository runs folder required')
    pack_path=ROOT/'regulations/hk/2026.11.08/pack.json';pack=json.loads(pack_path.read_text())
    used={r['source_id'] for r in pack['rules']}
    for key in used:
        row=pack['sources'][key];path=sources/row['cache_filename']
        if path.is_file() and digest(path)!=row['sha256']:raise ValueError('Official source hash differs;review source before staging')
    out.mkdir(parents=True);(out/'source').mkdir();(out/'sources').mkdir();origins={}
    for source,name in [(ROOT/'examples/electrical-paths/project.json','project.json'),(ROOT/'examples/electrical-paths/topology.json','topology.json'),(pack_path,'pack.json')]:
        shutil.copyfile(source,out/'source'/name);origins[source.relative_to(ROOT).as_posix()]=digest(source)
    presentation=[]
    if drawings:
        project_path=out/'source/project.json';project=json.loads(project_path.read_text())
        for i,device in enumerate(project['devices']):
            chosen=[0.,float(i)]
            presentation.append(dict(device_id=device['id'],original_schematic_xy_m=[device['x_m'],device['y_m']],chosen_schematic_xy_m=chosen))
            device['x_m'],device['y_m']=chosen
        project['sources']['schematic_presentation']='Explicit separated symbol rows for this synthetic public diagram only;one drawing metre row spacing is a drafting choice,not physical coordinates or service clearance. All electrical quantities unchanged.'
        project_path.write_text(json.dumps(project,indent=2),encoding='utf-8')
    basis_source=ROOT/'examples/regulations-hk/project.json';basis=json.loads(basis_source.read_text());basis['facts'].pop('installation_origin_to_fixed_equipment_voltage_drop')
    (out/'source/basis.json').write_text(json.dumps(basis,indent=2),encoding='utf-8');origins[basis_source.relative_to(ROOT).as_posix()]=digest(basis_source)
    for key in used:
        row=pack['sources'][key];path=sources/row['cache_filename']
        if path.is_file():shutil.copyfile(path,out/'sources'/row['cache_filename'])
    request=dict(schema='bsa.module-request/1',project_id='public-electrical-rules',scenario_id='synthetic-radial',capability='analysis.electrical.single-phase-circuits',coordinate_frame=dict(id='declared-electrical-schematic',kind='source-world-si',length_unit='m',georeferenced=False),sources=dict(project=dict(path='source/project.json',sha256=digest(out/'source/project.json'))))
    (out/'request.json').write_text(json.dumps(request,indent=2),encoding='utf-8')
    brief=out/'brief.md';brief.write_text('# Conditional radial electrical rule example\n\nCalculate source/project.json with the common single-phase electrical provider;preserve circuit IDs,current,ampacity,branch voltage drop and all unresolved protection/native checks.\n\nBind that exact passing result to source/topology.json,source/basis.json and source/pack.json. Use complete explicit radial origin-to-equipment paths;never substitute branch-only drop or user-supplied total metrics. Preserve source applicability and pending rule coverage.\n\nReview actual routes,products,protection,native drawings,source applicability and every remaining engineering requirement separately. Failed or pending rule checks must block this dependent review;scoped checks do not establish full regulatory or engineering acceptance.\n',encoding='utf-8')
    rows=passages(brief);tasks=[dict(id='electrical',kind='module_analysis',provider='bsa.single-phase-circuits',request='request.json'),dict(id='rules',kind='module_electrical_rules',depends_on='electrical',topology='source/topology.json',basis='source/basis.json',pack='source/pack.json',sources='sources'),dict(id='review',kind='manual',requires_pass=['rules'],description=rows[-1]['text'])]
    if drawings:
        text=brief.read_text(encoding='utf-8');marker='\n\nReview actual routes'
        text=text.replace(marker,'\n\nOnly after that rule task passes,inherit the same electrical module device DXF and source-check device IDs/coordinates. Save and independently reopen a DWG in isolated AutoCAD and plot a fit-to-page schematic. Inspect the actual PDF separately;symbols do not establish physical cable routes or fixed-scale installation drawings.'+marker)
        brief.write_text(text,encoding='utf-8');rows=passages(brief)
        tasks.insert(2,dict(id='native',kind='module_electrical_native',depends_on='rules'))
        tasks[-1].update(requires_pass=['rules','native'],description=rows[-1]['text'])
    if registered:tasks[1]['provider']='bsa.electrical-path-rules'
    plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'context' if i==0 else 'requirement' for i,r in enumerate(rows)},tasks=tasks,requirements=[dict(id='R'+str(i),task=t['id'],passage=r['id'],quote=r['text'],acceptance=r['text']) for i,(t,r) in enumerate(zip(tasks,rows[1:]),1)])
    (out/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    (out/'source-manifest.json').write_text(json.dumps(dict(public_source_sha256=origins,schematic_presentation=presentation,basis_transformation='Omit standalone demonstration total-drop value;the verified producer and explicit topology supply this computed metric',official_source_sha256={pack['sources'][k]['cache_filename']:digest(out/'sources'/pack['sources'][k]['cache_filename']) if (out/'sources'/pack['sources'][k]['cache_filename']).is_file() else None for k in used}),indent=2),encoding='utf-8')
    return out/'plan.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--sources',required=True);p.add_argument('--drawings',action='store_true');p.add_argument('--registered-rules',action='store_true');a=p.parse_args();print(build(a.out,a.sources,a.drawings,a.registered_rules))
