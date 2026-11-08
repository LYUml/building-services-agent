"""Auditable handoff from a host AI's brief interpretation to engineering tools.

This module does not pretend regex can interpret arbitrary engineering requirements.
The host agent supplies a source-linked plan; execution accepts only known adapters.
"""
import argparse
import html
import json
import re
from pathlib import Path
from .cli import digest
from .engine import ProjectError

IFC_ARTIFACTS={'annual_energy_ifc':'analysis.ifc','bim':'model.ifc','network_coordination':'bim/model.ifc',
               'route_model':'bound/bim/model.ifc','route_optimize':'selected/bound/bim/model.ifc',
               'network_model_design':'selected-coordination/bim/model.ifc',
               'electrical_coordination':'bim/model.ifc','electrical_lighting':'shared/bim/model.ifc','pump_electrical':'model.ifc','water_coordination':'model.ifc'}
NETWORK_ARTIFACTS={'network_coordination':'network-input.json','network_design':'selected-network.json',
                   'network_model_design':'selected-coordination/network-input.json'}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def passages(brief,ocr=None):
    from .documents import extract
    return extract(brief,ocr)["passages"]


def intake(brief,out,ocr=None):
    brief,out=brief.resolve(),out.resolve()
    if out==brief:raise ProjectError("cannot overwrite brief")
    if out.exists():raise ProjectError("refusing to overwrite intake")
    from .documents import extract
    result=dict(brief=str(brief),brief_sha256=digest(brief),**extract(brief,ocr),
        interpretation_status="pending host-agent interpretation",requirements=[])
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def local_path(root,value):
    if not isinstance(value,str) or Path(value).is_absolute():raise ProjectError("plan inputs must use relative paths")
    path=(root/value).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise ProjectError(f"invalid input path: {value}")
    return path


def regulatory_source_bindings(tasks,root):
    """Match known shared-source consumers, including inherited producer inputs."""
    shared={'electrical','electrical_fault','electrical_coordination','electrical_lighting',
            'electrical_regulations','lighting_regulations'}
    geometric={'electrical_coordination','electrical_lighting','lighting_regulations'}
    known={};ancestors={};sources={};bindings=[]
    hashes={}
    def hashed(path):
        if path not in hashes:hashes[path]=digest(path)
        return hashes[path]
    for task in tasks:
        name=task['id'];kind=task['kind']
        parents=[p for p in task.get('requires_pass',[]) if p in known]
        parents += [task[k] for k in ('depends_on','ifc_from') if isinstance(task.get(k),str) and task[k] in known]
        upstream=set(parents)
        for parent in parents:upstream.update(ancestors[parent])
        ancestors[name]=upstream
        current={}
        if kind in shared:
            current['project']=local_path(root,task.get('project'))
            if kind in geometric:current['geometry']=local_path(root,task.get('geometry'))
        elif isinstance(task.get('depends_on'),str):
            current=dict(sources.get(task['depends_on'],{}))
        for parent in sorted(upstream):
            if known[parent]['kind'] not in ('electrical_regulations','lighting_regulations'):continue
            for field in current.keys() & sources[parent].keys():
                checked=sources[parent][field];consumed=current[field]
                if hashed(checked)!=hashed(consumed):
                    raise ProjectError(f'regulatory gate {parent} checks different {field} bytes from consumer {name}')
                bindings.append(dict(check=parent,consumer=name,field=field,checked=str(checked),consumed=str(consumed),sha256=hashed(checked)))
        known[name]=task;sources[name]=current
    return bindings


