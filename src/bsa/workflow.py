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

IFC_ARTIFACTS={'rectangular_model_design':'selected-coordination/bim/model.ifc','rectangular_network_binding':'bim/model.ifc','product_alignment':'alignment.ifc','connector_ports':'placed-connector.ifc','cad_ifc':'fitting.ifc','product_ports':'placed-fitting.ifc','tee_selection':'selected/assembly/assembly.ifc','tee_assembly':'assembly.ifc','ifc_metadata':'native/model.ifc','selected_pump_ifc':'selected-model.ifc','regulated_water_model':'selected-coordination/bim/model.ifc','annual_energy_ifc':'analysis.ifc','bim':'model.ifc','network_coordination':'bim/model.ifc',
               'route_model':'bound/bim/model.ifc','route_optimize':'selected/bound/bim/model.ifc',
               'network_model_design':'selected-coordination/bim/model.ifc',
               'electrical_coordination':'bim/model.ifc','electrical_lighting':'shared/bim/model.ifc','pump_electrical':'model.ifc','water_coordination':'model.ifc'}
NETWORK_ARTIFACTS={'regulated_water_model':'selected-coordination/network-input.json','network_coordination':'network-input.json','network_design':'selected-network.json',
                   'network_model_design':'selected-coordination/network-input.json'}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def passages(brief,ocr=None):
    from .documents import extract
    return extract(brief,ocr)["passages"]


def intake(brief,out,ocr=None,supplements=None):
    brief,out=brief.resolve(),out.resolve()
    if out==brief:raise ProjectError("cannot overwrite brief")
    if out.exists():raise ProjectError("refusing to overwrite intake")
    spec=dict(brief=brief.name,brief_sha256=digest(brief))
    if ocr:
        sidecar=ocr.resolve()
        if not sidecar.is_relative_to(brief.parent):
            if supplements:raise ProjectError('bundled OCR must be under brief directory')
        else:spec.update(ocr=sidecar.relative_to(brief.parent).as_posix(),ocr_sha256=digest(sidecar))
    if supplements:
        spec['supplemental_briefs']=[]
        for value in supplements:
            value=value.resolve()
            if not value.is_relative_to(brief.parent):raise ProjectError('supplement must be under brief directory')
            spec['supplemental_briefs'].append(dict(brief=value.relative_to(brief.parent).as_posix(),brief_sha256=digest(value)))
    from .documents import extract
    document=plan_documents(brief.parent,spec) if supplements else extract(brief,ocr)
    if out in {Path(f) for f in document.get('supporting_files',[])}:raise ProjectError('cannot overwrite intake source')
    result=dict(**spec,**document,
        interpretation_status="pending host-agent interpretation",requirements=[])
    result['brief']=str(brief)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def local_path(root,value):
    if not isinstance(value,str) or Path(value).is_absolute():raise ProjectError("plan inputs must use relative paths")
    path=(root/value).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise ProjectError(f"invalid input path: {value}")
    return path


def plan_documents(root,plan):
    """Read every declared brief with independent identity and source coverage."""
    from .documents import extract
    extras=plan.get('supplemental_briefs',[])
    if not isinstance(extras,list):raise ProjectError('supplemental_briefs must be a list')
    specs=[plan]+extras
    documents=[];seen=set();supporting=set()
    for index,spec in enumerate(specs,1):
        if not isinstance(spec,dict) or (index>1 and set(spec)-{'brief','brief_sha256','ocr','ocr_sha256'}):
            raise ProjectError('supplement requires brief/hash and optional OCR/hash only')
        path=local_path(root,spec.get('brief'))
        if path in seen:raise ProjectError('duplicate brief document')
        seen.add(path)
        if digest(path)!=spec.get('brief_sha256'):raise ProjectError('brief hash differs; re-interpret current source')
        ocr=local_path(root,spec['ocr']) if spec.get('ocr') else None
        if ocr and digest(ocr)!=spec.get('ocr_sha256'):raise ProjectError('OCR sidecar changed; re-review transcription')
        doc=extract(path,ocr)
        supporting.add(str(path));supporting.update(doc.get('supporting_files',[]))
        documents.append((path,doc))
    if not extras:
        return documents[0][1]
    rows=[];issues=[];inventory=[]
    for index,(path,doc) in enumerate(documents,1):
        label=path.relative_to(root).as_posix()
        prefix='' if index==1 else f'D{index:03}:'
        inventory.append(dict(id=f'D{index:03}',path=label,sha256=digest(path),format=doc['format']))
        for row in doc['passages']:
            rows.append(dict(row,id=prefix+row['id'],source_document=label,source_sha256=digest(path)))
        for issue in doc['issues']:
            issues.append(dict(issue,id=prefix+issue['id'],locator=dict(issue['locator'],source_document=label)))
    return dict(format='document-bundle',extractor_version='2',documents=inventory,
        passages=rows,issues=issues,supporting_files=sorted(supporting),
        coverage_status='blocked' if any(i['severity']=='blocking' for i in issues)
        else 'needs review' if issues else 'text extracted')


def regulatory_source_bindings(tasks,root):
    """Match known shared-source consumers, including inherited producer inputs."""
    shared={'electrical','electrical_fault','electrical_coordination','electrical_lighting',
            'electrical_regulations','lighting_regulations'}
    geometric={'electrical_coordination','electrical_lighting','lighting_regulations'}
    known={};ancestors={};sources={};bindings=[]
    hashes={};fluid_declarations={}
    def hashed(path):
        if path not in hashes:hashes[path]=digest(path)
        return hashes[path]
    for task in tasks:
        name=task['id'];kind=task['kind']
        parents=[p for p in task.get('requires_pass',[]) if p in known]
        parents += [task[k] for k in ('depends_on','ifc_from','junction_from','connector_from') if isinstance(task.get(k),str) and task[k] in known]
        upstream=set(parents)
        for parent in parents:upstream.update(ancestors[parent])
        ancestors[name]=upstream
        current={}
        if kind in ('epanet_pipe_regulations','circulation_duty','water_network') and not task.get('depends_on'):
            current['circulation']=local_path(root,task.get('project'))
        elif kind in ('plumbing_pump_regulations','pump_operating_point','water_pipe_regulations','network') and not task.get('depends_on'):
            current['network']=local_path(root,task.get('project'))
        elif kind in ('network_coordination','ifc_network'):
            current={field:local_path(root,task[key]) for field,key in (('network_template','project'),('network_model','model'),('network_binding','binding'))}
        elif kind in shared:
            current['project']=local_path(root,task.get('project'))
            if kind in geometric:current['geometry']=local_path(root,task.get('geometry'))
        elif isinstance(task.get('depends_on'),str):
            current=dict(sources.get(task['depends_on'],{}))
        if kind=='plumbing_pump_set':
            from .plumbing_pump_set import inputs as set_inputs
            current={'pump_set':local_path(root,task['project']),'plumbing_basis':local_path(root,task['basis'])}
            for row in set_inputs(current['pump_set'])[1]:
                for field in ('network','curve'):current[row['role']+'_'+field]=row[field]
        if kind in ('plumbing_pump_regulations','pump_operating_point'):
            current['pump_curve']=local_path(root,task.get('curve'))
        if kind=='plumbing_pump_regulations':current['plumbing_basis']=local_path(root,task.get('basis'))
        set_parents=[p for p in upstream if known[p]['kind']=='plumbing_pump_set']
        role_kinds=('network','pump_operating_point','plumbing_pump_regulations','water_pipe_regulations')
        if 'pump_role' in task and (kind not in role_kinds or not set_parents):
            raise ProjectError('pump_role requires a supported consumer and upstream pump-set gate')
        for parent in sorted(upstream):
            if known[parent]['kind'] not in ('plumbing_pump_set','plumbing_pump_regulations','epanet_pipe_regulations','circulation_duty','electrical_regulations','lighting_regulations','water_pipe_regulations'):continue
            if known[parent]['kind']=='plumbing_pump_set' and kind in role_kinds:
                role=task.get('pump_role')
                if role not in ('duty','standby') or 'network' not in current:
                    raise ProjectError('pump-set gate requires explicit pump_role and source network')
                pairs={'network':role+'_network'}
                if kind in ('pump_operating_point','plumbing_pump_regulations'):pairs['pump_curve']=role+'_curve'
                if kind=='plumbing_pump_regulations':pairs['plumbing_basis']='plumbing_basis'
                for field,source_field in pairs.items():
                    checked=sources[parent][source_field];consumed=current[field]
                    if hashed(checked)!=hashed(consumed):
                        raise ProjectError(f'pump-set gate {parent} checks different {role} {field} bytes from consumer {name}')
                    bindings.append(dict(check=parent,consumer=name,field=field,pump_role=role,
                                         checked=str(checked),consumed=str(consumed),sha256=hashed(checked)))
            if (known[parent]['kind']=='plumbing_pump_regulations' and 'network_template' in sources[parent]
                    and kind in ('network','pump_operating_point','plumbing_pump_regulations') and 'network_template' not in current):
                raise ProjectError('derived plumbing gate requires the same inherited network producer; explicit replacement cannot establish correspondence')
            for field in current.keys() & sources[parent].keys():
                checked=sources[parent][field];consumed=current[field]
                if hashed(checked)!=hashed(consumed):
                    raise ProjectError(f'regulatory gate {parent} checks different {field} bytes from consumer {name}')
                bindings.append(dict(check=parent,consumer=name,field=field,checked=str(checked),consumed=str(consumed),sha256=hashed(checked)))
        if kind in ('circulation_duty','epanet_pipe_regulations'):
            from .fluid_bindings import density_declarations,check_density_consistency
            fluid_declarations[name]=density_declarations(task,local_path(root,task.get('basis')))
            check_density_consistency(fluid_declarations[name])
        # Include sibling prerequisites converging on a consumer, not only a chain.
        participants=(upstream|{name}) & fluid_declarations.keys()
        groups={}
        for participant in sorted(participants):
            scenario=current.get('circulation') if participant==name else sources[participant].get('circulation')
            if scenario is not None:groups.setdefault(hashed(scenario),[]).extend(fluid_declarations[participant])
        for scenario_hash,declarations in groups.items():
            from .fluid_bindings import check_density_consistency
            check_density_consistency(declarations)
            if len({q['task'] for q in declarations})>1:
                bindings.append(dict(consumer=name,field='density_consistency',hydraulic_sha256=scenario_hash,declarations=declarations,
                                     basis_hashes={q['basis']:hashed(Path(q['basis'])) for q in declarations}))
        known[name]=task;sources[name]=current
    return bindings


