"""Recenter rectangular four-outlet VAV groups without moving terminals or adding bends."""
import argparse
import copy
import importlib.metadata
import json
import math
import tempfile
from pathlib import Path

import ezdxf
from shapely.geometry import MultiPoint, LineString, Polygon
from . import air_terminal_drawing, autocad_schedule, duct_plan_clearance, duct_sheet, view_tags, duct_junction_review, duct_system_paths
from .autocad_source import local
from .cad_intake import METRES_PER_UNIT
from .cli import digest
from .workflow import verify as verify_workflow

SCOPE = 'Declared planar VAV/tap relocation with unchanged terminals, topology and flows; inherited finite-size friction compensation, not installed flex length, full pressure, hardware, ADPI or full engineering acceptance'


def compensate(project, schedule, old_binding, new_binding):
    """A derived design cap, preserving every original limit and candidate option."""
    result=copy.deepcopy(project);rows={r['id']:r for r in schedule['sections']};caps=[]
    for section in result['sections']:
        name=section['id'];old=old_binding['sections'][name];new=new_binding['sections'][name]
        before=math.dist(old['from_m'],old['to_m']);after=math.dist(new['from_m'],new['to_m'])
        if after>before+1e-8:
            if not section.get('candidates'):raise ValueError('Inherited finite size candidates required for length compensation')
            original_cap=section['limits']['friction_Pa_m']
            derived_cap=rows[name]['calculation']['friction_Pa_m']*before/after
            section['limits']['friction_Pa_m']=min(original_cap,derived_cap)
            caps.append(dict(section=name,original_limit_Pa_m=original_cap,derived_limit_Pa_m=section['limits']['friction_Pa_m'],
                             baseline_length_m=before,revised_length_m=after,
                             basis='Design choice: revised untrimmed centreline straight friction must not exceed this section baseline; no new code threshold'))
    result['basis']+='; source-preserving VAV recenter design choice: on lengthened sections, further restrict friction gradient to original section gradient times old/new centreline length; retain original candidate dimensions and all source caps'
    return result,caps


