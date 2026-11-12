"""Source-bound planar duct connection requirements; never a fitting design."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import ezdxf

from .cad_intake import METRES_PER_UNIT
from .cli import digest
from .workspace import allowed

ROOT = Path(__file__).resolve().parents[2]


def inspect(doc, schedule, binding):
    scale = METRES_PER_UNIT.get(doc.units)
    if scale is None: raise ValueError('Known drawing units required')
    if schedule.get('status') != 'pass': raise ValueError('Passing selected schedule required')
    if not isinstance(binding.get('basis'), str) or not binding['basis'].strip(): raise ValueError('Drawing binding source basis required')
    flow = schedule.get('flow_aggregation', {})
    if flow.get('topology_pass') is not True or flow.get('flow_conserved') is not True:
        raise ValueError('Conserved source tree required')
    if not isinstance(flow.get('basis'), str) or not flow['basis'].strip(): raise ValueError('Tree source basis required')
    rows = {r['id']: r for r in schedule['sections']}
    edges = {e['id']: e for e in flow['sections']}
    if not rows or len(rows) != len(schedule['sections']) or len(edges) != len(flow['sections']) or set(rows) != set(edges) or set(rows) != set(binding['sections']):
        raise ValueError('Exact unique schedule/tree/binding coverage required')
    if set(flow['section_flow_L_s']) != set(rows): raise ValueError('Exact section flow coverage required')
    nodes = {}; incoming = {}; outgoing = {}; used = set()
    def positive(value):
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0: raise ValueError('Positive finite section dimensions and flows required')
        return value
    for sid, row in rows.items():
        if row.get('failures') or not row.get('calculation'): raise ValueError('Computed selected section without failures required')
        edge = edges[sid]; a, b = edge['from'], edge['to']
        if any(not isinstance(n, str) or not n.strip() for n in (a, b)) or a == b or b in incoming: raise ValueError('Tree requires unique parents and nonempty distinct nodes')
        incoming[b] = sid; outgoing.setdefault(a, []).append(sid)
        width, height, q = (positive(row['inputs'][k]) for k in ('width_m', 'height_m', 'flow_m3_s'))
        if not math.isclose(positive(flow['section_flow_L_s'][sid]), q*1000, rel_tol=1e-12): raise ValueError('Schedule/tree flow mismatch')
        entry = binding['sections'][sid]
        if (entry['from_node'], entry['to_node']) not in ((a, b), (b, a)): raise ValueError('Binding/tree endpoint identity mismatch')
        entity = doc.entitydb.get(entry['line_handle'])
        if entity is None or entity.dxftype() != 'LINE' or entity not in doc.modelspace() or entity.dxf.handle in used:
            raise ValueError('Unique saved modelspace section LINE required')
        used.add(entity.dxf.handle); points = {}
        for node, key, actual in ((entry['from_node'], 'from_m', entity.dxf.start), (entry['to_node'], 'to_m', entity.dxf.end)):
            expected = entry[key]
            if not isinstance(expected, list) or len(expected) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) for v in expected): raise ValueError('Finite source metre points required')
            point = [v*scale for v in actual]
            if math.dist(point, expected) > 1e-8 or abs(point[2]) > 1e-8: raise ValueError('Saved planar LINE differs from binding')
            points[node] = point
            if node in nodes and math.dist(nodes[node]['point_m'], point) > 1e-8: raise ValueError('Shared source node is disconnected')
            nodes.setdefault(node, dict(point_m=point, incidents=[]))
        length = math.dist(points[a], points[b])
        if length <= 1e-8: raise ValueError('Nonzero section centreline required')
        for node, other, role in ((a, b, 'outgoing'), (b, a, 'incoming')):
            unit = [(v-u)/length for u, v in zip(points[node], points[other])]
            nodes[node]['incidents'].append(dict(section=sid, line_handle=entity.dxf.handle, role=role,
                outward_unit_vector=unit, source_centreline_length_m=length, width_m=width, height_m=height, flow_L_s=q*1000))
    root = flow['root']
    if root not in nodes or root in incoming or set(incoming) != set(nodes)-{root}: raise ValueError('One connected source root required')
    seen = set(); stack = [root]
    while stack:
        node = stack.pop()
        if node in seen: raise ValueError('Tree cycle detected')
        seen.add(node); stack.extend(edges[s]['to'] for s in outgoing.get(node, []))
    if seen != set(nodes): raise ValueError('Disconnected source tree')
    result = []
    def dot(a, b): return math.fsum(x*y for x, y in zip(a, b))
    for node, item in sorted(nodes.items()):
        incidents = item['incidents']; degree = len(incidents)
        qin = math.fsum(r['flow_L_s'] for r in incidents if r['role'] == 'incoming')
        qout = math.fsum(r['flow_L_s'] for r in incidents if r['role'] == 'outgoing')
        if node in incoming and node in outgoing and not math.isclose(qin, qout, rel_tol=1e-12): raise ValueError('Node flow is not conserved')
        equal = all(math.isclose(r['width_m'], incidents[0]['width_m'], abs_tol=1e-10, rel_tol=0) and math.isclose(r['height_m'], incidents[0]['height_m'], abs_tol=1e-10, rel_tol=0) for r in incidents)
        pairs = [dict(sections=[a['section'], b['section']], outward_angle_deg=math.degrees(math.acos(max(-1., min(1., dot(a['outward_unit_vector'], b['outward_unit_vector'])))))) for i, a in enumerate(incidents) for b in incidents[i+1:]]
        if any(p['outward_angle_deg'] < 1e-6 for p in pairs): raise ValueError('Coincident outward section rays require explicit revised topology')
        if node == root:
            kind = 'source_boundary'
        elif degree == 1:
            kind = 'terminal_boundary'
        elif degree == 2:
            angle = pairs[0]['outward_angle_deg']
            if math.isclose(angle, 180, abs_tol=1e-6): kind = 'straight_continuation' if equal else 'transition_required'
            elif math.isclose(angle, 90, abs_tol=1e-6): kind = 'elbow_required' if equal else 'bend_and_section_change_required'
            else: kind = 'non_orthogonal_bend_required' if equal else 'non_orthogonal_bend_and_section_change_required'
        elif degree == 3 and all(any(math.isclose(p['outward_angle_deg'], expected, abs_tol=1e-6) for p in pairs) for expected in (90, 180)):
            kind = 'equal_section_tee_candidate' if equal else 'unequal_section_tee_required'
        else:
            kind = 'multi_branch_connection_required' if degree > 3 else 'non_orthogonal_junction_required'
        result.append(dict(node=node, point_m=item['point_m'], degree=degree, nominal_sections_equal=equal,
            connection_requirement=kind, incidents=incidents, pair_angles=pairs, incoming_flow_L_s=qin, outgoing_flow_L_s=qout,
            fitting_authored=False, engineering_acceptance='pending'))
    total = positive(flow['total_flow_L_s'])
    if not math.isclose(total, math.fsum(r['flow_L_s'] for r in nodes[root]['incidents']), rel_tol=1e-12): raise ValueError('Root flow differs from tree total')
    leaves = {n for n in nodes if n not in outgoing}
    if set(flow['leaf_flow_L_s']) != leaves or any(not math.isclose(positive(flow['leaf_flow_L_s'][n]), nodes[n]['incidents'][0]['flow_L_s'], rel_tol=1e-12) for n in leaves): raise ValueError('Leaf flow coverage differs')
    return dict(nodes=result, counts=dict(Counter(r['connection_requirement'] for r in result)), section_count=len(rows),
        source_node_count=len(nodes), source_basis=flow['basis'], binding_basis=binding['basis'], source_correspondence_pass=True,
        status='review_required', design_accepted=False,
        missing_design_inputs=['Fitting end stations and source-backed trim lengths', 'Wall/insulation and joint/product construction',
            'Installation elevations and cross-section roll', 'Applicable fitting loss data and pressure/network verification'],
        scope='Source-linked planar centreline/nominal-size connection requirements only; no physical fittings, trim allowances, VAV ports or installed clearances established')


def from_workflow(plan, directory, native_task, output):
    from .workflow import verify, local_path
    plan, directory, output = [Path(p).resolve() for p in (plan, directory, output)]
    if not allowed(output) or output.exists() or output == directory or directory in output.parents or output in directory.parents or output == plan:
        raise ValueError('New review file outside immutable workflow required')
    pins = {str(p): digest(p) for p in (plan, directory/'workflow.json', Path(__file__),ROOT/'src/bsa/workspace.py')}
    if not verify(directory)['integrity_pass']: raise ValueError('Workflow sources/artifacts changed')
    report = json.loads((directory/'workflow.json').read_text(encoding='utf-8'))
    if report['inputs'].get(str(plan)) != pins[str(plan)]: raise ValueError('Plan does not belong to workflow')
    tasks = {t['id']: t for t in json.loads(plan.read_text(encoding='utf-8'))['tasks']}
    lineage = []; name = native_task
    for kind in ('duct_sheet_native', 'duct_sheet', 'duct_schedule'):
        task = tasks.get(name, {})
        if task.get('kind') != kind or report['tasks'].get(name, {}).get('status') != 'pass': raise ValueError('Passing native/sheet/schedule ancestry required')
        lineage.append((name, task)); name = task.get('depends_on')
    native, sheet, schedule = lineage
    drawing = directory/native[0]/'reopened/source-export.dxf'
    sizing = directory/schedule[0]/'results.json'; binding = local_path(plan.parent, sheet[1]['binding'])
    source = local_path(plan.parent, schedule[1]['project'])
    pins.update({str(p): digest(p) for p in (drawing, sizing, binding, source)})
    saved = json.loads(sizing.read_text(encoding='utf-8'))
    if saved['input_sha256'] != pins[str(source)]: raise ValueError('Schedule/project correspondence changed')
    result = inspect(ezdxf.readfile(drawing), saved, json.loads(binding.read_text(encoding='utf-8')))
    if any(digest(Path(p)) != sha for p, sha in pins.items()) or not verify(directory)['integrity_pass']: raise ValueError('Workflow changed during junction review')
    result.update(inputs=pins, lineage=[n for n, _ in lineage], workflow_integrity_pass=True)
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan'); parser.add_argument('workflow'); parser.add_argument('native_task'); parser.add_argument('--out', required=True)
    args = parser.parse_args(); print(json.dumps(from_workflow(args.plan, args.workflow, args.native_task, args.out)['counts'], indent=2))
    raise SystemExit(2)
