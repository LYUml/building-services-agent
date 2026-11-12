"""Compose existing recognition,HK LPD and independent electrical adapters.

All project facts here are explicit synthetic software controls. Official PDF
bytes may be copied from a host-selected cache;no missing source is fabricated.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.documents import extract

ROOT=Path(__file__).resolve().parents[2]


def build(out, sources=None, *, ifc_source=None, tolerances=None, air_balance=False):
    out=Path(out).resolve()
    if out.exists():raise ValueError('New workflow input directory required')
    out.mkdir(parents=True);(out/'sources').mkdir()
    if ifc_source is None:
        for name in ('l-shaped-room.geo','l-shaped-room.expected.json','l-shaped-room.request.json'):
            shutil.copyfile(ROOT/'examples/moosas-transform'/name,out/name)
        request_name='l-shaped-room.request.json';provider='moosas.surface-room-recognition';space_ids=['l-shaped-room']
    else:
        import ifcopenshell
        if not isinstance(tolerances,dict) or set(tolerances)!={'length_tolerance_m','area_tolerance_m2'}:raise ValueError('Explicit native source tolerances required')
        source=out/'native-source.ifc';shutil.copyfile(ifc_source,source)
        settings=out/'native-settings.json';settings.write_text(json.dumps(tolerances,indent=2))
        space_ids=[s.GlobalId for s in ifcopenshell.open(str(source)).by_type('IfcSpace')]
        request_name='native-request.json';provider='moosas.ifc-room-recognition'
        request=dict(schema='bsa.module-request/1',project_id='synthetic-native-ifc-workflow',scenario_id='source-inheritance',capability='spatial.ifc-room-recognition',coordinate_frame=dict(id='ifc-world-si',kind='source-world-si',length_unit='m',georeferenced=False),sources={role:dict(path=p.name,sha256=digest(p)) for role,p in [('ifc',source),('settings',settings)]})
        (out/request_name).write_text(json.dumps(request,indent=2))
    pack=ROOT/'regulations/hk/lighting-2026.11.08/pack.json'
    shutil.copyfile(pack,out/'lighting-pack.json')
    definition=json.loads(pack.read_text())
    if sources is not None:
        source=Path(sources)/definition['sources']['emsd_bec_2024']['cache_filename']
        if digest(source)!=definition['sources']['emsd_bec_2024']['sha256']:raise ValueError('Exact existing pinned official BEC source required')
        shutil.copyfile(source,out/'sources'/source.name)
    basis=json.loads((ROOT/'examples/regulations-hk-lighting/project.json').read_text())
    basis['lighting_space'].pop('internal_floor_area')
    bases={}
    for guid in space_ids:
        row=copy.deepcopy(basis)
        for light in row['lighting_space']['luminaires']:light['id']=guid+':'+light['id']
        bases[guid]=row
    (out/'lighting-basis.json').write_text(json.dumps(bases,indent=2))
    shutil.copyfile(ROOT/'examples/office-electrical/project.json',out/'electrical.json')
    brief=out/'brief.md'
    geometry_requirement=('Recognize the declared concave room from its surface geometry and preserve its source identity and boundary.' if ifc_source is None else
        'Recognize every supported saved IFC space,including concave boundaries,and preserve complete native GUID coverage without repeated room dimensions.')
    paragraphs=['# Synthetic source-recognition and lighting integration',geometry_requirement,
        'Inherit its recognized floor area into the existing selected Hong Kong office LPD check using the explicit synthetic luminaire inventory and applicability assertions.',
        'Review downstream engineering applicability only after geometry and selected rules pass; no physical or complete compliance claim follows from numerical checks.',
        'Execute the independent synthetic single-phase electrical calculation even when the recognition provider is unavailable.']
    ids=['recognition','lighting-rules','review','independent-electrical']
    if air_balance:
        from bsa.air_load import UNITS
        values=dict(cooling_allowance=200,sensible_fraction=.8,density=1.25,specific_heat=1000,temperature_difference=10)
        load_basis={guid:{key:dict(value=value,unit=UNITS[key],classification='assumed',source='Explicit synthetic uniform-allowance/air-property control;not measured room load') for key,value in values.items()} for guid in space_ids}
        (out/'air-balance-basis.json').write_text(json.dumps(load_basis,indent=2))
        paragraphs.insert(3,'Inherit every source space area into the existing classified thermal and supply-air balance using the explicit synthetic non-geometric basis; preserve unverified room-load and full HVAC acceptance.')
        ids.insert(2,'air-balance')
    brief.write_text('\n\n'.join(paragraphs)+'\n',encoding='utf-8')
    passages=extract(brief)['passages']
    plan=dict(version=1,brief=brief.name,brief_sha256=digest(brief),
        passage_dispositions={r['id']:'context' if i==0 else 'requirement' for i,r in enumerate(passages)},
        tasks=[dict(id='recognition',kind='module_exchange',provider=provider,request=request_name),
            dict(id='lighting-rules',kind='spatial_lighting_rules',depends_on='recognition',basis='lighting-basis.json',pack='lighting-pack.json',sources='sources'),
            dict(id='review',kind='manual',requires_pass=['recognition','lighting-rules'],description='Actual source interpretation,installation,photometry and full acceptance remain pending'),
            dict(id='independent-electrical',kind='electrical',project='electrical.json')],
        requirements=[dict(id='R'+str(i),passage=row['id'],quote=row['text'],task=task,acceptance=row['text']) for i,(row,task) in enumerate(zip(passages[1:],ids),1)])
    if air_balance:
        plan['tasks'].insert(2,dict(id='air-balance',kind='spatial_air_balance',depends_on='recognition',basis='air-balance-basis.json'))
        next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append('air-balance')
    if len(passages)!=len(ids)+1:raise ValueError('Exact public fixture passage coverage required')
    path=out/'plan.json';path.write_text(json.dumps(plan,indent=2));return path


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--sources',type=Path)
    parser.add_argument('--ifc',type=Path);parser.add_argument('--length-tolerance-m',type=float);parser.add_argument('--area-tolerance-m2',type=float)
    parser.add_argument('--air-balance',action='store_true')
    args=parser.parse_args()
    if args.ifc and (args.length_tolerance_m is None or args.area_tolerance_m2 is None):parser.error('Explicit IFC source length/area tolerances required')
    print(build(args.out,args.sources,ifc_source=args.ifc,tolerances=None if args.ifc is None else dict(length_tolerance_m=args.length_tolerance_m,area_tolerance_m2=args.area_tolerance_m2),air_balance=args.air_balance))