def validate_plan(path):
    root=path.resolve().parent;p=read_json(path)
    if not isinstance(p,dict) or type(p.get("version")) is not int or p.get("version")!=1:raise ProjectError("plan version 1 required")
    brief=local_path(root,p.get("brief"))
    if digest(brief)!=p.get("brief_sha256"):raise ProjectError("brief hash differs; re-interpret current source")
    from .documents import extract,check_review
    ocr=local_path(root,p['ocr']) if p.get('ocr') else None
    if ocr and digest(ocr)!=p.get('ocr_sha256'):raise ProjectError('OCR sidecar changed; re-review transcription')
    document=extract(brief,ocr)
    check_review(document,p.get("document_review",{}))
    source={x["id"]:x for x in document["passages"]}
    dispositions=p.get("passage_dispositions")
    if not isinstance(dispositions,dict) or set(dispositions)!=set(source):
        raise ProjectError("every brief passage needs an explicit requirement/context disposition")
    if any(v not in ("requirement","context") for v in dispositions.values()):raise ProjectError("invalid passage disposition")
    tasks=p.get("tasks");requirements=p.get("requirements")
    if not isinstance(tasks,list) or not tasks or not isinstance(requirements,list) or not requirements:
        raise ProjectError("nonempty tasks and requirements required")
    ids=set();inputs={brief}
    inputs.update(Path(f) for f in document.get('supporting_files',[]))
    for t in tasks:
        if not isinstance(t,dict) or not isinstance(t.get("id"),str) or not re.fullmatch(r"[A-Za-z0-9_-]+",t["id"]) or t["id"] in ids:
            raise ProjectError("task ids must be unique path-safe strings")
        kind=t.get("kind")
        gates=t.get('requires_pass',[])
        if not isinstance(gates,list) or any(not isinstance(g,str) or g not in ids for g in gates) or len(gates)!=len(set(gates)):
            raise ProjectError('requires_pass must list unique earlier task ids')
        if kind not in ("hvac_regulations","lighting_regulations","electrical_regulations","regulations","route_model","route_optimize","electrical","electrical_fault","electrical_coordination","electrical_lighting","energy","annual_energy","annual_energy_ifc","bim","network","water_network","water_coordination","network_coordination","network_design","network_model_design","pump_operating_point","pump_electrical","lighting","drawing_intake","base_overlay","ifc_clash","ifc_drawing","ifc_route_drawing","ifc_equipment","ifc_native","ifc_views","ifc_views_native","native_cad","manual"):
            raise ProjectError("unknown task adapter")
        if kind in ("electrical","electrical_fault","electrical_coordination","electrical_lighting","energy","annual_energy","annual_energy_ifc","bim","network","water_network","water_coordination","network_design","network_model_design","lighting"):
            inputs.add(local_path(root,t.get("project")))
        if kind=='hvac_regulations':
            dependency=t.get('depends_on')
            if dependency not in ids or next(x for x in tasks if x['id']==dependency)['kind']!='energy':
                raise ProjectError('HVAC regulations require an earlier design-day energy producer')
            if any(k in t for k in ('idf','project','variant')):
                raise ProjectError('HVAC regulations read both producer variants; replacement inputs forbidden')
        if kind in ('regulations','electrical_regulations','lighting_regulations','hvac_regulations'):
            from .regulations import source_paths
            pack=local_path(root,t.get('pack'));project=local_path(root,t.get('basis' if kind=='hvac_regulations' else 'project'))
            directory=t.get('sources')
            if not isinstance(directory,str) or Path(directory).is_absolute():raise ProjectError('relative regulation source directory required')
            directory=(root/directory).resolve()
            if not directory.is_relative_to(root):raise ProjectError('regulation sources escape plan root')
            official=source_paths(read_json(pack),directory)
            if any(not f.is_file() for f in official):raise ProjectError('download required official sources before workflow execution')
            inputs.update({pack,project}|official)
            if kind in ('electrical_regulations','lighting_regulations'):
                inputs.update(local_path(root,t.get(key)) for key in (('topology' if kind=='electrical_regulations' else 'geometry'),'basis'))
        if kind=='water_network':
            from .epanet import validate
            validate(read_json(local_path(root,t['project'])))
        if kind in ('route_model','route_optimize'):
            files=[local_path(root,t.get(key)) for key in ('routing','settings','network')]
            inputs.update(files)
            if kind=='route_model':
                from .route_model import compile_route
                compile_route(*(read_json(f) for f in files))
            else:
                from .route_optimize import select
                select(*(read_json(f) for f in files))
        if kind=='annual_energy':
            from .annual_energy import validate,read_weather
            data=validate(read_json(local_path(root,t['project'])));weather=local_path(root,t.get('weather'));inputs.add(weather)
            read_weather(weather,data['weather'],data['calendar_year'])
        if kind=='lighting':
            from .lighting import validate as validate_lighting
            lighting_project=local_path(root,t.get('project'))
            inputs.update(validate_lighting(read_json(lighting_project),lighting_project.parent))
        if kind=='electrical_coordination':inputs.add(local_path(root,t.get('geometry')))
        if kind=='electrical_fault':
            from .electrical_fault import prepare
            faults=local_path(root,t.get('faults'));inputs.add(faults)
            prepare(read_json(local_path(root,t['project'])),read_json(faults))
        if kind in ('ifc_clash','ifc_drawing','ifc_route_drawing','ifc_views','water_coordination','annual_energy_ifc'):
            if kind=='ifc_clash':
                from .clash import validate_policy
                policy=local_path(root,t.get('policy'));inputs.add(policy);validate_policy(read_json(policy))
            elif kind in ('ifc_drawing','ifc_route_drawing'):
                from .ifc_drawing import validate_settings
                settings=local_path(root,t.get('settings'));inputs.add(settings);validate_settings(read_json(settings))
                if kind=='ifc_route_drawing':
                    from .bim import validate as validate_bim
                    source_model=local_path(root,t.get('model'));inputs.add(source_model);validate_bim(read_json(source_model))
            elif kind=='ifc_views':
                from .ifc_views import validate_settings
                settings=local_path(root,t.get('settings'));inputs.add(settings);validate_settings(read_json(settings))
            elif kind=='annual_energy_ifc':
                from .thermal_binding import validate_contract
                from .annual_energy import read_weather
                binding=local_path(root,t.get('binding'));inputs.add(binding)
                data=read_json(local_path(root,t['project']));validate_contract(data,read_json(binding))
                weather=local_path(root,t.get('weather'));inputs.add(weather)
                read_weather(weather,data['weather'],data['calendar_year'])
            else:
                from .water_binding import validate_contract
                binding=local_path(root,t.get('binding'));inputs.add(binding)
                validate_contract(read_json(local_path(root,t['project'])),read_json(binding))
            if bool(t.get('ifc'))==bool(t.get('depends_on')):raise ProjectError('IFC task requires exactly one source IFC or earlier model dependency')
            if t.get('depends_on'):
                dependency=t['depends_on']
                if dependency not in ids or next(x for x in tasks if x['id']==dependency)['kind'] not in IFC_ARTIFACTS:
                    raise ProjectError('IFC dependency must be an earlier supported IFC producer')
            else:
                ifc_source=local_path(root,t.get('ifc'));inputs.add(ifc_source)
                if ifc_source.suffix.lower()!='.ifc':raise ProjectError('task source must be IFC')
        if kind=='ifc_views_native':
            if bool(t.get('manifest'))==bool(t.get('depends_on')):raise ProjectError('native views require exactly one multiview manifest or earlier producer')
            if t.get('depends_on'):
                if t['depends_on'] not in ids or next(x for x in tasks if x['id']==t['depends_on'])['kind']!='ifc_views':raise ProjectError('native multiview dependency must be an earlier ifc_views task')
            else:
                from .ifc_views import verify_manifest
                manifest=local_path(root,t['manifest']);data=verify_manifest(manifest);inputs.add(manifest)
                inputs.update((manifest.parent/name).resolve() for name in data['artifacts'])
        if kind=='ifc_equipment':
            from .ifc_equipment import validate_settings
            settings=local_path(root,t.get('settings'));inputs.add(settings);validate_settings(read_json(settings))
            dependency=t.get('depends_on')
            if dependency:
                if t.get('ifc') or t.get('report') or dependency not in ids or next(x for x in tasks if x['id']==dependency)['kind']!='annual_energy_ifc':raise ProjectError('equipment drawing dependency must be an earlier IFC annual producer')
            else:
                inputs.add(local_path(root,t.get('ifc')));inputs.add(local_path(root,t.get('report')))
        if kind=='ifc_native':
            from .ifc_native import validate_settings
            settings=local_path(root,t.get('settings'));inputs.add(settings);validate_settings(read_json(settings))
            if bool(t.get('dxf'))==bool(t.get('depends_on')):raise ProjectError('native IFC diagram requires exactly one DXF or earlier drawing dependency')
            if t.get('depends_on'):
                if t['depends_on'] not in ids or next(x for x in tasks if x['id']==t['depends_on'])['kind'] not in ('ifc_drawing','ifc_route_drawing','ifc_equipment'):
                    raise ProjectError('native IFC dependency must be an earlier supported drawing task')
            else:
                diagram_source=local_path(root,t.get('dxf'));inputs.add(diagram_source)
                if diagram_source.suffix.lower()!='.dxf':raise ProjectError('native diagram source must be DXF')
        if kind=='pump_operating_point':
            from .pump import validate_curve,prepare
            curve=local_path(root,t.get('curve'));inputs.add(curve);validate_curve(read_json(curve))
            if bool(t.get('project'))==bool(t.get('depends_on')):raise ProjectError('pump task requires exactly one network input or earlier network producer')
            if t.get('depends_on'):
                if t['depends_on'] not in ids or next(x for x in tasks if x['id']==t['depends_on'])['kind'] not in NETWORK_ARTIFACTS:
                    raise ProjectError('pump dependency must be an earlier supported network producer')
            else:
                pump_network=local_path(root,t.get('project'));inputs.add(pump_network);prepare(read_json(pump_network),read_json(curve))
        if kind=='pump_electrical':
            from .pump_electrical import validate_link
            for key in ('project','network_binding','link'):inputs.add(local_path(root,t.get(key)))
            validate_link(read_json(local_path(root,t['link'])))
            if t.get('depends_on') not in ids or next(x for x in tasks if x['id']==t['depends_on'])['kind']!='pump_operating_point':
                raise ProjectError('pump electrical binding requires an earlier pump operating-point task')
            if t.get('ifc_from') not in ids or next(x for x in tasks if x['id']==t['ifc_from'])['kind'] not in IFC_ARTIFACTS:
                raise ProjectError('pump electrical binding requires an earlier supported IFC producer')
        if kind=='network_design':
            from .network_design import validate_catalogue
            catalogue=local_path(root,t.get('catalogue'));inputs.add(catalogue)
            validate_catalogue(read_json(local_path(root,t['project'])),read_json(catalogue))
        if kind=='network_model_design':
            from .network_model_design import prepare
            files=[local_path(root,t.get(key)) for key in ('project','model','binding','catalogue','geometry')]
            inputs.update(files);prepare(*(read_json(f) for f in files))
        if kind=='drawing_intake':
            drawing=local_path(root,t.get('drawing'));inputs.add(drawing)
            if drawing.suffix.lower() not in ('.dwg','.dxf'):raise ProjectError('drawing intake requires DWG or DXF')
            if t.get('selection'):inputs.add(local_path(root,t['selection']))
        if kind=='base_overlay':
            from .cad_overlay import validate_settings
            for field in ('project','drawing','selection','settings'):inputs.add(local_path(root,t.get(field)))
            validate_settings(read_json(local_path(root,t['settings'])))
            if t.get('sheet'):inputs.add(local_path(root,t['sheet']))
        if kind=='network_coordination':
            from .network_binding import prepare
            model=local_path(root,t.get('model'));binding=local_path(root,t.get('binding'))
            inputs.update((local_path(root,t.get('project')),model,binding))
            prepare(read_json(local_path(root,t.get('project'))),read_json(model),read_json(binding))
        if kind=='electrical_lighting':
            from .lighting_binding import prepare
            ep=local_path(root,t.get('project'));gp=local_path(root,t.get('geometry'));op=local_path(root,t.get('optical'))
            inputs.update((gp,op))
            _,ies_inputs,_,_=prepare(read_json(ep),read_json(gp),read_json(op),op.parent)
            inputs.update(ies_inputs)
        if kind=="native_cad" and t.get("depends_on") not in ids:
            raise ProjectError("native task must depend on an earlier electrical task")
        if kind=="native_cad" and next(x for x in tasks if x["id"]==t["depends_on"])["kind"] not in ('electrical','electrical_coordination','electrical_lighting'):
            raise ProjectError("native task requires electrical or coordinated electrical overlay")
        ids.add(t["id"])
    seen=set();cited=set()
    for r in requirements:
        if not isinstance(r,dict) or not isinstance(r.get("id"),str) or not r["id"] or r["id"] in seen:
            raise ProjectError("unique requirement ids required")
        seen.add(r["id"])
        passage=r.get("passage")
        if not isinstance(passage,str) or passage not in source or dispositions[passage]!="requirement":raise ProjectError("invalid requirement source passage")
        if not isinstance(r.get("quote"),str) or not r["quote"].strip() or r["quote"] not in source[passage]["text"]:
            raise ProjectError("requirement quote does not match source")
        if r.get("task") not in ids:raise ProjectError("unknown requirement task")
        if not isinstance(r.get("acceptance"),str) or not r["acceptance"].strip():raise ProjectError("acceptance description required")
        cited.add(passage)
    if cited!={k for k,v in dispositions.items() if v=="requirement"}:
        raise ProjectError("requirement passage omitted from matrix")
    if {r["task"] for r in requirements}!=ids:raise ProjectError("every task must map to a requirement")
    regulatory_source_bindings(tasks,root)
    return p,inputs