def revised(doc, allocation, tree, binding, layers, schedule, obstacles):
    """A bounded rectangular-group design choice, not general spatial optimization."""
    before = air_terminal_drawing.inspect(doc, allocation, tree, binding, layers)
    scale = METRES_PER_UNIT[doc.units]
    old_snapshot = duct_sheet.snapshot(doc)
    result_binding = copy.deepcopy(binding)
    centers = {t['id']: t['center_m'] for t in allocation['terminals']}
    nodes = {}
    incident = {}
    for name, entry in binding['sections'].items():
        for node, xyz in [(entry['from_node'], entry['from_m']), (entry['to_node'], entry['to_m'])]:
            nodes[node] = list(xyz); incident.setdefault(node, []).append(name)
    moved = {}; changes = []; touched = set()
    table_cells = {c['handle'] for entry in binding['sections'].values() for c in entry.get('cells',[])}
    def text_for(value):
        matches = [e for e in doc.modelspace().query('TEXT') if e.dxf.text == value and e.dxf.handle not in table_cells]
        if len(matches) != 1: raise ValueError('Unique source label required: '+value)
        return matches[0]
    for group in before['groups']:
        if group['outlet_count'] != 4: raise ValueError('Exactly four rectangular outlet centres required')
        points = [centers[r['terminal']] for r in group['routes']]
        envelope = MultiPoint(points).envelope
        if envelope.geom_type != 'Polygon': raise ValueError('Nondegenerate rectangle required')
        corners = list(envelope.exterior.coords)[:-1]
        if len(corners) != 4 or any(min(math.dist(p,c) for c in corners) > 1e-8 for p in points) or len(set(tuple(p) for p in points)) != 4:
            raise ValueError('Only four-corner rectangular groups supported')
        center = envelope.centroid
        leaf = group['id']; old = nodes[leaf]; new = [center.x, center.y, old[2]]
        if math.dist(old, new) <= 1e-8: continue
        if len(incident[leaf]) != 1: raise ValueError('Single incoming leaf section required')
        inlet = binding['sections'][incident[leaf][0]]
        tap = inlet['from_node'] if inlet['to_node'] == leaf else inlet['to_node']
        parent = nodes[tap]
        if abs(parent[0]-old[0]) > 1e-8 or abs(parent[1]-old[1]) <= 1e-8:
            raise ValueError('Existing vertical leaf branch required')
        if abs(new[0]-old[0]) > 1e-8:
            trunk = [sid for sid in incident[tap] if sid != incident[leaf][0]]
            if len(trunk) not in (1,2) or any(abs(binding['sections'][sid]['from_m'][1]-binding['sections'][sid]['to_m'][1]) > 1e-8 for sid in trunk):
                raise ValueError('Moving tap requires one or two existing horizontal trunk sections')
        if leaf in moved or tap in moved: raise ValueError('Overlapping group/tap revision unsupported')
        moved[leaf] = new; moved[tap] = [new[0], parent[1], parent[2]]
        changes.append(dict(id=leaf, from_m=old, to_m=new, tap=tap,
                            baseline_max_plan_m=max(r['plan_length_m'] for r in group['routes'])))
        circle = doc.entitydb[group['vav_handle']]; circle.dxf.center = [v/scale for v in new]; touched.add(circle.dxf.handle)
        label = text_for(leaf)
        label.dxf.insert = [label.dxf.insert[i]+(new[i]-old[i])/scale for i in range(3)]; touched.add(label.dxf.handle)
        for route in group['routes']:
            line = doc.entitydb[route['flex_handle']]
            a, b = list(line.dxf.start), list(line.dxf.end)
            if math.dist([v*scale for v in a],old) <= 1e-8: line.dxf.start = [v/scale for v in new]
            elif math.dist([v*scale for v in b],old) <= 1e-8: line.dxf.end = [v/scale for v in new]
            else: raise ValueError('Flex endpoint no longer matches VAV')
            touched.add(line.dxf.handle)
    old_rigid = new_rigid = 0.
    for name, entry in result_binding['sections'].items():
        old_a, old_b = entry['from_m'], entry['to_m']
        new_a = moved.get(entry['from_node'], old_a); new_b = moved.get(entry['to_node'],old_b)
        old_rigid += math.dist(old_a,old_b); new_rigid += math.dist(new_a,new_b)
        old_vector = [b-a for a,b in zip(old_a,old_b)]; new_vector = [b-a for a,b in zip(new_a,new_b)]
        if sum(a*b for a,b in zip(old_vector,new_vector)) <= 0 or any(abs(old_vector[i]*new_vector[j]-old_vector[j]*new_vector[i]) > 1e-8 for i in range(3) for j in range(3)):
            raise ValueError('Section reversal, zero length or added bend rejected')
        if math.dist(old_a,new_a) > 1e-8 or math.dist(old_b,new_b) > 1e-8:
            line = doc.entitydb[entry['line_handle']]
            line.dxf.start = [v/scale for v in new_a]; line.dxf.end = [v/scale for v in new_b]; touched.add(line.dxf.handle)
            label = text_for(name)
            label.dxf.insert = [label.dxf.insert[i]+(new_a[i]+new_b[i]-old_a[i]-old_b[i])/2/scale for i in range(3)]; touched.add(label.dxf.handle)
            entry['from_m'] = list(new_a); entry['to_m'] = list(new_b)
    if new_rigid > old_rigid+1e-8: raise ValueError('Rigid centreline total would increase')
    after = air_terminal_drawing.inspect(doc, allocation, tree, result_binding, layers)
    by_id = {g['id']:g for g in after['groups']}
    for change in changes:
        group = by_id[change['id']]
        change['revised_max_plan_m'] = max(r['plan_length_m'] for r in group['routes'])
        if change['revised_max_plan_m'] >= change['baseline_max_plan_m']-1e-8:
            raise ValueError('Moved group must strictly improve its maximum planar length')
    def total(review): return math.fsum(r['plan_length_m'] for g in review['groups'] for r in g['routes'])
    if not changes or total(after) >= total(before)-1e-8: raise ValueError('No strict total flex-plan improvement')
    spec = dict(drawing_sha256='',schedule_sha256='',binding_sha256='',clearance_m=0,
                basis='Source-bound nominal-width overlap diagnostic only; no physical clearance target', obstacles=obstacles)
    planar = duct_plan_clearance.inspect(doc,schedule,result_binding,spec)
    if not planar['planar_target_met']: raise ValueError('Revised nominal rigid duct overlaps a tested source obstacle')
    flex_pairs = []
    for group in after['groups']:
        for route in group['routes']:
            line = doc.entitydb[route['flex_handle']]
            segment = LineString([(line.dxf.start.x*scale,line.dxf.start.y*scale),(line.dxf.end.x*scale,line.dxf.end.y*scale)])
            for item in obstacles:
                if segment.intersects(Polygon(item['polygon_m'])): raise ValueError('Revised flex centreline intersects a tested source obstacle')
                flex_pairs.append([route['terminal'],item['id'],segment.distance(Polygon(item['polygon_m']))])
    label_adjustments=[]
    # Existing conservative tag rectangles; only moved VAV labels may shift.
    for change in changes:
        label=text_for(change['id']);h=label.dxf.height;start=list(label.dxf.insert)
        others=[view_tags.rectangle(e.dxf.insert,e.dxf.text,e.dxf.height) for e in doc.modelspace().query('TEXT')
                if e.dxf.layer==label.dxf.layer and e.dxf.handle!=label.dxf.handle]
        if label.dxf.get('rotation',0)!=0: raise ValueError('Unrotated VAV label required')
        for offset in (0,-h,h,-2*h,2*h):
            point=[start[0],start[1]+offset,start[2]]
            if not any(view_tags.overlap(view_tags.rectangle(point,label.dxf.text,h),b) for b in others):
                label.dxf.insert=point
                if offset:label_adjustments.append(dict(id=change['id'],handle=label.dxf.handle,shift_drawing_units=[0,offset,0]))
                break
        else:raise ValueError('Moved VAV label has no clear bounded text position')
    current = duct_sheet.snapshot(doc)
    if set(current) != set(old_snapshot) or any(current[h] != value for h,value in old_snapshot.items() if h not in touched):
        raise ValueError('Unrelated source entity changed')
    return result_binding, dict(changes=changes,label_adjustments=label_adjustments,changed_entity_handles=sorted(touched),
        baseline_total_flex_plan_m=total(before), revised_total_flex_plan_m=total(after),
        baseline_max_flex_plan_m=before['maximum_plan_length_m'],revised_max_flex_plan_m=after['maximum_plan_length_m'],
        baseline_total_rigid_centreline_m=old_rigid,revised_total_rigid_centreline_m=new_rigid,
        rigid_obstacle_pairs=len(planar['checks']),flex_obstacle_pairs=len(flex_pairs),
        all_tested_projections_clear=True, terminal_count=after['terminal_count'],
        unchanged_terminals_flows_groups=True, added_bends=0,scope=SCOPE,design_accepted=False)


