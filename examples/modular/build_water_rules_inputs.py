"""Stage public synthetic native-water/HK workflow inputs; never submit anything."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.workflow import passages

ROOT=Path(__file__).resolve().parents[2]


def build(out,sources,drawings=False):
    out,sources=Path(out).resolve(),Path(sources).resolve()
    if not out.is_relative_to(ROOT/'runs') or out.exists():raise ValueError('New repository runs folder required')
    pack_path=ROOT/'regulations/hk/hvac-water-2026.11.08/pack.json';pack=json.loads(pack_path.read_text())
    for row in pack['sources'].values():
        source=sources/row['cache_filename']
        if source.is_file() and digest(source)!=row['sha256']:raise ValueError('Official source hash differs;review edition before staging')
    out.mkdir(parents=True);(out/'source').mkdir();(out/'sources').mkdir()
    origins={}
    for source,name in [(ROOT/'examples/circulation-ifc'/n,n) for n in ('model.json','project.json','binding.json','regulatory-bases.json')]+[(pack_path,'pack.json')]:
        shutil.copyfile(source,out/'source'/name);origins[source.relative_to(ROOT).as_posix()]=digest(source)
    for row in pack['sources'].values():
        source=sources/row['cache_filename']
        if source.is_file():shutil.copyfile(source,out/'sources'/row['cache_filename'])
    frame=dict(id='synthetic-circulation-world',kind='source-world-si',length_unit='m',georeferenced=False)
    for name,cap,roles in [('authoring','authoring.ifc.bim',{'project':'model.json'}),('water','analysis.water.ifc-steady-graph',{'project':'project.json','binding':'binding.json'})]:
        request=dict(schema='bsa.module-request/1',project_id='public-native-water-rules',scenario_id='synthetic-circulation',capability=cap,coordinate_frame=frame,sources={k:dict(path='source/'+v,sha256=digest(out/'source'/v)) for k,v in roles.items()})
        (out/(name+'-request.json')).write_text(json.dumps(request,indent=2)+'\n',encoding='utf-8')
    brief=out/'brief.md';brief.write_text('# Public native circulation and scoped HK checks\n\nAuthor source/model.json through the common IFC provider. Preserve stable GUIDs,hollow pipe bodies,ports and native saved verification.\n\nDerive the selected-system water graph from that exact saved IFC using source/project.json and binding.json. Reject repeated lengths,bores,elevations or inconsistent native connections;preserve raw signed flows and static pressure-head checks.\n\nApply the selected source/pack.json HVAC water-piping rules to that verified result with source/regulatory-bases.json and hash-matching official sources. Density,code diameter,flow/control mode,edition and scope remain synthetic sourced assertions;no domestic-water applicability or complete conformity is inferred.\n\nReview physical products,node/fitting and fluid applicability,clashes,installation drawings and all remaining engineering and Hong Kong requirements. Failed or pending checks block this dependent review path;full engineering acceptance remains pending.\n',encoding='utf-8')
    rows=passages(brief)
    tasks=[dict(id='model',kind='module_authoring',provider='ifcopenshell.bim-authoring',request='authoring-request.json'),dict(id='water',kind='module_analysis',provider='wntr.ifc-steady',request='water-request.json',depends_on='model'),dict(id='rules',kind='module_water_rules',depends_on='water',basis='source/regulatory-bases.json',pack='source/pack.json',sources='sources'),dict(id='review',kind='manual',requires_pass=['rules'],description=rows[4]['text'])]
    if drawings:
        settings=ROOT/'examples/circulation-ifc/views-settings.json';shutil.copyfile(settings,out/'source/views-settings.json');origins[settings.relative_to(ROOT).as_posix()]=digest(settings)
        text=brief.read_text(encoding='utf-8');marker='\n\nReview physical products'
        additions='\n\nDraw plan and front centreline views of that same verified authoring model using source/views-settings.json,only after the scoped water rule check passes. Preserve all four pipe GUIDs,true/projected lengths and symbolic end-on crosses;excluded pump/node bodies and installation details remain pending.\n\nUse isolated AutoCAD Core Console to save and independently reopen each generated DWG,and plot the declared1:30 two-page set. Check each physical PDF reference and inspect both actual rendered pages before recording visual evidence separately.'
        assert marker in text;brief.write_text(text.replace(marker,additions+marker),encoding='utf-8');rows=passages(brief)
        tasks[3:3]=[dict(id='views',kind='ifc_views',depends_on='model',requires_pass=['rules'],settings='source/views-settings.json'),dict(id='native',kind='ifc_views_native',depends_on='views',requires_pass=['rules'])]
        tasks[-1].update(requires_pass=['rules','native'],description=rows[-1]['text'])
    plan=dict(version=1,brief='brief.md',brief_sha256=digest(brief),passage_dispositions={r['id']:'context' if i==0 else 'requirement' for i,r in enumerate(rows)},tasks=tasks,requirements=[dict(id='R'+str(i),task=t['id'],passage=r['id'],quote=r['text'],acceptance=r['text']) for i,(t,r) in enumerate(zip(tasks,rows[1:]),1)])
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    (out/'source-manifest.json').write_text(json.dumps(dict(public_source_sha256=origins,official_source_sha256={r['cache_filename']:digest(out/'sources'/r['cache_filename']) if (out/'sources'/r['cache_filename']).is_file() else None for r in pack['sources'].values()}),indent=2)+'\n',encoding='utf-8')
    return out/'plan.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--sources',required=True);p.add_argument('--drawings',action='store_true');a=p.parse_args();print(build(a.out,a.sources,a.drawings))