def inventory_source_bindings(tasks,root):
    """Bind supported saved-IFC consumers to upstream inventory checks."""
    electrical_readers={'three_phase_ifc_project','three_phase_ifc','three_phase_topology','three_phase_bend_limits','three_phase_coordination','three_phase_cable_regulations','cable_route_drawing'}
    readers={'connector_ports','ifc_preview','product_ports','tee_drawing','tee_split','tee_pressure','tee_losses','ifc_network','ifc_metadata','ifc_query','ids_check','ifc_clash','ifc_drawing','ifc_route_drawing',
             'ifc_views','water_coordination','annual_energy_ifc'}|electrical_readers
    known={};ancestors={};identities={};bindings=[];rechecks={}
    for task in tasks:
        name=task['id']
        refresh=task.get('refresh_inventory',False)
        if type(refresh) is not bool or 'refresh_inventory' in task and task['kind']!='ifc_query':
            raise ProjectError('refresh_inventory is a Boolean option on ifc_query only')
        parents=set(task.get('requires_pass',[]))
        parents.update(task[k] for k in ('depends_on','ifc_from','junction_from','connector_from') if isinstance(task.get(k),str))
        parents &= known.keys()
        upstream=set(parents)
        for parent in parents:upstream.update(ancestors[parent])
        ancestors[name]=upstream
        superseded=set()
        for parent in upstream:superseded.update(rechecks.get(parent,set()))
        applicable=upstream-(superseded-parents)
        if refresh:rechecks[name]={p for p in upstream if known[p]['kind']=='ifc_query'} | superseded
        derived_plumbing=task['kind']=='plumbing_pump_regulations' and task.get('depends_on') in identities
        if task['kind'] in readers or derived_plumbing:
            if task['kind'] in electrical_readers:identity={'sha256':digest(local_path(root,task['ifc']))}
            elif derived_plumbing:identity=identities[task['depends_on']]
            elif task.get('depends_on'):
                identity={'producer':task['depends_on']}
            else:
                path=local_path(root,task['ifc'])
                identity={'sha256':digest(path)}
            identities[name]=identity
            for parent in sorted(applicable):
                if parent not in identities:continue
                if known[parent]['kind'] not in ('tee_split','tee_pressure','ifc_query','ifc_network','plumbing_pump_regulations') and not (task['kind']=='ifc_preview' and known[parent]['kind']=='ids_check'):continue
                if refresh and known[parent]['kind']=='ifc_query':
                    bindings.append(dict(check=parent,consumer=name,previous_model_identity=identities[parent],model_identity=identity,fresh_inventory_required=True))
                    continue
                if identities[parent]!=identity:
                    raise ProjectError(f'IFC inventory gate {parent} checks a different model from consumer {name}; use the same explicit bytes or inherited producer')
                bindings.append(dict(check=parent,consumer=name,model_identity=identity))
        if refresh:ancestors[name]=set()  # New inventory is the downstream correspondence boundary.
        known[name]=task
    return bindings


def three_phase_rule_bindings(tasks):
    """A drawing cannot borrow a rule pass from a different numerical producer."""
    known={};ancestors={};bindings=[]
    for task in tasks:
        parents=set(task.get('requires_pass',[]))
        parents.update(task[k] for k in ('depends_on','ifc_from','junction_from','connector_from') if isinstance(task.get(k),str))
        parents &= known.keys()
        rules=set()
        for parent in parents:rules.update(ancestors[parent])
        if task['kind'] in ('three_phase_regulations','three_phase_ifc','three_phase_topology','three_phase_bend_limits','three_phase_coordination','three_phase_cable_regulations'):rules.add(task['id'])
        if task['kind'] in ('three_phase_drawing','cable_route_drawing'):
            if task['kind']=='cable_route_drawing' and not {'three_phase_bend_limits','three_phase_coordination'} <= {known[r]['kind'] for r in rules}:
                raise ProjectError('cable route drawing requires bend and coordination release gates')
            for rule_id in sorted(rules):
                if known[rule_id]['depends_on']!=task['depends_on']:raise ProjectError('three-phase rule gate checks a different study from drawing '+task['id'])
                bindings.append(dict(check=rule_id,consumer=task['id'],study_producer=task['depends_on']))
        ancestors[task['id']]=rules;known[task['id']]=task
    return bindings


def three_phase_model_bindings(root,tasks):
    """Native gates must check one exact saved model and cable-role mapping."""
    root=Path(root).resolve()
    known={t['id']:t for t in tasks};native={'three_phase_ifc','three_phase_topology','three_phase_bend_limits','three_phase_coordination','three_phase_cable_regulations','cable_route_drawing'}
    identities={};records=[]
    def identity(task):
        return dict(ifc_sha256=digest(local_path(root,task['ifc'])),
                    geometry_binding_sha256=digest(local_path(root,task['binding'])))
    for task in tasks:
        if task['kind'] not in native:continue
        current=identities[task['id']]=identity(task)
        parent=known[task['depends_on']]
        if parent['kind']=='three_phase_ifc_project':
            if current!=identity(parent):raise ProjectError('native electrical check uses a different IFC or cable binding from derived study '+task['id'])
            records.append(dict(producer=parent['id'],consumer=task['id'],**current))
    drawing_models={t['id']:identities[t['id']] for t in tasks if t['kind']=='cable_route_drawing'}
    for link in three_phase_rule_bindings(tasks):
        if known[link['check']]['kind'] not in native:continue
        current=identities[link['check']];drawing=link['consumer']
        if drawing in drawing_models and drawing_models[drawing]!=current:
            raise ProjectError('electrical drawing prerequisites check different IFC models or cable bindings '+drawing)
        drawing_models[drawing]=current
        records.append(dict(producer=link['check'],consumer=drawing,**current))
    return records