def resolve(plan, workflow, native_task):
    if not verify_workflow(workflow)['integrity_pass']: raise ValueError('Original workflow source or artifacts changed')
    report = json.loads((workflow/'workflow.json').read_text(encoding='utf-8'))
    if report['inputs'].get(str(plan)) != digest(plan): raise ValueError('Wrong original plan')
    tasks = {t['id']:t for t in json.loads(plan.read_text(encoding='utf-8'))['tasks']}
    lineage=[]; name=native_task
    for kind in ('duct_sheet_native','duct_sheet','duct_schedule','air_allocation'):
        task=tasks.get(name,{})
        if task.get('kind') != kind or report['tasks'].get(name,{}).get('status') != 'pass': raise ValueError('Passing original native ancestry required')
        lineage.append((name,task));name=task.get('depends_on')
    native,sheet,schedule,allocation=lineage
    files=dict(source=local(plan.parent/sheet[1]['drawing']), binding=local(plan.parent/sheet[1]['binding']),
        project=local(plan.parent/schedule[1]['project']), allocation_project=local(plan.parent/allocation[1]['project']),
        native_settings=local(plan.parent/native[1]['settings']),
        allocation=workflow/allocation[0]/'allocation.json',schedule=workflow/schedule[0]/'results.json')
    return files


