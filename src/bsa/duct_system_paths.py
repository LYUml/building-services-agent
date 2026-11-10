"""Source-bound whole-tree nominal centreline friction studies,not full pressure."""
import argparse
import html
import importlib.metadata
import json
import math
from pathlib import Path

from .cli import digest
from .duct_equivalent import calculate as friction
from .duct_junction_review import from_workflow

ROOT = Path(__file__).resolve().parents[2]


def calculate(junction, schedule):
    if junction.get('source_correspondence_pass') is not True or schedule.get('status')!='pass':
        raise ValueError('Passing source correspondence and selected schedule required')
    flow = schedule['flow_aggregation']
    if flow.get('topology_pass') is not True or flow.get('flow_conserved') is not True:
        raise ValueError('Verified source supply tree required')
    nodes = {n['node']:n for n in junction['nodes']}; rows = {r['id']:r for r in schedule['sections']}
    edges = flow['sections']; root = flow['root']
    if len(nodes)!=len(junction['nodes']) or len(rows)!=len(schedule['sections']) or len(edges)!=len(rows) or {e['id'] for e in edges}!=set(rows) or root not in nodes:
        raise ValueError('Exact unique source nodes,edges and selected sections required')
    graph={n:[] for n in nodes}; parents={}; sections={}
    for edge in edges:
        sid,a,b = [edge[k] for k in ('id','from','to')]
        if a not in nodes or b not in nodes or b==root or a==b or b in parents:
            raise ValueError('One-parent directed source tree required')
        first=[i for i in nodes[a]['incidents'] if i['section']==sid and i['role']=='outgoing']
        last=[i for i in nodes[b]['incidents'] if i['section']==sid and i['role']=='incoming']
        if len(first)!=1 or len(last)!=1: raise ValueError('Source node incidents disagree with directed section')
        row=rows[sid];calc=friction(**row['inputs'],**schedule['air'])
        if row.get('failures') or not math.isclose(calc['friction_Pa_m'],row['calculation']['friction_Pa_m'],rel_tol=1e-12,abs_tol=1e-12):
            raise ValueError('Selected source friction differs from fresh method replay')
        length=math.dist(nodes[a]['point_m'],nodes[b]['point_m'])
        if not math.isfinite(length) or length<=0: raise ValueError('Finite source centreline length required')
        for incident in (first[0],last[0]):
            expected=(length,row['inputs']['width_m'],row['inputs']['height_m'],row['inputs']['flow_m3_s']*1000)
            actual=tuple(incident[k] for k in ('source_centreline_length_m','width_m','height_m','flow_L_s'))
            if any(not math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-10) for x,y in zip(actual,expected)):
                raise ValueError('Saved source incident length,size or flow differs')
        if not math.isclose(row['inputs']['flow_m3_s']*1000,flow['section_flow_L_s'][sid],rel_tol=1e-12):
            raise ValueError('Source schedule/tree section flow differs')
        sections[sid]=dict(id=sid,from_node=a,to_node=b,source_line_handle=first[0]['line_handle'],
            source_centreline_length_m=length,flow_m3_s=row['inputs']['flow_m3_s'],width_m=row['inputs']['width_m'],height_m=row['inputs']['height_m'],
            calculation=calc,nominal_centreline_friction_Pa=calc['friction_Pa_m']*length,
            physical_straight_length_m=None,physical_straight_friction_Pa=None)
        if not math.isfinite(sections[sid]['nominal_centreline_friction_Pa']): raise ValueError('Nominal friction overflowed')
        graph[a].append((sid,b));parents[b]=a
    if set(parents)!=set(nodes)-{root}:raise ValueError('Complete connected source tree required')
    for node in nodes:
        incoming=math.fsum(sections[e['id']]['flow_m3_s'] for e in edges if e['to']==node)
        outgoing=math.fsum(sections[sid]['flow_m3_s'] for sid,_ in graph[node])
        if node!=root and graph[node] and not math.isclose(incoming,outgoing,rel_tol=1e-12):raise ValueError('Source node flow is not conserved')
    paths=[];stack=[(root,[],[])];seen=set();used=set()
    while stack:
        node,ids,visited=stack.pop()
        if node in seen:raise ValueError('Repeated or cyclic source tree node')
        seen.add(node);visited=visited+[node]
        if not graph[node]:
            if node not in flow['leaf_flow_L_s'] or not ids:raise ValueError('Exact source terminal coverage required')
            q=sections[ids[-1]]['flow_m3_s']
            if not math.isclose(q*1000,flow['leaf_flow_L_s'][node],rel_tol=1e-12):raise ValueError('Source leaf flow differs')
            paths.append(dict(outlet_node=node,flow_m3_s=q,section_ids=ids,node_ids=visited,
                source_centreline_length_m=math.fsum(sections[s]['source_centreline_length_m'] for s in ids),
                nominal_centreline_friction_Pa=math.fsum(sections[s]['nominal_centreline_friction_Pa'] for s in ids),
                unresolved_connection_nodes=[dict(node=n,requirement=nodes[n]['connection_requirement']) for n in visited[1:-1] if nodes[n]['connection_requirement']!='straight_continuation'],
                complete_total_pressure_drop_Pa=None,design_accepted=False))
        for sid,child in sorted(graph[node],reverse=True):used.add(sid);stack.append((child,ids+[sid],visited))
    if seen!=set(nodes) or used!=set(sections) or {p['outlet_node'] for p in paths}!=set(flow['leaf_flow_L_s']):raise ValueError('Whole source-tree path coverage differs')
    inlet=math.fsum(sections[s]['flow_m3_s'] for s,_ in graph[root]);outlet=math.fsum(p['flow_m3_s'] for p in paths)
    if not math.isclose(inlet,outlet,rel_tol=1e-12) or not math.isclose(inlet*1000,flow['total_flow_L_s'],rel_tol=1e-12):raise ValueError('Whole source boundary flow is not conserved')
    return dict(status='pending',root_node=root,section_count=len(sections),node_count=len(nodes),outlet_path_count=len(paths),
        inlet_flow_m3_s=inlet,outlet_flow_m3_s=outlet,flow_conservation_pass=True,whole_source_path_coverage_pass=True,
        sections=list(sections.values()),paths=paths,fan_critical_path=None,pressure_budget_complete=False,design_accepted=False,
        scope='Source CAD centreline and selected nominal-section friction estimate only. Both-end fitting trims are not known;centreline friction is not physical straight friction or a conservative pressure bound. Fitting/equipment/boundary/balancing/installation/regulatory and complete assignment acceptance remain pending. Parallel paths must not be added.')