def validate_plan(path):
    root=path.resolve().parent;p=read_json(path)
    if not isinstance(p,dict) or type(p.get("version")) is not int or p.get("version")!=1:raise ProjectError("plan version 1 required")
    brief=local_path(root,p.get("brief"))
    from .documents import check_review
    document=plan_documents(root,p)
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
        if 'allow_failed_baseline' in t and (kind!='circulation_pump_design' or type(t['allow_failed_baseline']) is not bool or not t.get('depends_on')):raise ProjectError('allow_failed_baseline requires inherited pump screening and a boolean')
        gates=t.get('requires_pass',[])
        if not isinstance(gates,list) or any(not isinstance(g,str) or g not in ids for g in gates) or len(gates)!=len(set(gates)):
            raise ProjectError('requires_pass must list unique earlier task ids')
        if kind not in ("rectangular_fan_operating_point","rectangular_fan_regulations","rectangular_drawing","rectangular_model_design","rectangular_network_binding","rectangular_network_design","rectangular_network","three_phase_cable_regulations","cable_route_drawing","three_phase","three_phase_ifc_project","three_phase_ifc","three_phase_topology","three_phase_bend_limits","three_phase_coordination","three_phase_regulations","three_phase_drawing","revit_inventory_check","drainage_input","product_alignment","alignment_native","connector_ports","ifc_preview","cad_ifc","product_ports","tee_selection","tee_assembly","tee_drawing","tee_split","tee_pressure","tee_losses","ifc_network","ifc_metadata","ifc_query","plumbing_pump_set","plumbing_pump_regulations","selected_pump_ifc","ids_check","circulation_pump_design","ifc_circulation_checks","epanet_pipe_regulations","circulation_duty","regulated_water_model","water_pipe_regulations","hvac_regulations","lighting_regulations","electrical_regulations","regulations","route_model","route_optimize","electrical","electrical_fault","electrical_coordination","electrical_lighting","energy","annual_energy","annual_energy_ifc","bim","network","water_network","water_coordination","network_coordination","network_design","network_model_design","pump_operating_point","pump_electrical","lighting","drawing_intake","base_overlay","ifc_clash","ifc_drawing","ifc_route_drawing","ifc_equipment","ifc_native","ifc_views","ifc_views_native","native_cad","manual"):
            raise ProjectError("unknown task adapter")
        if kind in ("electrical","electrical_fault","electrical_coordination","electrical_lighting","energy","annual_energy","annual_energy_ifc","bim","network","rectangular_network","water_network","water_coordination","network_design","network_model_design","lighting"):
            if not (kind in ("water_network","rectangular_network") and t.get("depends_on")):inputs.add(local_path(root,t.get("project")))
        if kind=='rectangular_fan_regulations':
            if set(t)-{'id','kind','depends_on','basis','pack','sources','requires_pass','description'}:raise ProjectError('native fan check inherits rectangular producer; replacement inputs forbidden')
            parent=t.get('depends_on')
            if parent not in ids or next(x for x in tasks if x['id']==parent)['kind'] not in ('rectangular_model_design','rectangular_network_binding'):raise ProjectError('native fan check requires earlier rectangular native producer')
            from . import rectangular_fan_regulations,regulations
            pack=local_path(root,t.get('pack'));directory=t.get('sources')
            if not isinstance(directory,str) or Path(directory).is_absolute() or not (root/directory).resolve().is_relative_to(root):raise ProjectError('plan-local official source directory required')
            official=regulations.source_paths(read_json(pack),root/directory)
            if any(not f.is_file() for f in official):raise ProjectError('download both fan-power official sources before execution')
            inputs.update({pack,local_path(root,t.get('basis')),Path(rectangular_fan_regulations.__file__).resolve()}|official|regulations.method_paths(read_json(pack)))
        if kind=='rectangular_drawing':
            if set(t)-{'id','kind','depends_on','settings','sheet','requires_pass','description'}:raise ProjectError('rectangular drawing inherits model; replacements forbidden')
            parent=t.get('depends_on')
            if parent not in ids or next(x for x in tasks if x['id']==parent)['kind'] not in ('rectangular_model_design','rectangular_network_binding'):raise ProjectError('rectangular drawing requires earlier native rectangular producer')
            if not any(x['id'] in gates and x['kind']=='ifc_clash' and x.get('depends_on')==parent for x in tasks):raise ProjectError('rectangular drawing requires same-model clash prerequisite')
            if any(x['id'] in gates and x['kind']=='rectangular_fan_regulations' and x.get('depends_on')!=parent for x in tasks):raise ProjectError('rectangular drawing fan gate checks a different native producer')
            from . import rectangular_drawing,rectangular_drawing_audit,ifc_native,route_drawing_qa,cad_text_layout
            inputs.update((local_path(root,t.get('settings')),local_path(root,t.get('sheet')),Path(rectangular_drawing.__file__).resolve(),Path(rectangular_drawing_audit.__file__).resolve(),Path(route_drawing_qa.__file__).resolve(),Path(cad_text_layout.__file__).resolve(),Path(ifc_native.__file__).resolve()))
        if kind=='rectangular_model_design':
            if set(t)-{'id','kind','project','model','binding','catalogue','geometry','requires_pass','description'}:raise ProjectError('rectangular model design requires project/model/binding/catalogue/geometry only')
            from . import rectangular_model_design,rectangular_design,rectangular_binding,rectangular_network,network_design,network_model_design,network_binding,network,bim,rectangular_geometry,rectangular_elbow,circular_geometry
            inputs.update(local_path(root,t.get(key)) for key in ('project','model','binding','catalogue','geometry'))
            inputs.update(Path(module.__file__).resolve() for module in (rectangular_model_design,rectangular_design,rectangular_binding,rectangular_network,network_design,network_model_design,network_binding,network,bim,rectangular_geometry,rectangular_elbow,circular_geometry))
        if kind=='rectangular_network_binding':
            if set(t)-{'id','kind','project','model','binding','requires_pass','description'}:raise ProjectError('rectangular binding requires project/model/binding only')
            from . import rectangular_binding,rectangular_network,network_binding,network,bim,rectangular_geometry,rectangular_elbow,circular_geometry
            inputs.update(local_path(root,t.get(key)) for key in ('project','model','binding'))
            inputs.update(Path(module.__file__).resolve() for module in (rectangular_binding,rectangular_network,network_binding,network,bim,rectangular_geometry,rectangular_elbow,circular_geometry))
        if kind=='rectangular_network_design':
            if set(t)-{'id','kind','project','catalogue','requires_pass','description'}:raise ProjectError('rectangular design requires project and catalogue only')
            from . import rectangular_design,rectangular_network,network_design,network
            inputs.update((local_path(root,t.get('project')),local_path(root,t.get('catalogue'))))
            inputs.update(Path(module.__file__).resolve() for module in (rectangular_design,rectangular_network,network_design,network))
        if kind=='rectangular_network':
            if set(t)-{'id','kind','project','depends_on','requires_pass','description'}:raise ProjectError('rectangular network accepts project or selection producer only')
            if t.get('depends_on'):
                if 'project' in t or t['depends_on'] not in ids or next(x for x in tasks if x['id']==t['depends_on'])['kind']!='rectangular_network_design':raise ProjectError('rectangular network requires earlier sizing producer and no replacement project')
            from . import rectangular_network,network
            inputs.update((Path(rectangular_network.__file__).resolve(),Path(network.__file__).resolve()))
        if kind=='three_phase':
            if set(t)-{'id','kind','project','requires_pass','description'}:raise ProjectError('three-phase task requires project only; runtime is an explicit CLI option')
            from .three_phase_bridge import inputs as three_phase_inputs
            inputs.update(three_phase_inputs(local_path(root,t.get('project'))))
        if kind=='three_phase_ifc_project':
            if set(t)-{'id','kind','project','ifc','binding','requires_pass','description'}:raise ProjectError('IFC-derived study requires baseline project, IFC and binding only')
            from . import three_phase_ifc_project,three_phase_ifc
            from .three_phase_bridge import inputs as three_phase_inputs
            project=local_path(root,t.get('project'))
            inputs.update(three_phase_inputs(project))
            inputs.update(three_phase_ifc.inputs(project,local_path(root,t.get('ifc')),local_path(root,t.get('binding'))))
            inputs.add(Path(three_phase_ifc_project.__file__).resolve())
        if kind in ('three_phase_ifc','three_phase_topology','three_phase_bend_limits','three_phase_coordination','three_phase_cable_regulations'):
            if set(t)-({'id','kind','depends_on','ifc','binding','requires_pass','description'}|({'basis','pack','sources'} if kind=='three_phase_cable_regulations' else {'topology'} if kind=='three_phase_topology' else {'basis'} if kind=='three_phase_bend_limits' else {'policy'} if kind=='three_phase_coordination' else set())):raise ProjectError('three-phase IFC inherits study; replacement project forbidden')
            parent=t.get('depends_on')
            if not isinstance(parent,str) or parent not in ids or next(x for x in tasks if x['id']==parent)['kind'] not in ('three_phase','three_phase_ifc_project'):raise ProjectError('three-phase IFC requires an earlier three_phase study')
            from . import three_phase_ifc,three_phase_drawing
            producer=next(x for x in tasks if x['id']==parent)
            inputs.update(three_phase_ifc.inputs(local_path(root,producer['project']),local_path(root,t.get('ifc')),local_path(root,t.get('binding'))))
            inputs.add(Path(three_phase_drawing.__file__).resolve())
            if kind=='three_phase_topology':
                from .three_phase_topology import inputs as topology_inputs
                inputs.update(topology_inputs(local_path(root,producer['project']),local_path(root,t['ifc']),local_path(root,t['binding']),local_path(root,t.get('topology'))))
            if kind=='three_phase_bend_limits':
                from .cable_bend_limits import prepare as prepare_bend_limits
                _,limit_inputs=prepare_bend_limits(local_path(root,t.get('basis')))
                inputs.update(limit_inputs)
            if kind=='three_phase_coordination':
                from .three_phase_coordination import inputs as coordination_inputs
                inputs.update(coordination_inputs(local_path(root,producer['project']),local_path(root,t['ifc']),local_path(root,t['binding']),local_path(root,t.get('policy'))))
            if kind=='three_phase_cable_regulations':
                from . import cable_bend_regulations,cable_bend_rules,regulations
                _,basis_files=cable_bend_regulations.prepare(local_path(root,t.get('basis')))
                pack=local_path(root,t.get('pack'));directory=t.get('sources')
                if not isinstance(directory,str) or Path(directory).is_absolute() or not (root/directory).resolve().is_relative_to(root):raise ProjectError('contained official-source directory required')
                inputs.update(basis_files|regulations.source_paths(read_json(pack),root/directory)|{pack,Path(cable_bend_rules.__file__).resolve(),Path(regulations.__file__).resolve()})
        if kind=='three_phase_drawing':
            if set(t)-{'id','kind','depends_on','requires_pass','description'}:raise ProjectError('three-phase drawing inherits its study; replacement project/settings forbidden')
            parent=t.get('depends_on')
            if not isinstance(parent,str) or parent not in ids or next(x for x in tasks if x['id']==parent)['kind'] not in ('three_phase','three_phase_ifc_project'):
                raise ProjectError('three-phase drawing requires an earlier three_phase study')
            from . import three_phase_drawing
            inputs.add(Path(three_phase_drawing.__file__).resolve())
        if kind=='cable_route_drawing':
            if set(t)-{'id','kind','depends_on','ifc','binding','settings','native_settings','obstacles','requires_pass','description'}:raise ProjectError('cable route drawing inherits its study; replacement project forbidden')
            parent=t.get('depends_on')
            if not isinstance(parent,str) or parent not in ids or next(x for x in tasks if x['id']==parent)['kind']!='three_phase_ifc_project':raise ProjectError('cable route drawing requires earlier IFC-derived study')
            from . import cable_route_drawing,three_phase_ifc,ifc_native,three_phase_drawing
            from .ifc_drawing import validate_settings as drawing_settings
            producer=next(x for x in tasks if x['id']==parent)
            inputs.update(three_phase_ifc.inputs(local_path(root,producer['project']),local_path(root,t.get('ifc')),local_path(root,t.get('binding'))))
            for field,validator in (('settings',drawing_settings),('native_settings',ifc_native.validate_settings)):
                path=local_path(root,t.get(field));inputs.add(path);validator(read_json(path))
            inputs.update(Path(m.__file__).resolve() for m in (cable_route_drawing,ifc_native,three_phase_drawing))
            from .cable_route_audit import inputs as cable_audit_inputs
            inputs.update(cable_audit_inputs())
            if 'obstacles' in t:
                from .obstacle_projection import inputs as obstacle_inputs
                inputs.update(obstacle_inputs(local_path(root,t['obstacles'])))
        if kind=='three_phase_regulations':
            if set(t)-{'id','kind','depends_on','basis','pack','sources','requires_pass','description'}:raise ProjectError('three-phase rules inherit study; replacement project forbidden')
            parent=t.get('depends_on')
            if not isinstance(parent,str) or parent not in ids or next(x for x in tasks if x['id']==parent)['kind'] not in ('three_phase','three_phase_ifc_project'):raise ProjectError('three-phase rules require earlier three_phase study')
            from . import three_phase_regulations,three_phase_drawing
            _,basis_files=three_phase_regulations.basis_inputs(local_path(root,t.get('basis')))
            pack=local_path(root,t.get('pack'));directory=t.get('sources')
            if not isinstance(directory,str) or Path(directory).is_absolute() or not (root/directory).resolve().is_relative_to(root):raise ProjectError('relative plan-local official source directory required')
            from .regulations import source_paths
            official=source_paths(read_json(pack),(root/directory).resolve())
            if any(not f.is_file() for f in official):raise ProjectError('download required official sources before workflow execution')
            inputs.update(basis_files|official|{pack,Path(three_phase_regulations.__file__).resolve(),Path(three_phase_drawing.__file__).resolve()})
        if kind=='revit_inventory_check':
            if set(t)-{'id','kind','inventory','model','tolerance_m','requires_pass','description'}:
                raise ProjectError('Revit check requires explicit saved inventory/model and tolerance')
            import math
            tolerance=t.get('tolerance_m')
            if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or tolerance<=0:
                raise ProjectError('Revit check requires a positive finite tolerance in metres')
            inputs.update(local_path(root,t.get(k)) for k in ('inventory','model'))
        if kind=='drainage_input':
            if set(t)-{'id','kind','project','requires_pass','description'}:
                raise ProjectError('drainage preparation requires explicit project only')
            inputs.add(local_path(root,t.get('project')))
        if kind=='product_alignment':
            if set(t)-{'id','kind','junction_from','connector_from','basis','requires_pass','description'}:
                raise ProjectError('alignment inherits source placement tasks; replacement inputs forbidden')
            for field,expected in (('junction_from','product_ports'),('connector_from','connector_ports')):
                parent=t.get(field)
                if parent not in ids or next(x for x in tasks if x['id']==parent)['kind']!=expected:
                    raise ProjectError('alignment requires earlier matching placement producers')
            inputs.add(local_path(root,t.get('basis')))
        if kind=='alignment_native':
            if set(t)-{'id','kind','depends_on','requires_pass','description'}:
                raise ProjectError('native comparison inherits alignment and both source bundles')
            parent=t.get('depends_on')
            if parent not in ids or next(x for x in tasks if x['id']==parent)['kind']!='product_alignment':
                raise ProjectError('native comparison requires earlier product alignment')
        if kind=='cad_ifc':
            if set(t)-{'id','kind','drawing','basis','requires_pass','description'}:
                raise ProjectError('CAD IFC uses explicit drawing/basis and the workflow engine only')
            inputs.update(local_path(root,t.get(k)) for k in ('drawing','basis'))
        if kind=='connector_ports':
            if set(t)-{'id','kind','depends_on','basis','requires_pass','description'}:
                raise ProjectError('connector ports inherit conversion; replacement inputs forbidden')
            parent=t.get('depends_on')
            if parent not in ids or next(x for x in tasks if x['id']==parent)['kind']!='cad_ifc':
                raise ProjectError('connector ports require an earlier cad_ifc producer')
            inputs.add(local_path(root,t.get('basis')))
        if kind=='product_ports':
            if set(t)-{'id','kind','depends_on','basis','requires_pass','description'}:
                raise ProjectError('product ports inherit the conversion; replacement inputs forbidden')
            parent=t.get('depends_on')
            if parent not in ids or next(x for x in tasks if x['id']==parent)['kind']!='cad_ifc':
                raise ProjectError('product ports require an earlier cad_ifc producer')
            basis=local_path(root,t.get('basis'));inputs.add(basis)
            nested=read_json(basis).get('passage_basis')
            if not isinstance(nested,str) or Path(nested).is_absolute():
                raise ProjectError('relative product passage basis required')
            inputs.add(local_path(root,str(basis.relative_to(root).parent/nested)))
        if kind=='tee_selection':
            from .tee_selection import prepare
            _,_,selection_files=prepare(local_path(root,t.get('catalogue')));inputs.update(selection_files)
            if any(k in t for k in ('depends_on','ifc','tee_spec','assembly_spec','basis','control')):raise ProjectError('selection inherits only catalogue sources')
        if kind=='tee_assembly':
            inputs.update(local_path(root,t.get(k)) for k in ('tee_spec','assembly_spec'))
            if any(k in t for k in ('depends_on','ifc')):raise ProjectError('tee assembly uses explicit source specs')
        if kind in ('tee_losses','tee_pressure','tee_split','tee_drawing'):
            parent=t.get('depends_on')
            if parent not in ids or next(x for x in tasks if x['id']==parent)['kind'] not in (('tee_assembly','tee_selection') if kind=='tee_drawing' else ('tee_assembly',)):
                raise ProjectError('tee losses require an earlier tee_assembly')
            if any(k in t for k in ('ifc','model','tee_spec','assembly_spec')):
                raise ProjectError('tee losses inherit producer IFC and specs; replacement inputs forbidden')
            if kind!='tee_drawing':inputs.add(local_path(root,t.get('basis')))
            if kind=='tee_split':inputs.add(local_path(root,t.get('control')))
        if kind=='hvac_regulations':
            dependency=t.get('depends_on')
            if dependency not in ids or next(x for x in tasks if x['id']==dependency)['kind']!='energy':
                raise ProjectError('HVAC regulations require an earlier design-day energy producer')
            if any(k in t for k in ('idf','project','variant')):
                raise ProjectError('HVAC regulations read both producer variants; replacement inputs forbidden')
        if kind in ('plumbing_pump_set','plumbing_pump_regulations','epanet_pipe_regulations','regulations','electrical_regulations','lighting_regulations','hvac_regulations','water_pipe_regulations','regulated_water_model'):
            from .regulations import source_paths
            pack=local_path(root,t.get('pack'));project=local_path(root,t.get('basis' if kind=='hvac_regulations' or kind in ('water_pipe_regulations','plumbing_pump_regulations') and t.get('depends_on') else 'project'))
            directory=t.get('sources')
            if not isinstance(directory,str) or Path(directory).is_absolute():raise ProjectError('relative regulation source directory required')
            directory=(root/directory).resolve()
            if not directory.is_relative_to(root):raise ProjectError('regulation sources escape plan root')
            official=source_paths(read_json(pack),directory)
            if any(not f.is_file() for f in official):raise ProjectError('download required official sources before workflow execution')
            inputs.update({pack,project}|official)
            from .regulations import method_paths
            inputs.update(method_paths(read_json(pack)))
            if kind in ('electrical_regulations','lighting_regulations'):
                inputs.update(local_path(root,t.get(key)) for key in (('topology' if kind=='electrical_regulations' else 'geometry'),'basis'))
        if kind=='plumbing_pump_regulations':
            if t.get('depends_on'):
                parent=t['depends_on']
                if parent not in ids or next(x for x in tasks if x['id']==parent)['kind'] not in ('network_coordination','ifc_network'):raise ProjectError('derived plumbing capacity requires earlier network_coordination or ifc_network')
                if any(k in t for k in ('project','model','binding','ifc','producer')):raise ProjectError('derived plumbing capacity inherits original inputs; replacements forbidden')
            inputs.update(local_path(root,t.get(key)) for key in ('curve','basis'))
        if kind=='plumbing_pump_set':
            from .plumbing_pump_set import inputs as pump_set_inputs
            if t.get('depends_on'):raise ProjectError('pump set requires explicit sourced scenarios; inheritance unsupported')
            inputs.update(pump_set_inputs(local_path(root,t.get('project')))[2])
            inputs.add(local_path(root,t.get('basis')))
        if kind=='circulation_pump_design':
            from .circulation_pump_design import candidates
            from .regulations import source_paths
            catalogue=local_path(root,t.get('catalogue'));pack=local_path(root,t.get('pack'))
            parent=t.get('depends_on')
            if parent:
                if parent not in ids or next(x for x in tasks if x['id']==parent)['kind']!='water_coordination' or 'project' in t:raise ProjectError('inherited pump screening requires earlier water_coordination and no replacement project')
                producer=next(x for x in tasks if x['id']==parent)
                project=local_path(root,producer['project'])
            else:project=local_path(root,t.get('project'))
            if not parent:candidates(read_json(project),read_json(catalogue))
            directory=t.get('sources')
            if not isinstance(directory,str) or Path(directory).is_absolute():raise ProjectError('relative regulation source directory required')
            directory=(root/directory).resolve()
            if not directory.is_relative_to(root):raise ProjectError('regulation sources escape plan root')
            official=source_paths(read_json(pack),directory)
            if any(not f.is_file() for f in official):raise ProjectError('download required official sources before workflow execution')
            inputs.update({project,catalogue,pack,local_path(root,t.get('thermal_basis')),local_path(root,t.get('rule_basis'))}|official)
        if kind=='selected_pump_ifc':
            parent=t.get('depends_on')
            if parent not in ids or next(x for x in tasks if x['id']==parent)['kind']!='circulation_pump_design':raise ProjectError('selected IFC requires earlier pump screening')
            screen=next(x for x in tasks if x['id']==parent)
            if not screen.get('depends_on'):raise ProjectError('selected IFC requires screening inherited from water_coordination')
            if any(k in t for k in ('project','ifc','template','binding','catalogue','producer','screening','ifc_from')):raise ProjectError('selected IFC inherits all inputs; replacements forbidden')
        if kind=='ifc_circulation_checks':
            parent=t.get('depends_on')
            if parent not in ids or next(x for x in tasks if x['id']==parent)['kind'] not in ('water_coordination','selected_pump_ifc'):raise ProjectError('IFC circulation checks require earlier water_coordination or selected_pump_ifc')
            if any(k in t for k in ('project','template','binding','ifc','producer')):raise ProjectError('IFC circulation checks inherit producer inputs; replacements forbidden')
            from .regulations import source_paths
            pack=local_path(root,t.get('pack'))
            directory=t.get('sources')
            if not isinstance(directory,str) or Path(directory).is_absolute():raise ProjectError('relative regulation source directory required')
            directory=(root/directory).resolve()
            if not directory.is_relative_to(root):raise ProjectError('regulation sources escape plan root')
            official=source_paths(read_json(pack),directory)
            if any(not f.is_file() for f in official):raise ProjectError('download required official sources before workflow execution')
            inputs.update({pack,local_path(root,t.get('thermal_basis')),local_path(root,t.get('rule_basis'))}|official)
        if kind=='epanet_pipe_regulations':
            from .epanet import validate as validate_water
            validate_water(read_json(local_path(root,t['project'])))
            inputs.add(local_path(root,t.get('basis')))
            if t.get('depends_on'):raise ProjectError('EPANET rules require explicit project; depends_on unsupported')
        if kind=='water_pipe_regulations':
            if t.get('depends_on'):
                parent=t['depends_on']
                if t.get('project') or parent not in ids or next(x for x in tasks if x['id']==parent)['kind']!='network_coordination':raise ProjectError('derived water rules require earlier network_coordination and no replacement project')
            inputs.add(local_path(root,t.get('basis')))
        if kind=='circulation_duty':
            from .circulation_duty import validate as validate_duty
            from .epanet import validate as validate_water
            project=local_path(root,t.get('project'));basis=local_path(root,t.get('basis'))
            if t.get('depends_on'):raise ProjectError('circulation duty executes fresh project; depends_on not supported')
            inputs.update((project,basis))
            validate_duty(read_json(basis),validate_water(read_json(project)))
        if kind=='water_network':
            if t.get('depends_on'):
                parent=t['depends_on']
                if parent not in ids or next(x for x in tasks if x['id']==parent)['kind']!='circulation_pump_design' or 'project' in t:raise ProjectError('selected water network requires earlier pump screening and no replacement project')
            else:
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
        if kind in ('ifc_preview','ifc_network','ifc_metadata','ifc_query','ids_check','ifc_clash','ifc_drawing','ifc_route_drawing','ifc_views','water_coordination','annual_energy_ifc'):
            if kind=='ifc_preview':
                if set(t)-{'id','kind','guid','ifc','depends_on','requires_pass','description'}:
                    raise ProjectError('unexpected IFC preview task fields')
                if not isinstance(t.get('guid'),str) or len(t['guid'])!=22:
                    raise ProjectError('explicit IFC preview GlobalId required')
            elif kind=='ifc_network':
                from .network_binding import prepare
                network_paths=[local_path(root,t.get(k)) for k in ('project','model','binding')]
                inputs.update(network_paths);prepare(*(read_json(p) for p in network_paths))
            elif kind=='ifc_metadata':
                inputs.add(local_path(root,t.get('patch')))
            elif kind=='ifc_query':
                from .ifc_query import validate
                query_requirements=local_path(root,t.get('requirements'));inputs.add(query_requirements);validate(read_json(query_requirements))
            elif kind=='ids_check':
                inputs.add(local_path(root,t.get('ids')))
            elif kind=='ifc_clash':
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
                if t['depends_on'] not in ids or next(x for x in tasks if x['id']==t['depends_on'])['kind'] not in ('tee_drawing','ifc_drawing','ifc_route_drawing','ifc_equipment'):
                    raise ProjectError('native IFC dependency must be an earlier supported drawing task')
            else:
                diagram_source=local_path(root,t.get('dxf'));inputs.add(diagram_source)
                if diagram_source.suffix.lower()!='.dxf':raise ProjectError('native diagram source must be DXF')
        if kind=='rectangular_fan_operating_point':
            from . import rectangular_fan,rectangular_network,pump,network,rectangular_fan_binding,rectangular_binding
            if set(t)-{'id','kind','project','depends_on','curve','requires_pass','description'}:raise ProjectError('fan inherits native inputs; replacement model/study forbidden')
            curve=local_path(root,t.get('curve'));inputs.add(curve);rectangular_fan.validate_curve(read_json(curve))
            inputs.update(Path(m.__file__).resolve() for m in (rectangular_fan,rectangular_network,pump,network,rectangular_fan_binding,rectangular_binding))
            if t.get('depends_on'):
                parent=t['depends_on']
                if 'project' in t or parent not in ids or next(x for x in tasks if x['id']==parent)['kind'] not in ('rectangular_model_design','rectangular_network_binding'):raise ProjectError('native fan needs earlier rectangular producer and no replacement project')
            else:
                project=local_path(root,t.get('project'));inputs.add(project)
                rectangular_fan.prepare(read_json(project),read_json(curve))
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
        if kind=='regulated_water_model':
            inputs.update(local_path(root,t.get(key)) for key in ('basis','classifications'))
        if kind in ('network_model_design','regulated_water_model'):
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
    from .input_issues import validate as validate_inputs
    validate_inputs(p,source,ids)
    regulatory_source_bindings(tasks,root)
    inventory_source_bindings(tasks,root)
    three_phase_rule_bindings(tasks)
    three_phase_model_bindings(root,tasks)
    return p,inputs