def execute(plan,out,energyplus=None,autocad=None,radiance_bin=None):
    plan,out=plan.resolve(),out.resolve()
    p,inputs=validate_plan(plan);inputs.add(plan)
    if any(out==f or out in f.parents for f in inputs):raise ProjectError("run output must not contain inputs")
    before={str(f):digest(f) for f in inputs}
    out.mkdir(parents=True,exist_ok=False)
    evidence={};tasks={}
    root=plan.parent
    for t in p["tasks"]:
        folder=out/t["id"]
        status="pending";reason="";payload=None
        try:
            if any(not f.is_file() or digest(f)!=before[str(f)] for f in inputs):
                raise ProjectError('workflow source changed before task execution; adapter not executed')
            blocked=[g for g in t.get('requires_pass',[]) if tasks[g]['status']!='pass']
            if blocked:
                reason='required checks unresolved: '+', '.join(g+' ('+tasks[g]['status']+')' for g in blocked)+'; adapter not executed'
            elif t['kind']=='hvac_regulations':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream energy producer '+parent+' did not pass; native regulatory checks not executed'
                else:
                    from .hvac_energy_rules import run
                    payload=run(out/parent,local_path(root,t['basis']),local_path(root,t['pack']),root/t['sources'],folder)
                    status=payload['status'];reason=payload['scope']+'; whole-project conformity not established'
            elif t['kind']=='lighting_regulations':
                from .lighting_regulations import run
                payload=run(*(local_path(root,t[key]) for key in ('project','geometry','basis','pack')),root/t['sources'],folder)
                status=payload['status']
                reason=payload['scope']+'; whole-project regulatory compliance not established'
            elif t['kind']=='electrical_regulations':
                from .electrical_regulations import run
                payload=run(*(local_path(root,t[key]) for key in ('project','topology','basis','pack')),root/t['sources'],folder)
                status=payload['status']
                reason=payload['scope']+'; whole-project regulatory compliance not established'
            elif t['kind']=='regulations':
                from .regulations import run
                payload=run(local_path(root,t['pack']),local_path(root,t['project']),root/t['sources'],folder)
                status='pass' if payload['supported_checks_pass'] else 'pending'
                reason='Selected jurisdiction checks only; whole-project regulatory compliance not established. '+', '.join(r['id']+': '+r['status'] for r in payload['checks'])
            elif t['kind'] in ('route_model','route_optimize'):
                if t['kind']=='route_model':
                    from .route_model import run
                else:
                    from .route_optimize import run
                payload=run(*(local_path(root,t[key]) for key in ('routing','settings','network')),folder)
                status='pass' if payload['calculated_checks_pass'] else 'fail'
                reason='searched finite-radius pipe route, actual saved IFC and prescribed-flow pressure checks; obstacle correspondence, self-clash and complete engineering acceptance remain separate'
            elif t['kind']=='pump_electrical':
                pump_task=t['depends_on'];model_task=t['ifc_from']
                if any(tasks[id]['status']!='pass' for id in (pump_task,model_task)):reason='upstream pump/model did not pass; no electrical operating scenario fabricated'
                else:
                    from .pump_electrical import run
                    source_ifc=out/model_task/IFC_ARTIFACTS[tasks[model_task]['kind']]
                    payload=run(local_path(root,t['project']),out/pump_task/'pump.json',source_ifc,local_path(root,t['network_binding']),local_path(root,t['link']),folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='replayed pump estimate explicitly bound to electrical device/IFC source port; baseline hardware retained; steady scenario and property-only IFC checked; motor/fault/full acceptance pending'
            elif t['kind']=='pump_operating_point':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream network producer did not pass; no pump operating point fabricated'
                else:
                    from .pump import run
                    network_source=out/dependency/NETWORK_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['project'])
                    payload=run(network_source,local_path(root,t['curve']),folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='source-bounded single-terminal pump/system intersection and selected pressure rerun; efficiency, motor, NPSH and full engineering acceptance pending'
            elif t['kind']=='ifc_views_native':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC multiview producer did not pass; no native sheets fabricated'
                elif not autocad:reason='AutoCAD executable not supplied for native IFC multiview set'
                else:
                    from .ifc_views import run_native
                    manifest=out/dependency/'views.json' if dependency else local_path(root,t['manifest'])
                    payload=run_native(manifest,folder,autocad);status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='per-view DWG reopen/GUID audits and fixed-scale PDF references; merged pages retained; actual visual and installation acceptance pending'
            elif t['kind']=='ifc_views':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; no multiview drawing fabricated'
                else:
                    from .ifc_views import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(source,local_path(root,t['settings']),folder);status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='complete per-view segment/end-on symbols and combined axis coverage; true/projected lengths and GUIDs retained; native/physical/visual acceptance separate'
            elif t['kind']=='ifc_equipment':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream HVAC analysis did not pass; no equipment drawing fabricated'
                else:
                    from .ifc_equipment import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    report=out/dependency/'thermal-binding.json' if dependency else local_path(root,t['report'])
                    payload=run(source,report,local_path(root,t['settings']),folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='saved HVAC identity/box geometry/results to plan and equipment schedule; native and installation acceptance separate'
            elif t['kind']=='ifc_native':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC drawing did not pass; no native drawing fabricated'
                elif not autocad:reason='AutoCAD executable not supplied for native IFC diagram'
                else:
                    from .ifc_native import run
                    source=out/dependency/('equipment.dxf' if tasks[dependency]['kind']=='ifc_equipment' else 'segments.dxf') if dependency else local_path(root,t['dxf'])
                    payload=run(source,local_path(root,t['settings']),folder,autocad)
                    status='pass' if payload['native_reopen_pass'] and payload['plot']['pdf_reference_pass'] else 'fail'
                    reason='isolated native DWG reopen, geometry/IFC XDATA reconciliation and physical PDF reference verified; visual/installation acceptance pending'
            elif t['kind']=='water_coordination':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; no water geometry or result fabricated'
                else:
                    from .water_binding import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(local_path(root,t['project']),source,local_path(root,t['binding']),folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='saved IFC GUID/profile/connected reversible routes bound to EPANET; source copy unchanged; physical fittings, product/visual/domain acceptance pending'
            elif t['kind']=='ifc_route_drawing':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; no route drawing fabricated'
                else:
                    from .ifc_route_drawing import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(source,local_path(root,t['model']),local_path(root,t['settings']),folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='source-checked saved circular walls and finite arcs to GUID-linked planar axes/OD outlines; product and installation acceptance pending'
            elif t['kind']=='ifc_drawing':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; no drawing fabricated'
                else:
                    from .ifc_drawing import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(source,local_path(root,t['settings']),folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='saved hollow profiles and ports reconciled to schedule/projected centreline DXF; native and installation drawing acceptance pending'
            elif t['kind']=='ifc_clash':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; no clash result fabricated'
                else:
                    from .clash import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(source,local_path(root,t['policy']),folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='saved IFC triangle clearance plus Manifold3D solid-overlap coverage with sourced contact exceptions; product fidelity and complete acceptance pending'
            elif t['kind']=='base_overlay':
                drawing=local_path(root,t['drawing'])
                if (drawing.suffix.lower()=='.dwg' or t.get('sheet')) and not autocad:reason='AutoCAD required for source DWG or requested fixed-scale sheet'
                else:
                    from .cad_overlay import run
                    payload=run(local_path(root,t['project']),drawing,local_path(root,t['selection']),local_path(root,t['settings']),folder,autocad,
                                local_path(root,t['sheet']) if t.get('sheet') else None)
                    status='pass';reason='supported base entities preserved and electrical devices placed; native/physical PDF checks recorded when requested; full design and visual acceptance pending'
            elif t['kind']=='drawing_intake':
                drawing=local_path(root,t['drawing'])
                if drawing.suffix.lower()=='.dwg' and not autocad:reason='AutoCAD executable not supplied for source DWG extraction'
                else:
                    from .cad_intake import run
                    selected=local_path(root,t['selection']) if t.get('selection') else None
                    payload=run(drawing,folder,selected,autocad)
                    status='pass';reason='read-only drawing inventory and explicitly selected unit-checked geometry; semantic, DWG fidelity and visual acceptance pending'
            elif t['kind']=='electrical_fault':
                from .electrical_fault import run
                payload=run(local_path(root,t['project']),local_path(root,t['faults']),folder)
                status=payload['status'];reason='sourced TN loop/device/energy proof criteria; missing or uncovered guarantees pending; actual code/product/full protection acceptance pending'
            elif t["kind"]=="electrical":
                from .cli import run
                payload=run(local_path(root,t["project"]),folder)
                status="pass" if payload["calculated_checks_pass"] else "fail"
                reason="conditional electrical checks only; remaining design checks are in calculations.json"
            elif t['kind']=='electrical_coordination':
                from .coordination import run
                payload=run(local_path(root,t['project']),local_path(root,t['geometry']),folder)
                status='pass' if payload['calculated_checks_pass'] else 'fail'
                reason='same electrical IDs/XY/power/PF/circuits reconciled across saved calculations, DXF and IFC envelopes; final design acceptance pending'
            elif t['kind']=='electrical_lighting':
                if radiance_bin:
                    from .lighting_binding import run
                    payload=run(local_path(root,t['project']),local_path(root,t['geometry']),local_path(root,t['optical']),folder,radiance_bin)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='shared electrical/CAD/IFC light positions bound to explicit IES origins and Radiance calculation; complete physical/domain acceptance pending'
                else:reason='Radiance binary directory not supplied for bound lighting'
            elif t['kind']=='annual_energy_ifc':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass'
                elif not energyplus:reason='EnergyPlus executable not supplied for IFC-bound annual analysis'
                else:
                    from .thermal_binding import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(local_path(root,t['project']),local_path(root,t['binding']),source,local_path(root,t['weather']),folder,energyplus)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='saved IFC space geometry/GUID coverage bound to actual annual simulation; boundary/material/HVAC/domain acceptance pending'
            elif t['kind']=='annual_energy':
                if energyplus:
                    from .annual_energy import run
                    payload=run(local_path(root,t['project']),local_path(root,t['weather']),folder,energyplus)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='complete hourly EPW calendar and weather-only annual SQL checks; thermal supply and lighting electricity separated; native completion-flag discrepancies retained; real building/plant/domain acceptance pending'
                else:reason='EnergyPlus executable not supplied for annual weather analysis'
            elif t["kind"]=="energy":
                if energyplus:
                    from .energy import run
                    payload=run(local_path(root,t["project"]),folder,energyplus)
                    status="pass";reason="design-day engine execution; no annual energy or physical HVAC routing asserted"
                else:reason="EnergyPlus executable not supplied"
            elif t["kind"]=="bim":
                from .bim import run
                payload=run(local_path(root,t['project']),folder)
                status='pass';reason='IFC4 envelope geometry, schema, spatial/system/port relationships checked; detailed shape and routing acceptance pending'
            elif t['kind']=='network_model_design':
                from .network_model_design import run
                files=[local_path(root,t[key]) for key in ('project','model','binding','catalogue','geometry')]
                payload=run(*files,folder)
                status='pass' if payload['calculated_checks_pass'] else 'fail'
                reason='source-backed envelopes/explicit walls resized on fixed endpoints; saved IFC dimensions and derived pressure reconciled; actual products/clashes/full acceptance pending'
            elif t['kind']=='network_design':
                from .network_design import run
                payload=run(local_path(root,t['project']),local_path(root,t['catalogue']),folder)
                status='pass' if payload['feasible_design_found'] and payload['selected_rerun_pass'] else 'fail'
                reason='exhaustive supplied-catalogue circular tree sizing; failed candidates retained; optimum conditional on fixed route/K/demand and full design acceptance pending'
            elif t['kind']=='network_coordination':
                from .network_binding import run
                payload=run(local_path(root,t['project']),local_path(root,t['model']),local_path(root,t['binding']),folder)
                status='pass' if payload['calculated_checks_pass'] else 'fail'
                reason='IFC port-derived circular route dimensions and prescribed-flow pressure budget; detailed routing and full acceptance pending'
            elif t['kind']=='water_network':
                from .epanet import run
                payload=run(local_path(root,t['project']),folder)
                status='pass' if payload['calculated_checks_pass'] else 'fail'
                reason='steady EPANET water graph, static head, sourced numerical/target checks; route binding, power and full acceptance pending'
            elif t['kind']=='network':
                from .network import run
                payload=run(local_path(root,t['project']),folder)
                status='pass' if payload['calculated_checks_pass'] else 'fail'
                reason='prescribed-demand circular tree flow/pressure budget only; operating point, physical routing and domain acceptance pending'
            elif t['kind']=='lighting':
                if radiance_bin:
                    from .lighting import run
                    payload=run(local_path(root,t['project']),folder,radiance_bin)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='IES-backed Radiance direct/reflected sensor illuminance; source evidence, grid convergence, actual geometry and full lighting acceptance pending'
                else:reason='Radiance binary directory not supplied'
            elif t["kind"]=="native_cad":
                upstream=tasks[t["depends_on"]]
                if upstream["status"]!='pass':reason=f"upstream electrical producer {t['depends_on']} is {upstream['status']}; native conversion waits for passing source evidence"
                elif autocad:
                    from .native_cad import convert,plot
                    base=out/t['depends_on']
                    if upstream['kind']=='electrical_coordination':base=base/'electrical'
                    if upstream['kind']=='electrical_lighting':base=base/'shared'/'electrical'
                    dxf=base/'devices.dxf'
                    payload=convert(dxf,folder,autocad)
                    payload["plot"]=plot(folder/"devices.dwg",dxf,folder/"devices.pdf",autocad)
                    (folder/"native-verification.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
                    status="pass";reason="native reopen/geometry checks and PDF generation; visual acceptance pending"
                else:reason="AutoCAD executable not supplied"
            else:reason=t.get("description","manual engineering/visual verification required")
        except Exception as exc:
            status="fail";reason=f"{type(exc).__name__}: {exc}"
        tasks[t["id"]]=dict(kind=t["kind"],status=status,scope=reason)
        # An executed adapter is evidence for its narrow scope, not every interpreted requirement.
        evidence[t["id"]]=[f.relative_to(out).as_posix() for f in folder.rglob("*") if f.is_file()] if folder.exists() else []
    unchanged=all(f.is_file() and digest(f)==before[str(f)] for f in inputs)
    source_rows={x["id"]:x for x in passages(local_path(root,p["brief"]),local_path(root,p['ocr']) if p.get('ocr') else None)}
    matrix=[]
    for r in p["requirements"]:
        task=tasks[r["task"]]
        matrix.append(dict(**r,execution_status=task["status"],acceptance_status="pending review",
                           source_locator={k:v for k,v in source_rows[r["passage"]].items() if k not in ("id","text")},
                           execution_scope=task["scope"],evidence=evidence[r["task"]]))
    result=dict(inputs=before,inputs_unchanged=unchanged,tasks=tasks,requirements=matrix,
        regulatory_source_bindings=regulatory_source_bindings(p['tasks'],root) if unchanged else [],
        artifact_hashes={f.relative_to(out).as_posix():digest(f) for f in out.rglob("*") if f.is_file()},
        execution_pass=unchanged and all(x["status"]=="pass" for x in tasks.values()),
        design_accepted=False,acceptance_note="Host agent must compare each artifact to the complete acceptance text; execution is not engineering acceptance")
    (out/"workflow.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    rows="".join('<tr><td>'+html.escape(r['id'])+'</td><td>'+html.escape(r['quote'])+'</td><td>'+html.escape(r['execution_status'])+'</td><td>'+html.escape(r['execution_scope'])+'</td><td>Pending review</td></tr>' for r in matrix)
    (out/"index.html").write_text('<!doctype html><meta charset="utf-8"><title>MEP workflow evidence</title><h1>MEP workflow evidence</h1><p>Design acceptance: pending. Source hashes unchanged: '+str(unchanged)+'</p><table border="1"><tr><th>Requirement</th><th>Source quote</th><th>Execution</th><th>Scope</th><th>Acceptance</th></tr>'+rows+'</table>',encoding="utf-8")
    if not unchanged:raise ProjectError("source inputs changed during workflow")
    return result


def verify(run_directory):
    root=run_directory.resolve()
    report=read_json(root/"workflow.json")
    issues=[]
    for name,expected in report["inputs"].items():
        path=Path(name)
        if not path.is_file() or digest(path)!=expected:issues.append(f"input changed or missing: {name}")
    for name,expected in report["artifact_hashes"].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest(path)!=expected:
            issues.append(f"artifact changed or missing: {name}")
    return dict(integrity_pass=not issues,issues=issues,design_accepted=False,
                scope="Recorded inputs and task artifact bytes only; no semantic or engineering acceptance")


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    i=sub.add_parser("intake");i.add_argument("brief",type=Path);i.add_argument("--out",type=Path,required=True)
    i.add_argument('--ocr',type=Path)
    v=sub.add_parser("validate");v.add_argument("plan",type=Path)
    e=sub.add_parser("execute");e.add_argument("plan",type=Path);e.add_argument("--out",required=True,type=Path)
    e.add_argument("--energyplus",type=Path);e.add_argument("--autocad",type=Path)
    e.add_argument('--radiance-bin',type=Path)
    v=sub.add_parser("verify");v.add_argument("run_directory",type=Path)
    a=p.parse_args()
    try:
        if a.command=="intake":
            r=intake(a.brief,a.out,a.ocr)
            print(f"Indexed {len(r['passages'])} source passages; coverage: {r['coverage_status']}; interpretation pending")
            if r["coverage_status"]=="blocked":return 2
        elif a.command=="validate":validate_plan(a.plan);print("Source-linked plan valid; interpretation accuracy still requires review")
        elif a.command=="verify":
            r=verify(a.run_directory);print(json.dumps(r,indent=2))
            if not r["integrity_pass"]:return 2
        else:
            r=execute(a.plan,a.out,a.energyplus,a.autocad,a.radiance_bin)
            print(json.dumps({"tasks":r["tasks"],"design_accepted":False},indent=2))
            if not r["execution_pass"]:return 2
    except (ProjectError,OSError,ValueError) as exc:p.exit(2,str(exc)+"\n")
    return 0

if __name__=="__main__":raise SystemExit(main())
