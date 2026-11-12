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


def build(out, sources=None, *, ifc_source=None, tolerances=None, air_balance=False, terminal_allocation=False, performance_settings=None, drawing_settings=None, native_settings=None, ifc_basis=None, clash_policy=None, inlet_basis=None, stub_basis=None):
    if terminal_allocation and not air_balance:raise ValueError('Terminal allocation requires explicit air balance selection')
    if performance_settings is not None and not terminal_allocation:raise ValueError("Performance requires explicit terminal allocation")
    if drawing_settings is not None and not terminal_allocation:raise ValueError('Drawing requires explicit terminal allocation')
    if native_settings is not None and drawing_settings is None:raise ValueError('Native verification requires explicit drawing settings')
    if ifc_basis is not None and performance_settings is None:raise ValueError('IFC envelope study requires explicit terminal performance')
    if inlet_basis is not None and ifc_basis is None:raise ValueError('Inlets require explicit terminal IFC basis')
    if clash_policy is not None and ifc_basis is None:raise ValueError('Coordination requires explicit terminal IFC basis')
    if stub_basis is not None and inlet_basis is None:raise ValueError('Short stubs require explicit inlet basis')
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
    if terminal_allocation:
        from shapely.geometry import Polygon
        if ifc_source is None:
            rooms=json.loads((out/'l-shaped-room.expected.json').read_text())['expected']
        else:
            from bsa.ifc_space_surfaces import prepare as native_spaces
            _,declaration,_=native_spaces(out/'native-source.ifc',**tolerances);rooms=declaration['expected']
        terminal_basis={}
        for room in rooms:
            point=Polygon(room['boundary_vertices']).representative_point()
            terminal_basis[room['id']]=dict(terminals=[dict(id=room['id']+'_terminal1',center_m=[point.x,point.y],unit='m',classification='design_choice',source='Synthetic interior-point placement for integration checks;not optimized air coverage or installed position')],turndown=dict(value=.4,unit='1',classification='assumed',source='Explicit synthetic40%turndown control;not measured equipment performance'))
        (out/'terminal-design-basis.json').write_text(json.dumps(terminal_basis,indent=2))
        paragraphs.insert(4,'Allocate each inherited room airflow to explicitly declared synthetic terminal positions and turndown; preserve source geometry,maximum/minimum flow conservation and pending ADPI/installation checks.')
        ids.insert(3,'terminal-allocation')
    if performance_settings is not None:
        from bsa.terminal_performance import settings_inputs
        settings=Path(performance_settings).resolve();spec,_=settings_inputs(settings)
        target=out/'performance-source';target.mkdir()
        shutil.copyfile(settings,target/'settings.json')
        for role in ('source','catalogue'):
            destination=target/spec[role];destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(settings.parent/spec[role],destination)
        selections={terminal['id']:dict(settings='performance-source/settings.json',source='Explicit synthetic product trial;installation applicability unverified',classification='design_choice') for room in terminal_basis.values() for terminal in room['terminals']}
        (out/'performance-selections.json').write_text(json.dumps(selections,indent=2))
        paragraphs.insert(5,'Query the explicitly selected source catalogue at inherited maximum/minimum terminal flows;preserve out-of-range data requests and pending ADPI,acoustics and fan acceptance.')
        ids.insert(4,'terminal-performance')
    if drawing_settings is not None:
        shutil.copyfile(drawing_settings,out/'drawing-settings.json')
        paragraphs.insert(-1,'Generate an editable source-bound room and terminal-centre airflow schematic;preserve pending native DWG,installation and complete engineering review.')
        ids.insert(-1,'terminal-drawing')
    if native_settings is not None:
        shutil.copyfile(native_settings,out/'spatial-native-settings.json')
        paragraphs.insert(-1,'Save and independently reopen the inherited schematic in AutoCAD and verify its fixed-scale PDF reference;retain visual and engineering review as pending.')
        ids.insert(-1,'terminal-native')
    for path,name,text in [(ifc_basis,'terminal-ifc','Author source-classified terminal IFC envelopes from the inherited performance/allocation source,retaining every original space/entity and pending installation checks.'),(inlet_basis,'terminal-inlets','Add explicit source-classified logical inlets and air-system groups while preserving body geometry and pending physical connection requirements.'),(stub_basis,'terminal-stubs','Author explicit hollow short ducts from saved inlet frames and source-classified dimensions;retain open upstream boundaries and unresolved physical/network acceptance.'),(clash_policy,'terminal-coordination','Check the exact authored IFC against the complete sourced clash policy;retain whole-model failures and pending engineering applicability.')]:
        if path is not None:
            shutil.copyfile(path,out/(name+'-basis.json'))
            paragraphs.insert(-1,text);ids.insert(-1,name)
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
    if terminal_allocation:
        plan['tasks'].insert(3,dict(id='terminal-allocation',kind='spatial_air_allocation',depends_on='air-balance',basis='terminal-design-basis.json'))
        next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append('terminal-allocation')
    if performance_settings is not None:
        plan['tasks'].insert(4,dict(id='terminal-performance',kind='spatial_terminal_performance',depends_on='terminal-allocation',basis='performance-selections.json'))
        next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append('terminal-performance')
    if drawing_settings is not None:
        index=next(i for i,t in enumerate(plan['tasks']) if t['id']=='review')
        plan['tasks'].insert(index,dict(id='terminal-drawing',kind='spatial_terminal_drawing',depends_on='terminal-allocation',settings='drawing-settings.json'))
        next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append('terminal-drawing')
    if native_settings is not None:
        index=next(i for i,t in enumerate(plan['tasks']) if t['id']=='review')
        plan['tasks'].insert(index,dict(id='terminal-native',kind='spatial_terminal_native',depends_on='terminal-drawing',settings='spatial-native-settings.json'))
        next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append('terminal-native')
    for path,name,kind,parent,field in [(ifc_basis,'terminal-ifc','spatial_terminal_ifc','terminal-performance','basis'),(inlet_basis,'terminal-inlets','spatial_terminal_inlets','terminal-ifc','basis'),(stub_basis,'terminal-stubs','spatial_terminal_stubs','terminal-inlets','basis'),(clash_policy,'terminal-coordination','spatial_terminal_coordination','terminal-stubs' if stub_basis is not None else 'terminal-inlets' if inlet_basis is not None else 'terminal-ifc','policy')]:
        if path is not None:
            index=next(i for i,t in enumerate(plan['tasks']) if t['id']=='review')
            plan['tasks'].insert(index,dict(id=name,kind=kind,depends_on=parent,**{field:name+'-basis.json'}))
            next(t for t in plan['tasks'] if t['id']=='review')['requires_pass'].append(name)
    if len(passages)!=len(ids)+1:raise ValueError('Exact public fixture passage coverage required')
    path=out/'plan.json';path.write_text(json.dumps(plan,indent=2));return path


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--sources',type=Path)
    parser.add_argument('--ifc',type=Path);parser.add_argument('--length-tolerance-m',type=float);parser.add_argument('--area-tolerance-m2',type=float)
    parser.add_argument('--air-balance',action='store_true')
    parser.add_argument('--terminal-allocation',action='store_true')
    parser.add_argument('--performance-settings',type=Path)
    parser.add_argument('--drawing-settings',type=Path)
    parser.add_argument('--native-settings',type=Path)
    parser.add_argument('--ifc-basis',type=Path);parser.add_argument('--clash-policy',type=Path)
    parser.add_argument('--inlet-basis',type=Path)
    parser.add_argument('--stub-basis',type=Path)
    args=parser.parse_args()
    if args.ifc and (args.length_tolerance_m is None or args.area_tolerance_m2 is None):parser.error('Explicit IFC source length/area tolerances required')
    print(build(args.out,args.sources,ifc_source=args.ifc,tolerances=None if args.ifc is None else dict(length_tolerance_m=args.length_tolerance_m,area_tolerance_m2=args.area_tolerance_m2),air_balance=args.air_balance,terminal_allocation=args.terminal_allocation,performance_settings=args.performance_settings,drawing_settings=args.drawing_settings,native_settings=args.native_settings,ifc_basis=args.ifc_basis,clash_policy=args.clash_policy,inlet_basis=args.inlet_basis,stub_basis=args.stub_basis))