def screening_project(task,tasks,root,out):
    """Resolve the exact screening scenario; reconcile inherited saved geometry."""
    parent=task.get('depends_on')
    if not parent:return local_path(root,task['project'])
    from .ifc_circulation_checks import verify_producer
    producer=next(x for x in tasks if x['id']==parent)
    verify_producer(out/parent,local_path(root,producer['project']),local_path(root,producer['binding']))
    return out/parent/'network-input.json'


def three_phase_locations(root,out,producer):
    """Resolve inseparable project/study paths from a validated producer kind."""
    if producer['kind']=='three_phase_ifc_project':return out/producer['id']/'project.json',out/producer['id']/'study'
    if producer['kind']=='three_phase':return local_path(root,producer['project']),out/producer['id']
    raise ProjectError('not a three-phase numerical producer')


def execute(plan,out,energyplus=None,autocad=None,radiance_bin=None,ifcmcp_python=None,three_phase_python=None,graphviz=None):
    plan,out=plan.resolve(),out.resolve()
    p,inputs=validate_plan(plan);inputs.add(plan)
    if any(out==f or out in f.parents for f in inputs):raise ProjectError("run output must not contain inputs")
    before={str(f):digest(f) for f in inputs}
    out.mkdir(parents=True,exist_ok=False)
    evidence={};tasks={};three_phase_pins={};three_phase_rule_pins={};rectangular_pins={}
    root=plan.parent
    for t in p["tasks"]:
        folder=out/t["id"]
        status="pending";reason="";payload=None
        try:
            if any(not f.is_file() or digest(f)!=before[str(f)] for f in inputs):
                raise ProjectError('workflow source changed before task execution; adapter not executed')
            for parent in [t.get('depends_on'),*t.get('requires_pass',[])]:
                if parent in rectangular_pins and any(not Path(f).is_file() or digest(Path(f))!=sha for f,sha in rectangular_pins[parent].items()):raise ProjectError('rectangular producer artifacts changed before consumer execution')
            blocked=[g for g in t.get('requires_pass',[]) if tasks[g]['status']!='pass']
            from .input_issues import blockers
            missing_inputs=blockers(p,t['id'])
            if missing_inputs:
                reason='unresolved design inputs: '+', '.join(i['id']+' ('+i['kind']+'): '+i['description'] for i in missing_inputs)+'; adapter not executed'
            elif blocked:
                reason='required checks unresolved: '+', '.join(g+' ('+tasks[g]['status']+')' for g in blocked)+'; adapter not executed'
            elif t['kind']=='three_phase':
                if not three_phase_python:reason='Three-phase isolated Python runtime not supplied; adapter not executed'
                else:
                    from .three_phase_bridge import run as run_three_phase
                    payload=run_three_phase(local_path(root,t['project']),folder,three_phase_python)
                    status=payload['status'];reason=payload['scope']
                    three_phase_pins[t['id']]={str(f):digest(f) for f in folder.rglob('*') if f.is_file()}
            elif t['kind']=='three_phase_ifc_project':
                if not three_phase_python:reason='Three-phase isolated Python runtime not supplied; IFC-derived study not executed'
                else:
                    from .three_phase_ifc_project import run as derive_three_phase
                    payload=derive_three_phase(local_path(root,t['project']),local_path(root,t['ifc']),local_path(root,t['binding']),folder,three_phase_python)
                    if payload.get('derived_geometry_correspondence_pass') is not True or payload.get('design_accepted') is not False or payload.get('numerical_status') not in ('pass','fail'):raise ProjectError('invalid IFC-derived study result')
                    status=payload['numerical_status'];reason=payload['scope']
                    three_phase_pins[t['id']]={str(f):digest(f) for f in folder.rglob('*') if f.is_file()}
            elif t['kind'] in ('three_phase_ifc','three_phase_topology','three_phase_bend_limits','three_phase_coordination','three_phase_cable_regulations'):
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream three-phase study '+parent+' did not pass; IFC binding not executed'
                else:
                    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in three_phase_pins[parent].items()):raise ProjectError('three-phase producer artifacts changed before IFC binding')
                    from .three_phase_ifc import run as check_cable_ifc
                    from .three_phase_drawing import context as study_context
                    producer=next(x for x in p['tasks'] if x['id']==parent)
                    project,study_folder=three_phase_locations(root,out,producer)
                    _,_,study_sources=study_context(project,study_folder)
                    if t['kind']=='three_phase_bend_limits':
                        from .cable_bend_limits import run as check_bend_limits
                        payload=check_bend_limits(project,local_path(root,t['ifc']),local_path(root,t['binding']),local_path(root,t['basis']),folder)
                        if payload.get('status') not in ('pass','fail','pending') or payload.get('manufacturer_selection_verified') is not False:raise ProjectError('invalid bend-limit result')
                    elif t['kind']=='three_phase_cable_regulations':
                        from .cable_bend_regulations import run as check_cable_rules
                        payload=check_cable_rules(project,local_path(root,t['ifc']),local_path(root,t['binding']),local_path(root,t['basis']),local_path(root,t['pack']),root/t['sources'],folder)
                        if payload.get('status') not in ('pass','fail','pending') or payload.get('regulatory_compliance')!='not_established':raise ProjectError('invalid scoped cable-rule result')
                    elif t['kind']=='three_phase_coordination':
                        from .three_phase_coordination import run as check_coordination
                        payload=check_coordination(project,local_path(root,t['ifc']),local_path(root,t['binding']),local_path(root,t['policy']),folder)
                        checks=payload.get('clash_checks',{})
                        if set(checks)!={'geometry_coverage','no_intersections','clearance'} or any(type(v) is not bool for v in checks.values()) or payload.get('status')!=('pass' if all(checks.values()) else 'fail'):raise ProjectError('invalid electrical coordination result')
                    elif t['kind']=='three_phase_topology':
                        from .three_phase_topology import run as check_topology
                        payload=check_topology(project,local_path(root,t['ifc']),local_path(root,t['binding']),local_path(root,t['topology']),folder)
                        if payload.get('native_port_relationships_pass') is not True or payload.get('logical_graph_correspondence_pass') is not True:raise ProjectError('native electrical graph correspondence did not pass')
                    else:payload=check_cable_ifc(project,local_path(root,t['ifc']),local_path(root,t['binding']),folder)
                    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in study_sources.items()):raise ProjectError('study changed during IFC binding')
                    if payload.get('geometry_correspondence_pass') is not True or payload.get('design_accepted') is not False:raise ProjectError('invalid IFC correspondence result')
                    status=payload['status'] if t['kind'] in ('three_phase_bend_limits','three_phase_coordination','three_phase_cable_regulations') else 'pass';reason=payload['scope']
                    three_phase_rule_pins[t['id']]={str(f):digest(f) for f in folder.rglob('*') if f.is_file()}
            elif t['kind']=='cable_route_drawing':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream IFC-derived electrical study did not pass; route drawing not executed'
                elif not autocad:reason='AutoCAD executable not supplied; cable route delivery not executed'
                else:
                    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in three_phase_pins[parent].items()):raise ProjectError('three-phase producer artifacts changed before route drawing')
                    for binding in three_phase_rule_bindings(p['tasks']):
                        if binding['consumer']==t['id'] and any(not Path(f).is_file() or digest(Path(f))!=h for f,h in three_phase_rule_pins[binding['check']].items()):raise ProjectError('three-phase rule artifacts changed before route drawing')
                    from .cable_route_drawing import run as draw_route
                    from .three_phase_drawing import context as study_context
                    from .ifc_native import run as native_route
                    producer=next(x for x in p['tasks'] if x['id']==parent)
                    project,study_folder=three_phase_locations(root,out,producer)
                    _,_,study_sources=study_context(project,study_folder)
                    payload=draw_route(project,local_path(root,t['ifc']),local_path(root,t['binding']),local_path(root,t['settings']),folder,obstacles=local_path(root,t['obstacles']) if 'obstacles' in t else None)
                    payload['native']=native_route(folder/'cable-route.dxf',local_path(root,t['native_settings']),folder/'native',autocad)
                    from .cable_route_audit import audit_saved as audit_cable
                    payload['native_saved_audit']=audit_cable(folder/'native/native-reopen/source-export.dxf',payload['cable'],payload['geometry'],payload['settings'],payload['obstacles'])
                    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in study_sources.items()):raise ProjectError('study changed during cable route delivery')
                    if payload['saved_identity_and_geometry_pass'] is not True or payload['native']['native_reopen_pass'] is not True or payload['native']['plot']['pdf_reference_pass'] is not True:raise ProjectError('cable route native/plot verification did not pass')
                    payload['study_sources']=study_sources
                    (folder/'workflow-drawing.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
                    status='pass';reason=payload['scope']+'; actual visual/engineering review remains pending'
            elif t['kind']=='three_phase_drawing':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream three-phase study '+parent+' did not pass; drawing not executed'
                elif not graphviz:reason='Graphviz executable not supplied; native three-phase drawing not executed'
                elif not autocad:reason='AutoCAD executable not supplied; native three-phase drawing not executed'
                else:
                    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in three_phase_pins[parent].items()):raise ProjectError('three-phase producer artifacts changed before drawing')
                    for binding in three_phase_rule_bindings(p['tasks']):
                        if binding['consumer']==t['id'] and any(not Path(f).is_file() or digest(Path(f))!=h for f,h in three_phase_rule_pins[binding['check']].items()):raise ProjectError('three-phase rule artifacts changed before drawing')
                    from .three_phase_drawing import run as draw_three_phase
                    producer=next(x for x in p['tasks'] if x['id']==parent)
                    project,study_folder=three_phase_locations(root,out,producer)
                    payload=draw_three_phase(project,study_folder,folder,graphviz,autocad)
                    if payload.get('dxf_identity_pass') is not True or payload.get('native',{}).get('native_reopen_pass') is not True or payload['native']['plot'].get('pdf_reference_pass') is not True:
                        raise ProjectError('three-phase native/plot verification did not pass')
                    status='pass';reason=payload['scope']+'; actual page visual/engineering review remains pending'
            elif t['kind']=='three_phase_regulations':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream three-phase study '+parent+' did not pass; regulatory binding not executed'
                else:
                    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in three_phase_pins[parent].items()):raise ProjectError('three-phase producer artifacts changed before rules')
                    from .three_phase_regulations import run as phase_rules
                    producer=next(x for x in p['tasks'] if x['id']==parent)
                    project,study_folder=three_phase_locations(root,out,producer)
                    payload=phase_rules(project,study_folder,local_path(root,t['basis']),local_path(root,t['pack']),root/t['sources'],folder)
                    status=payload['status'];reason=payload['scope']
                    three_phase_rule_pins[t['id']]={str(f):digest(f) for f in folder.rglob('*') if f.is_file()}
            elif t['kind']=='revit_inventory_check':
                from .revit_connectivity import run
                payload=run(local_path(root,t['inventory']),local_path(root,t['model']),folder/'diagnosis.json',t['tolerance_m'])
                status=payload['diagnostic_status'];reason=payload['scope']+'; native host and complete-system acceptance remain pending'
            elif t['kind']=='drainage_input':
                from .drainage_input import run
                payload=run(local_path(root,t['project']),folder)
                status='pass';reason=payload['scope']+'; model preparation only, native parse and simulation unverified'
            elif t['kind']=='water_pipe_regulations':
                if t.get('depends_on'):
                    parent=t['depends_on']
                    if tasks[parent]['status']!='pass':reason='upstream coordinated network did not pass; regulatory check not executed'
                    else:
                        from .ifc_water_rules import run
                        producer=next(x for x in p['tasks'] if x['id']==parent)
                        payload=run(out/parent,local_path(root,producer['model']),local_path(root,producer['binding']),local_path(root,t['basis']),local_path(root,t['pack']),root/t['sources'],folder)
                else:
                    from .water_pipe_regulations import run
                    payload=run(*(local_path(root,t[key]) for key in ('project','basis','pack')),root/t['sources'],folder)
                if payload is not None:status=payload['status'];reason=payload['scope']
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
            elif t['kind']=='rectangular_fan_operating_point':
                parent=t.get('depends_on')
                if parent and tasks[parent]['status']!='pass':reason='upstream rectangular native study did not pass; fan intersection not executed'
                else:
                    if parent:
                        from .rectangular_fan_binding import run
                        producer=next(x for x in p['tasks'] if x['id']==parent)
                        base=out/parent/('selected-coordination' if producer['kind']=='rectangular_model_design' else '')
                        model=out/parent/'selected-model.json' if producer['kind']=='rectangular_model_design' else local_path(root,producer['model'])
                        payload=run(base/'network-input.json',model,local_path(root,producer['binding']),base/'bim/model.ifc',base/'analysis/network.json',local_path(root,t['curve']),folder)
                    else:
                        from .rectangular_fan import run
                        payload=run(local_path(root,t['project']),local_path(root,t['curve']),folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='Bounded total-pressure fan/system intersection with saved rectangular rerun; native path verified when inherited; fan equipment, motor/product and full acceptance pending'
                    if parent and any(not Path(f).is_file() or digest(Path(f))!=sha for f,sha in rectangular_pins[parent].items()):raise ProjectError('rectangular producer artifacts changed during fan intersection')
                    rectangular_pins[t['id']]={str(f):digest(f) for f in folder.rglob('*') if f.is_file()}
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
            elif t['kind']=='product_alignment':
                parents=[t['junction_from'],t['connector_from']]
                if any(tasks[x]['status']!='pass' for x in parents):
                    reason='source placements did not pass; alignment not executed'
                else:
                    from .product_alignment import run
                    payload=run(out/parents[0],out/parents[1],local_path(root,t['basis']),folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='saved product alignment and mesh overlap checked; native comparison and installation acceptance separate'
            elif t['kind']=='alignment_native':
                parent=t['depends_on'];report=out/parent/'alignment.json'
                if tasks[parent]['status'] not in ('pass','fail') or not report.is_file():
                    reason='no executed alignment diagnostic available'
                elif read_json(report).get('model_alignment_pass') is not True:
                    reason='source model alignment did not pass; native comparison not executed'
                elif not autocad:
                    reason='AutoCAD executable not supplied for alignment diagnostic'
                else:
                    from .alignment_native import run
                    producer=next(x for x in p['tasks'] if x['id']==parent)
                    payload=run(out/parent,out/producer['junction_from'],out/producer['connector_from'],folder,autocad)
                    status='pass' if payload['native_clear'] and payload['mesh_calculated_checks_pass'] else 'fail'
                    reason='source-bound native/mesh comparison; disagreements retained and engineering acceptance pending'
            elif t['kind']=='cad_ifc':
                if not autocad:reason='AutoCAD executable not supplied; CAD IFC conversion not executed'
                else:
                    from .cad_ifc import run
                    payload=run(local_path(root,t['drawing']),local_path(root,t['basis']),folder,autocad)
                    status='pass' if payload['geometry_conversion_pass'] else 'fail'
                    reason='source-bound tessellated IFC conversion; ports, product and engineering acceptance separate'
            elif t['kind']=='connector_ports':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream CAD IFC conversion did not pass; connector ports not executed'
                else:
                    from .connector_ports import run
                    payload=run(out/parent,local_path(root,t['basis']),folder)
                    status='pass' if payload['connector_ports_pass'] else 'fail'
                    reason='source CAD model-node placement verified; installed gap, physical joints and engineering acceptance pending'
            elif t['kind']=='product_ports':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream CAD IFC conversion did not pass; product ports not executed'
                else:
                    from .product_ports import run
                    payload=run(out/parent,local_path(root,t['basis']),folder)
                    status='pass' if payload['product_ports_pass'] else 'fail'
                    reason='source-anchored placed model ports and saved-IFC probe checks; physical joints, external network and engineering acceptance pending'
            elif t['kind']=='tee_selection':
                from .tee_selection import run
                payload=run(local_path(root,t['catalogue']),folder)
                status='pass' if payload['calculated_checks_pass'] else 'fail';reason=payload['scope']
            elif t['kind']=='tee_assembly':
                from .tee_assembly import run
                payload=run(local_path(root,t['tee_spec']),local_path(root,t['assembly_spec']),folder)
                status='pass' if payload['assembly_checks_pass'] else 'fail';reason=payload['scope']
            elif t['kind']=='tee_drawing':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream tee assembly did not pass; drawing not executed'
                else:
                    from .tee_drawing import run
                    producer=next(x for x in p['tasks'] if x['id']==parent)
                    if producer['kind']=='tee_selection':
                        from .tee_selection import selected_paths
                        selected=selected_paths(out/parent,local_path(root,producer['catalogue']))
                        payload=run(*selected,folder)
                    else:
                        payload=run(out/parent/'assembly.ifc',local_path(root,producer['tee_spec']),local_path(root,producer['assembly_spec']),folder)
                    status='pass' if payload['saved_geometry_identity_pass'] else 'fail';reason=payload['scope']
            elif t['kind'] in ('tee_losses','tee_pressure','tee_split'):
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream tee assembly did not pass; diagnostic not executed'
                else:
                    if t['kind']=='tee_split':
                        from .tee_split import run
                    elif t['kind']=='tee_pressure':
                        from .tee_pressure import run
                    else:
                        from .tee_losses import run
                    producer=next(x for x in p['tasks'] if x['id']==parent)
                    arguments=[out/parent/'assembly.ifc',local_path(root,producer['tee_spec']),local_path(root,producer['assembly_spec']),local_path(root,t['basis'])]
                    if t['kind']=='tee_split':arguments.append(local_path(root,t['control']))
                    payload=run(*arguments,folder)
                    status='pass' if payload.get('calculated_checks_pass',payload.get('diagnostic_executed',False)) else 'fail'
                    reason=payload.get('scope','saved-assembly signed coefficient diagnostic only; full network balance and correlation applicability pending')
            elif t['kind']=='ifc_network':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; hydraulic analysis not executed'
                else:
                    from .ifc_network import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(*(local_path(root,t[k]) for k in ('project','model','binding')),source,folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail';reason=payload['scope']
            elif t['kind']=='ifc_metadata':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; metadata edit not executed'
                elif not ifcmcp_python:reason='isolated IFC MCP Python runtime not supplied'
                else:
                    from .ifc_metadata import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(source,local_path(root,t['patch']),folder,ifcmcp_python)
                    status='pass' if payload['calculated_checks_pass'] else 'fail';reason=payload['scope']
            elif t['kind']=='ifc_query':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; query not executed'
                elif not ifcmcp_python:reason='isolated IFC MCP Python runtime not supplied'
                else:
                    from .ifc_query import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(source,local_path(root,t['requirements']),folder,ifcmcp_python)
                    status='pass' if payload['calculated_checks_pass'] else 'fail';reason=payload['scope']
            elif t['kind']=='ifc_preview':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; preview not executed'
                else:
                    from .ifc_preview import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(source,t['guid'],folder)
                    status='pass';reason='saved selected-element preview generated; visual review and engineering acceptance pending'
            elif t['kind']=='ids_check':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; IDS check not executed'
                else:
                    from .ids_check import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(local_path(root,t['ids']),source,folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason=payload['scope']
            elif t['kind']=='ifc_clash':
                dependency=t.get('depends_on')
                if dependency and tasks[dependency]['status']!='pass':reason='upstream IFC producer did not pass; no clash result fabricated'
                else:
                    from .clash import run
                    source=out/dependency/IFC_ARTIFACTS[tasks[dependency]['kind']] if dependency else local_path(root,t['ifc'])
                    payload=run(source,local_path(root,t['policy']),folder)
                    if dependency in rectangular_pins and any(not Path(f).is_file() or digest(Path(f))!=sha for f,sha in rectangular_pins[dependency].items()):raise ProjectError('rectangular producer artifacts changed during clash check')
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='saved IFC triangle clearance plus Manifold3D solid-overlap coverage with sourced contact exceptions; product fidelity and complete acceptance pending'
                    if dependency in rectangular_pins:rectangular_pins[t['id']]={str(f):digest(f) for f in folder.rglob('*') if f.is_file()}
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
            elif t['kind']=='regulated_water_model':
                from .regulated_water_model import run
                files=[local_path(root,t[key]) for key in ('project','model','binding','catalogue','geometry','basis','classifications','pack')]
                payload=run(*files,root/t['sources'],folder)
                status='pass' if payload['calculated_checks_pass'] else 'fail';reason=payload['scope']
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
            elif t['kind']=='circulation_pump_design':
                from .circulation_pump_design import run
                parent=t.get('depends_on')
                recovery=None
                may_iterate=parent and tasks[parent]['status']=='fail' and t.get('allow_failed_baseline') is True
                if parent and tasks[parent]['status']!='pass' and not may_iterate:reason='upstream water model unavailable; screening not executed'
                else:
                    if may_iterate:
                        from .iteration_baseline import verify_failed_baseline
                        baseline=next(x for x in p['tasks'] if x['id']==parent)
                        recovery=verify_failed_baseline(out/parent,local_path(root,baseline['project']),local_path(root,baseline['binding']))
                    source=screening_project(t,p['tasks'],root,out)
                    payload=run(source,*(local_path(root,t[key]) for key in ('catalogue','thermal_basis','rule_basis','pack')),root/t['sources'],folder)
                    screening_project(t,p['tasks'],root,out)
                    if recovery is not None:
                        if verify_failed_baseline(out/parent,local_path(root,baseline['project']),local_path(root,baseline['binding']))!=recovery:raise ProjectError('iteration baseline changed')
                        payload['baseline_recovery']=recovery
                        (folder/'pump-screening.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
                    status='pass' if payload['feasible_candidate_found'] and payload['selected_rerun_pass'] else 'fail'
                    reason='bounded sourced pump screening with hydraulic/thermal/pipe-rule checks and selected rerun; product/full acceptance pending'
            elif t['kind']=='selected_pump_ifc':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream pump screening has no passing selection; IFC revision not executed'
                else:
                    from .selected_pump_ifc import run
                    screen=next(x for x in p['tasks'] if x['id']==parent)
                    bound=next(x for x in p['tasks'] if x['id']==screen['depends_on'])
                    payload=run(out/bound['id'],out/parent,local_path(root,bound['project']),local_path(root,bound['binding']),local_path(root,screen['catalogue']),folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='selected curve on new IFC with stable pump/port identity and fresh hydraulic rebind; product geometry and full acceptance pending'
            elif t['kind']=='ifc_circulation_checks':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream saved water coordination did not pass; combined checks not executed'
                else:
                    from .ifc_circulation_checks import run
                    producer=next(x for x in p['tasks'] if x['id']==parent)
                    if producer['kind']=='selected_pump_ifc':
                        screen=next(x for x in p['tasks'] if x['id']==producer['depends_on'])
                        bound=next(x for x in p['tasks'] if x['id']==screen['depends_on'])
                        directory=out/parent/'rebound';template=out/parent/'selected-template.json';binding=local_path(root,bound['binding'])
                    else:
                        directory=out/parent;template=local_path(root,producer['project']);binding=local_path(root,producer['binding'])
                    payload=run(directory,template,binding,local_path(root,t['thermal_basis']),local_path(root,t['rule_basis']),local_path(root,t['pack']),root/t['sources'],folder)
                    status=payload['status'];reason='saved IFC-derived circulation thermal and scoped pipe rules; full acceptance pending'
            elif t['kind']=='plumbing_pump_set':
                from .plumbing_pump_set import run
                payload=run(*(local_path(root,t[key]) for key in ('project','basis','pack')),root/t['sources'],folder)
                status=payload['status'];reason=payload['scope']
            elif t['kind']=='plumbing_pump_regulations':
                parent=t.get('depends_on')
                if parent and tasks[parent]['status']!='pass':reason='upstream saved network did not pass; plumbing capacity not executed'
                else:
                    if parent:
                        from .ifc_plumbing_pump import run
                        producer=next(x for x in p['tasks'] if x['id']==parent)
                        saved_ifc=None
                        if producer['kind']=='ifc_network':
                            inherited=producer.get('depends_on')
                            saved_ifc=out/inherited/IFC_ARTIFACTS[tasks[inherited]['kind']] if inherited else local_path(root,producer['ifc'])
                        payload=run(out/parent,*(local_path(root,producer[key]) for key in ('project','model','binding')),*(local_path(root,t[key]) for key in ('curve','basis','pack')),root/t['sources'],folder,saved_ifc=saved_ifc)
                    else:
                        from .plumbing_pump_binding import run
                        payload=run(*(local_path(root,t[key]) for key in ('project','curve','basis','pack')),root/t['sources'],folder)
                    status=payload['status'];reason='fresh single-line pump capacity with sourced tank association and WSD checks; duplication, controls and full acceptance pending'
            elif t['kind']=='epanet_pipe_regulations':
                from .epanet_pipe_regulations import run
                payload=run(local_path(root,t['project']),local_path(root,t['basis']),local_path(root,t['pack']),(root/t['sources']).resolve(),folder)
                status=payload['status']
                reason='fresh EPANET speed and distributed friction bound to scoped rules; fluid applicability and full conformity pending'
            elif t['kind']=='circulation_duty':
                from .circulation_duty import run
                payload=run(local_path(root,t['project']),local_path(root,t['basis']),folder)
                status='pass' if payload['calculated_checks_pass'] else 'fail'
                reason='fresh circulation flow and sourced thermal transport targets; heat transfer, load coverage and full acceptance pending'
            elif t['kind']=='water_network':
                from .epanet import run
                parent=t.get('depends_on')
                if parent and tasks[parent]['status']!='pass':reason='upstream pump screening has no passing selection; native water run not executed'
                else:
                    if parent:
                        from .circulation_pump_design import selected_input
                        producer=next(x for x in p['tasks'] if x['id']==parent)
                        source=selected_input(out/parent,screening_project(producer,p['tasks'],root,out),local_path(root,producer['catalogue']))
                    else:source=local_path(root,t['project'])
                    payload=run(source,folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason='steady EPANET water graph, static head, sourced numerical/target checks; route binding, power and full acceptance pending'
            elif t['kind']=='rectangular_fan_regulations':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream rectangular native study did not pass; fan rule not executed'
                else:
                    from .rectangular_fan_regulations import run
                    producer=next(x for x in p['tasks'] if x['id']==parent)
                    base=out/parent/('selected-coordination' if producer['kind']=='rectangular_model_design' else '')
                    model=out/parent/'selected-model.json' if producer['kind']=='rectangular_model_design' else local_path(root,producer['model'])
                    payload=run(base/'network-input.json',model,local_path(root,producer['binding']),base/'bim/model.ifc',base/'analysis/network.json',local_path(root,t['basis']),local_path(root,t['pack']),root/t['sources'],folder)
                    status=payload['status'];reason=payload['scope']
                    rectangular_pins[t['id']]={str(f):digest(f) for f in folder.rglob('*') if f.is_file()}
            elif t['kind']=='rectangular_drawing':
                parent=t['depends_on']
                if tasks[parent]['status']!='pass':reason='upstream rectangular model did not pass; drawing not executed'
                elif not autocad:reason='AutoCAD executable not supplied; rectangular drawing not executed'
                else:
                    from .rectangular_drawing import run as draw
                    from .ifc_native import run as native
                    producer=next(x for x in p['tasks'] if x['id']==parent)
                    source=out/parent/IFC_ARTIFACTS[producer['kind']]
                    model=out/parent/'selected-model.json' if producer['kind']=='rectangular_model_design' else local_path(root,producer['model'])
                    payload=draw(source,model,local_path(root,t['settings']),folder)
                    native(folder/'segments.dxf',local_path(root,t['sheet']),folder/'native',autocad)
                    from .rectangular_drawing_audit import audit
                    export_audit=audit(folder/'native/native-reopen/source-export.dxf',payload['elements'],payload['axes'],payload['annotation_height_m'])
                    (folder/'native-source-audit.json').write_text(json.dumps(export_audit,indent=2),encoding='utf-8')
                    if any(not Path(f).is_file() or digest(Path(f))!=sha for f,sha in rectangular_pins[parent].items()):raise ProjectError('rectangular model changed during native drawing')
                    status='pass';reason=payload['scope']+'; native DWG/scale verified, actual visual and full engineering review separate'
            elif t['kind']=='rectangular_model_design':
                from .rectangular_model_design import run
                payload=run(*(local_path(root,t[key]) for key in ('project','model','binding','catalogue','geometry')),folder)
                status='pass' if payload['calculated_checks_pass'] and payload['stable_object_port_ids_match'] and payload['fixed_endpoints_pass'] else 'fail'
                reason=payload['scope']
                rectangular_pins[t['id']]={str(f):digest(f) for f in folder.rglob('*') if f.is_file()}
            elif t['kind']=='rectangular_network_binding':
                from .rectangular_binding import run
                payload=run(*(local_path(root,t[key]) for key in ('project','model','binding')),folder)
                status='pass' if payload['saved_ifc_geometry_match'] and payload['calculated_checks_pass'] else 'fail'
                reason=payload['scope']
                rectangular_pins[t['id']]={str(f):digest(f) for f in folder.rglob('*') if f.is_file()}
            elif t['kind']=='rectangular_network_design':
                from .rectangular_design import run
                payload=run(local_path(root,t['project']),local_path(root,t['catalogue']),folder)
                status='pass' if payload['feasible_design_found'] and payload['selected_rerun_pass'] else 'fail'
                reason=payload['scope']
                rectangular_pins[t['id']]={str(f):digest(f) for f in folder.rglob('*') if f.is_file()}
            elif t['kind']=='rectangular_network':
                parent=t.get('depends_on')
                if parent and tasks[parent]['status']!='pass':reason='upstream rectangular selection did not pass; analysis not executed'
                else:
                    from .rectangular_network import run
                    if parent:
                        if any(not Path(f).is_file() or digest(Path(f))!=sha for f,sha in rectangular_pins[parent].items()):raise ProjectError('rectangular producer artifacts changed before analysis')
                        from .rectangular_design import selected_input
                        producer=next(x for x in p['tasks'] if x['id']==parent)
                        source=selected_input(out/parent,local_path(root,producer['project']),local_path(root,producer['catalogue']))
                    else:source=local_path(root,t['project'])
                    payload=run(source,folder)
                    status='pass' if payload['calculated_checks_pass'] else 'fail'
                    reason=payload['scope']+'; geometry, product and Hong Kong acceptance pending'
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
    source_rows={x["id"]:x for x in plan_documents(root,p)['passages']}
    matrix=[]
    for r in p["requirements"]:
        task=tasks[r["task"]]
        matrix.append(dict(**r,execution_status=task["status"],acceptance_status="pending review",
                           source_locator={k:v for k,v in source_rows[r["passage"]].items() if k not in ("id","text")},
                           execution_scope=task["scope"],evidence=evidence[r["task"]]))
    result=dict(inputs=before,inputs_unchanged=unchanged,tasks=tasks,requirements=matrix,
        unresolved_inputs=p.get('unresolved_inputs',[]),three_phase_source_bindings=three_phase_rule_bindings(p['tasks']),
        three_phase_model_bindings=three_phase_model_bindings(root,p['tasks']) if unchanged else [],
        regulatory_source_bindings=regulatory_source_bindings(p['tasks'],root) if unchanged else [],
        inventory_source_bindings=inventory_source_bindings(p['tasks'],root) if unchanged else [],
        artifact_hashes={f.relative_to(out).as_posix():digest(f) for f in out.rglob("*") if f.is_file()},
        execution_pass=unchanged and all(x["status"]=="pass" for x in tasks.values()),
        design_accepted=False,acceptance_note="Host agent must compare each artifact to the complete acceptance text; execution is not engineering acceptance")
    from .workflow_report import render
    (out/"index.html").write_text(render(result),encoding="utf-8")
    result['artifact_hashes']['index.html']=digest(out/'index.html')
    (out/"workflow.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
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
    i.add_argument('--supplement',type=Path,action='append',help='Additional brief/rubric under the main brief directory; repeatable')
    v=sub.add_parser("validate");v.add_argument("plan",type=Path)
    e=sub.add_parser("execute");e.add_argument("plan",type=Path);e.add_argument("--out",required=True,type=Path)
    e.add_argument("--energyplus",type=Path);e.add_argument("--autocad",type=Path)
    e.add_argument('--radiance-bin',type=Path)
    e.add_argument('--ifcmcp-python',type=Path)
    e.add_argument('--three-phase-python',type=Path)
    e.add_argument('--graphviz',type=Path)
    v=sub.add_parser("verify");v.add_argument("run_directory",type=Path)
    a=p.parse_args()
    try:
        if a.command=="intake":
            r=intake(a.brief,a.out,a.ocr,a.supplement)
            print(f"Indexed {len(r['passages'])} source passages; coverage: {r['coverage_status']}; interpretation pending")
            if r["coverage_status"]=="blocked":return 2
        elif a.command=="validate":validate_plan(a.plan);print("Source-linked plan valid; interpretation accuracy still requires review")
        elif a.command=="verify":
            r=verify(a.run_directory);print(json.dumps(r,indent=2))
            if not r["integrity_pass"]:return 2
        else:
            r=execute(a.plan,a.out,a.energyplus,a.autocad,a.radiance_bin,a.ifcmcp_python,a.three_phase_python,a.graphviz)
            print(json.dumps({"tasks":r["tasks"],"design_accepted":False},indent=2))
            if not r["execution_pass"]:return 2
    except (ProjectError,OSError,ValueError) as exc:p.exit(2,str(exc)+"\n")
    return 0

if __name__=="__main__":raise SystemExit(main())