def render(result):
    esc=lambda v:html.escape(str(v))
    rows=[]
    for p in sorted(result['paths'],key=lambda p:p['outlet_node']):
        values=[p['outlet_node'],f"{p['flow_m3_s']*1000:.3f}",len(p['section_ids']),f"{p['source_centreline_length_m']:.4f}",
            f"{p['nominal_centreline_friction_Pa']:.4f}",len(p['unresolved_connection_nodes']),'Pending']
        rows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Whole Supply Tree Review</title><style>body{font:16px/1.5 Arial;color:#20343c;max-width:1250px;margin:35px auto;padding:0 20px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #cbd4d8;padding:8px;text-align:left}th{background:#eaf0f2}.pending{background:#fff0d2;padding:16px;border-left:5px solid #b47016}</style><h1>Whole Supply Tree Review</h1><p class="pending"><strong>Full pressure and fan duty remain pending.</strong> These are nominal untrimmed source-centreline friction estimates,not physical straight losses or complete pressure bounds. Do not add parallel outlet paths or combine these values with trimmed fitting/straight studies.</p><p>'+str(result['section_count'])+' source sections,'+str(result['node_count'])+' nodes and '+str(result['outlet_path_count'])+' outlet paths checked. Inlet and outlet flow: '+f"{result['inlet_flow_m3_s']*1000:.3f}"+' L/s. Every original source section is covered. Paths end at the original tree leaves; downstream equipment,flexible ducts and terminal losses are not inferred.</p><table><tr><th>Outlet</th><th>Flow L/s</th><th>Sections</th><th>Source centreline m</th><th>Nominal centreline friction Pa</th><th>Unresolved internal connections</th><th>Complete pressure</th></tr>'+''.join(rows)+'</table><h2>Original assignment</h2><p>'+str(len(result['original_requirements']))+' original requirements and their recorded execution/acceptance states retained. This diagnostic does not accept them or determine the fan critical path.</p><p><a href="system-paths.json">All source identities,section/path arithmetic and pending requirements</a> · <a href="junction-review.json">Source-native connection review</a></p></html>'


def run(plan,workflow,native_task,out):
    from .delivery import context
    import fluids.friction as engine
    plan,workflow,out=[Path(p).resolve() for p in (plan,workflow,out)]
    if out.exists() or not out.is_relative_to(ROOT) or out.is_relative_to(workflow) or workflow.is_relative_to(out) or plan.is_relative_to(out):raise ValueError('New repository output outside source workflow required')
    if importlib.metadata.version('fluids')!='1.3.1':raise ValueError('Pinned fluids1.3.1 required')
    source_report=workflow/'workflow.json';report_sha=digest(source_report)
    _,record,integrity=context(plan,workflow)
    if not integrity['integrity_pass']:raise ValueError('Source workflow integrity failed')
    junction=from_workflow(plan,workflow,native_task,out/'junction-review.json')
    schedule_path=workflow/junction['lineage'][-1]/'results.json'
    schedule=json.loads(schedule_path.read_text(encoding='utf-8'));pins={str(source_report):report_sha}
    artifacts={}
    for name,sha in record['artifact_hashes'].items():
        p=(workflow/name).resolve()
        if not p.is_relative_to(workflow):raise ValueError('Source artifact escaped recorded workflow')
        artifacts[str(p)]=sha
    for addition in (record['inputs'],record.get('runtime_inputs',{}),junction['inputs'],artifacts):
        for name,sha in addition.items():
            if name in pins and pins[name]!=sha:raise ValueError('Source context changed between system checks')
            pins[name]=sha
    for p in (Path(__file__),Path(friction.__code__.co_filename),Path(engine.__file__)):
        pins[str(p.resolve())]=digest(p)
    result=calculate(junction,schedule)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Source or method changed during system path study')
    result.update(inputs=pins,air=schedule['air'],source_basis=junction['source_basis'],drawing_binding_basis=junction['binding_basis'],
        input_interpretation='Inherited preliminary design air conditions,flows and selected nominal sizes;CAD-derived planar source lengths,not measured installed straight lengths. Original assumptions/targets retain their source records.',
        source_context=dict(plan=str(plan),workflow=str(workflow),native_task=native_task),original_requirements=record['requirements'])
    (out/'system-paths.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (out/'index.html').write_text(render(result),encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('workflow');p.add_argument('native_task');p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.plan,a.workflow,a.native_task,a.out);print(r['section_count'],'source sections;',r['outlet_path_count'],'outlet paths;',r['status']);raise SystemExit(2)