def run(plan, workflow, native_task, policy, output, autocad):
    plan,workflow,policy,output = local(plan),local(workflow),local(policy),local(output,True)
    files=resolve(plan,workflow,native_task)
    protected=[plan,workflow,policy,*files.values()]
    if output.exists() or any(output==p or output in p.parents or p.is_dir() and p in output.parents for p in protected): raise ValueError('Fresh output separate from original sources/workflow required')
    settings=json.loads(policy.read_text(encoding='utf-8'))
    if set(settings) != {'layers','obstacles','coverage','basis','classification'} or settings['classification']!='design_choice' or not isinstance(settings['basis'],str) or not settings['basis'].strip(): raise ValueError('Explicit source-scoped recenter design choice required')
    coverage=settings['coverage']
    if set(coverage) != {'complete','unresolved'} or coverage['complete'] is not False or not coverage['unresolved']: raise ValueError('Retain incomplete installation/obstacle coverage explicitly')
    controls=[Path(__file__),Path(air_terminal_drawing.__file__),Path(duct_plan_clearance.__file__),Path(view_tags.__file__),Path(duct_junction_review.__file__),Path(duct_system_paths.__file__)]
    pins={str(p):digest(p) for p in [plan,workflow/'workflow.json',policy,*files.values(),*controls]}
    allocation=json.loads(files['allocation'].read_text(encoding='utf-8'));project=json.loads(files['project'].read_text(encoding='utf-8'))
    original_binding=json.loads(files['binding'].read_text(encoding='utf-8'))
    if original_binding['source_sha256'] != digest(files['source']): raise ValueError('Original drawing/binding mismatch')
    doc=ezdxf.readfile(files['source'])
    binding,geometry=revised(doc,allocation,project['tree'],original_binding,settings['layers'],json.loads(files['schedule'].read_text(encoding='utf-8')),settings['obstacles'])
    output.mkdir(parents=True);inputs=output/'inputs';inputs.mkdir()
    drawing=inputs/'Supply Air Distribution.dxf';doc.saveas(drawing)
    binding['source_sha256']=digest(drawing)
    binding['basis']+='; declared VAV/tap recenter revision; original allocation and topology unchanged; installed geometry remains unverified'
    binding_path=inputs/'binding.json';binding_path.write_text(json.dumps(binding,indent=2),encoding='utf-8')
    original_schedule=json.loads(files['schedule'].read_text(encoding='utf-8'))
    revised_project,caps=compensate(project,original_schedule,original_binding,binding)
    project_path=inputs/'ducts.json';project_path.write_text(json.dumps(revised_project,indent=2),encoding='utf-8')
    delivered=autocad_schedule.run(drawing,project_path,binding_path,output/'delivery',allocation_project=files['allocation_project'],native_settings=files['native_settings'],autocad=autocad,original_plan=plan)
    if delivered['status']!='written': raise ValueError('Revised native delivery failed: '+str(delivered.get('error')))
    reopened=output/'delivery/native/reopened/source-export.dxf'
    checked=air_terminal_drawing.run(reopened,output/'delivery/allocation/allocation.json',project_path,binding_path,output/'reopened-connections.json',layers=settings['layers'])
    if checked['terminal_count']!=geometry['terminal_count']: raise ValueError('Native terminal coverage changed')
    new_schedule=json.loads((output/'delivery/schedule/results.json').read_text(encoding='utf-8'))
    spec=dict(drawing_sha256='',schedule_sha256='',binding_sha256='',clearance_m=0,basis='Revised selected nominal-width source-column overlap diagnostic',obstacles=settings['obstacles'])
    if not duct_plan_clearance.inspect(ezdxf.readfile(reopened),new_schedule,binding,spec)['planar_target_met']:raise ValueError('Selected revised duct width overlaps tested source column')
    baseline=duct_system_paths.calculate(duct_junction_review.inspect(ezdxf.readfile(files['source']),original_schedule,original_binding),original_schedule)
    revised_paths=duct_system_paths.calculate(duct_junction_review.inspect(ezdxf.readfile(reopened),new_schedule,binding),new_schedule)
    old_paths={p['outlet_node']:p for p in baseline['paths']};deltas=[]
    for p in revised_paths['paths']:
        old=old_paths[p['outlet_node']]
        if p['section_ids']!=old['section_ids'] or p['flow_m3_s']!=old['flow_m3_s'] or p['nominal_centreline_friction_Pa']>old['nominal_centreline_friction_Pa']+1e-9:raise ValueError('Revised straight-friction path regressed or changed identity/flow')
        deltas.append(dict(outlet=p['outlet_node'],baseline_Pa=old['nominal_centreline_friction_Pa'],revised_Pa=p['nominal_centreline_friction_Pa']))
    old_rows={r['id']:r for r in original_schedule['sections']};sizes=[]
    for row in new_schedule['sections']:
        old=old_rows[row['id']]
        if row['inputs']!=old['inputs']:sizes.append(dict(section=row['id'],baseline=old['inputs'],revised=row['inputs']))
    compensation=dict(derived_design_caps=caps,changed_sizes=sizes,paths=deltas,all_untrimmed_straight_path_friction_nonincreasing=True,
        scope='Existing equivalent-round engine on untrimmed centreline lengths only; flexible duct, fittings, transitions, equipment and fan duty remain unknown')
    if any(digest(Path(p))!=sha for p,sha in pins.items()) or not verify_workflow(workflow)['integrity_pass']: raise ValueError('Original source changed during revision')
    record=dict(schema='bsa.vav-recenter/1',plan=str(plan),workflow=str(workflow),native_task=native_task,policy=str(policy),inputs=pins,
        versions={k:importlib.metadata.version(k) for k in ('ezdxf','shapely','fluids')},geometry=geometry,friction_compensation=compensation,coverage=coverage,
        native_reopen_pass=delivered['native_reopen_pass'],plot_visual_review='pending',design_accepted=False)
    record['artifacts']={p.relative_to(output).as_posix():digest(p) for p in output.rglob('*') if p.is_file()}
    (output/'revision.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    return record


def verify(output):
    output=local(output);r=json.loads((output/'revision.json').read_text(encoding='utf-8'))
    if r.get('schema')!='bsa.vav-recenter/1' or r['design_accepted'] is not False: raise ValueError('Source-bound unaccepted revision required')
    if any(digest(Path(p))!=sha for p,sha in r['inputs'].items()) or r['versions']!={k:importlib.metadata.version(k) for k in ('ezdxf','shapely','fluids')}: raise ValueError('Revision source or runtime changed')
    for name,sha in r['artifacts'].items():
        p=(output/name).resolve()
        if not p.is_relative_to(output) or digest(p)!=sha: raise ValueError('Revision artifact changed')
    files=resolve(local(r['plan']),local(r['workflow']),r['native_task']);policy=json.loads(local(r['policy']).read_text(encoding='utf-8'))
    doc=ezdxf.readfile(files['source'])
    binding,geometry=revised(doc,json.loads(files['allocation'].read_text(encoding='utf-8')),json.loads(files['project'].read_text(encoding='utf-8'))['tree'],json.loads(files['binding'].read_text(encoding='utf-8')),policy['layers'],json.loads(files['schedule'].read_text(encoding='utf-8')),policy['obstacles'])
    saved=ezdxf.readfile(output/'inputs/Supply Air Distribution.dxf')
    if duct_sheet.snapshot(doc)!=duct_sheet.snapshot(saved) or geometry!=r['geometry'] or r['coverage']!=policy['coverage']: raise ValueError('Saved design differs from source reconstruction')
    saved_binding=json.loads((output/'inputs/binding.json').read_text(encoding='utf-8'))
    binding['source_sha256']=digest(output/'inputs/Supply Air Distribution.dxf')
    binding['basis']+='; declared VAV/tap recenter revision; original allocation and topology unchanged; installed geometry remains unverified'
    if binding!=saved_binding: raise ValueError('Saved geometry binding differs from source')
    project,caps=compensate(json.loads(files['project'].read_text(encoding='utf-8')),json.loads(files['schedule'].read_text(encoding='utf-8')),json.loads(files['binding'].read_text(encoding='utf-8')),binding)
    if project!=json.loads((output/'inputs/ducts.json').read_text(encoding='utf-8')) or caps!=r['friction_compensation']['derived_design_caps']:raise ValueError('Compensated sizing project differs from original source/grid')
    delivered=autocad_schedule.verify(output/'delivery')
    if not delivered['native_reopen_pass'] or r['native_reopen_pass'] is not True: raise ValueError('Native correspondence not verified')
    schedules=[json.loads(p.read_text(encoding='utf-8')) for p in (files['schedule'],output/'delivery/schedule/results.json')]
    paths=[]
    for drawing,schedule,b in [(files['source'],schedules[0],json.loads(files['binding'].read_text(encoding='utf-8'))),(output/'delivery/native/reopened/source-export.dxf',schedules[1],binding)]:
        paths.append(duct_system_paths.calculate(duct_junction_review.inspect(ezdxf.readfile(drawing),schedule,b),schedule)['paths'])
    old_paths={p['outlet_node']:p for p in paths[0]};deltas=[]
    for p in paths[1]:
        old=old_paths[p['outlet_node']]
        if p['nominal_centreline_friction_Pa']>old['nominal_centreline_friction_Pa']+1e-9:raise ValueError('Reconstructed straight-friction path regressed')
        deltas.append(dict(outlet=p['outlet_node'],baseline_Pa=old['nominal_centreline_friction_Pa'],revised_Pa=p['nominal_centreline_friction_Pa']))
    old_rows={row['id']:row for row in schedules[0]['sections']}
    sizes=[dict(section=row['id'],baseline=old_rows[row['id']]['inputs'],revised=row['inputs']) for row in schedules[1]['sections'] if row['inputs']!=old_rows[row['id']]['inputs']]
    if deltas!=r['friction_compensation']['paths'] or sizes!=r['friction_compensation']['changed_sizes'] or r['friction_compensation']['all_untrimmed_straight_path_friction_nonincreasing'] is not True:raise ValueError('Saved path or size comparison differs from source replay')
    return dict(integrity_pass=True,moved_vav_groups=len(geometry['changes']),terminal_count=geometry['terminal_count'],native_reopen_pass=True,scope=SCOPE,design_accepted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('run')
    for name in ('plan','workflow','native_task','policy'):q.add_argument(name)
    q.add_argument('--out',required=True);q.add_argument('--autocad',required=True)
    sub.add_parser('verify').add_argument('output');a=p.parse_args()
    result=verify(a.output) if a.command=='verify' else run(a.plan,a.workflow,a.native_task,a.policy,a.out,a.autocad)
    print(json.dumps({k:result[k] for k in ('native_reopen_pass','design_accepted')}))
