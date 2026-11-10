"""Bind a saved local chain to inherited design flows and isolated straight friction."""
import argparse
import html
import importlib.metadata
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.system as system
import numpy as np

from . import duct_fitting_chain as chain_tool
from . import duct_fitting_span as span_tool
from . import rectangular_tee_transitions as composition
from . import rectangular_transition as transition
from .duct_equivalent import calculate as straight_friction
from .cli import digest
from .tee_geometry import stable_guid

ROOT = Path(__file__).resolve().parents[2]


def render(result):
    def esc(value): return html.escape(str(value))
    straight = []
    for row in result['straight_sections']:
        calc = row['calculation']
        values = [row['source_section'], f"{row['length_m']:.4f}", f"{row['width_m']*1000:.0f} × {row['height_m']*1000:.0f}",
            f"{row['flow_m3_s']*1000:.3f}", f"{calc['actual_velocity_m_s']:.4f}", f"{calc['equivalent_round_velocity_m_s']:.4f}",
            f"{calc['friction_Pa_m']:.5f}", f"{row['straight_friction_Pa']:.5f}"]
        straight.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    missing = []
    for row in result['missing_fitting_path_losses']:
        first = result['port_flows'][row['inlet_port_guid']]; last = result['port_flows'][row['outlet_port_guid']]
        values = [first['source_node'], row['predefined_type'], first['source_section']+' → '+last['source_section'],
            f"{row['inlet_actual_velocity_m_s']:.4f}", f"{row['outlet_actual_velocity_m_s']:.4f}", 'Pending source basis']
        missing.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    path_rows = []
    for row in result['boundary_paths']:
        outlet = result['port_flows'][row['outlet_port_guid']]
        values = [outlet['source_node'], outlet['source_section'], f"{row['outlet_flow_m3_s']*1000:.3f}",
            f"{row['known_straight_friction_Pa']:.5f}", row['missing_fitting_path_count'], 'Pending']
        path_rows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    path_html = '<h2>Separate inlet-to-outlet paths</h2><p>Parallel outlets are separate pressure paths. Known straight contributions exclude missing fitting losses; critical path and fan duty remain undetermined. Shared cap interfaces describe connectivity, not verified joint losses.</p><table><tr><th>Outlet node</th><th>Source section</th><th>Outlet L/s</th><th>Known straight Pa</th><th>Missing fitting paths</th><th>Full path pressure</th></tr>'+''.join(path_rows)+'</table>'
    air = result['air']; basis = result['air_source_basis']
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Local Duct Flow and Straight Friction</title><style>body{font:16px/1.5 Arial;color:#20343c;max-width:1250px;margin:35px auto;padding:0 20px}h1{line-height:1.2}.pending{background:#fff0d2;padding:16px;border-left:5px solid #b47016}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #cbd4d8;padding:8px;text-align:left}th{background:#eaf0f2}a{color:#075c70}</style><h1>Local Duct Flow and Straight Friction</h1><p class="pending"><strong>Complete pressure assessment pending.</strong> '+str(len(missing))+' fitting paths require applicable loss data. Full chain pressure drop is unavailable.</p><p>Source-prescribed local flows conserve at all saved products,interfaces and boundaries. This preliminary local study retains source construction and condition assumptions; product,installation and full-network acceptance remain pending.</p><h2>Local design case</h2><p>Boundary inlet: <strong>'+f"{result['boundary_inlet_flow_m3_s']*1000:.3f}"+' L/s</strong>; boundary outlet: <strong>'+f"{result['boundary_outlet_flow_m3_s']*1000:.3f}"+' L/s</strong>. '+str(len(result['port_flows']))+' saved ports and '+str(len(result['interfaces']))+' interfaces checked.</p><p>Inherited air conditions: density '+f"{air['density_kg_m3']:.4g}"+' kg/m³; dynamic viscosity '+f"{air['viscosity_Pa_s']:.4g}"+' Pa·s; roughness '+f"{air['roughness_m']*1000:.4g}"+' mm. These are source design conditions and assumptions.</p><h2>Isolated straight contribution</h2><p>Equivalent-round straight friction; actual rectangular and equivalent-round velocities remain distinct. Saved straight length excludes both fitting reaches.</p><table><tr><th>Source section</th><th>Model length m</th><th>Inside size mm</th><th>Flow L/s</th><th>Actual velocity m/s</th><th>Equivalent-round velocity m/s</th><th>Gradient Pa/m</th><th>Straight contribution Pa</th></tr>'+''.join(straight)+'</table><p><strong>Straight subtotal: '+f"{result['straight_friction_subtotal_Pa']:.5f}"+' Pa.</strong> Fitting body losses and their wall-friction conventions remain unresolved.</p>'+path_html+'<h2>Missing fitting path data</h2><table><tr><th>Source node</th><th>Body</th><th>Source flow path</th><th>Actual inlet m/s</th><th>Actual outlet m/s</th><th>Loss basis</th></tr>'+''.join(missing)+'</table><details><summary>Inherited source basis and evidence</summary><p>'+esc(basis['basis'])+'</p><p>'+esc(result['geometry_basis'])+'</p><p><a href="analysis.json">Source hashes,native checks,port quantities and full numerical evidence</a></p></details></html>'


def source_schedule(plan, workflow, native_task):
    from .workflow import local_path, verify
    if not verify(workflow)['integrity_pass']: raise ValueError('Original native source workflow changed')
    report = json.loads((workflow/'workflow.json').read_text(encoding='utf-8'))
    if report['inputs'].get(str(plan)) != digest(plan): raise ValueError('Source plan/workflow mismatch')
    tasks = {t['id']: t for t in json.loads(plan.read_text(encoding='utf-8'))['tasks']}
    name = native_task
    for kind in ('duct_sheet_native', 'duct_sheet', 'duct_schedule'):
        task = tasks.get(name, {})
        if task.get('kind') != kind or report['tasks'].get(name, {}).get('status') != 'pass': raise ValueError('Passing native/sheet/schedule source ancestry required')
        if kind != 'duct_schedule': name = task.get('depends_on')
    path = workflow/name/'results.json'; project = local_path(plan.parent, task['project'])
    saved = json.loads(path.read_text(encoding='utf-8'))
    if saved.get('status') != 'pass' or saved.get('input_sha256') != digest(project) or any(r.get('failures') for r in saved['sections']): raise ValueError('Source selected schedule/project correspondence required')
    rows = {r['id']: r['inputs'] for r in saved['sections']}
    if len(rows) != len(saved['sections']): raise ValueError('Unique source sections required')
    return saved['air'], rows, path, project


def bind_flows(project, directory, model):
    project, data, plan, workflow, ends = span_tool.prepare(project)
    air, schedule, schedule_path, schedule_project = source_schedule(plan, workflow, data['native_task'])
    assigned = {}
    def assign(guid, section, node):
        if section not in schedule: raise ValueError('Unknown source schedule section')
        row = schedule[section]; q = row['flow_m3_s']
        if type(q) not in (int, float) or not math.isfinite(q) or q <= 0: raise ValueError('Positive inherited design flow required')
        item = dict(flow_m3_s=q, source_section=section, source_node=node, classification='inherited preliminary design flow')
        if guid in assigned and assigned[guid] != item: raise ValueError('Conflicting source-to-port flow assignment')
        assigned[guid] = item
    for i, end in enumerate(ends, 1):
        _, _, _, spec, children = composition.prepare(end['project'])
        binding = json.loads(end['binding'].read_text(encoding='utf-8'))
        review = json.loads((directory/'span'/('endpoint-'+str(i))/'junction-review.json').read_text(encoding='utf-8'))
        nodes = [n for n in review['nodes'] if n['node'] == binding['node']]
        if len(nodes) != 1: raise ValueError('Exact inherited node required')
        incidents = {r['section']: r for r in nodes[0]['incidents']}
        if set(incidents) != set(binding['arms'].values()): raise ValueError('Exact source node/arm coverage required')
        for arm, section in binding['arms'].items():
            incident = incidents[section]; row = schedule[section]
            if not np.allclose([row['width_m'], row['height_m']], [incident['width_m'], incident['height_m']], atol=1e-10, rtol=0) or not math.isclose(row['flow_m3_s']*1000, incident['flow_L_s'], rel_tol=1e-12): raise ValueError('Source node/schedule flow or size differs')
            guid = stable_guid(spec, 'IfcDistributionPort', 'RECTANGULAR-TEE', arm)
            expected_direction = 'SINK' if incident['role'] == 'incoming' else 'SOURCE'
            if model.by_guid(guid).FlowDirection != expected_direction: raise ValueError('Saved port direction differs from inherited source flow')
            assign(guid, section, binding['node'])
            if arm in children:
                for name in ('start', 'end'): assign(stable_guid(children[arm], 'IfcDistributionPort', transition.KEY, name), section, binding['node'])
    for name in ('near', 'far'):
        assign(stable_guid(data, 'IfcDistributionPort', span_tool.KEY, data['section'], name), data['section'], 'source-bound connecting span')
    if set(assigned) != {p.GlobalId for p in model.by_type('IfcDistributionPort')}: raise ValueError('Exact complete saved-port flow coverage required')
    return assigned, air, schedule, schedule_path, schedule_project


def section_at_port(obj, port):
    body = obj.Representation.Representations[0].Items[0]
    if obj.is_a('IfcDuctSegment'):
        profile = body.SweptArea; return profile.XDim-2*profile.WallThickness, profile.YDim-2*profile.WallThickness
    if obj.PredefinedType == 'JUNCTION':
        profile = body.SecondOperand.FirstOperand.SweptArea; return profile.XDim, profile.YDim
    if obj.PredefinedType == 'TRANSITION':
        points = np.asarray([p.Coordinates for face in body.SecondOperand.Outer.CfsFaces for bound in face.Bounds for p in bound.Bound.Polygon])
        station = points[:, 2].min() if port.Name == 'start' else points[:, 2].max()
        ring = points[np.isclose(points[:, 2], station, atol=1e-10, rtol=0)]
        return float(np.ptp(ring[:, 0])), float(np.ptp(ring[:, 1]))
    raise ValueError('Unsupported saved fitting cross-section')


def boundary_paths(ports, products, interfaces, straight, missing, boundaries):
    """Trace a divergent local tree; never add losses from parallel outlets."""
    edges = {g: [] for g in ports}; indegree = dict.fromkeys(ports, 0)
    def add(a, b, kind, product=None, known=None):
        if a not in ports or b not in ports or a == b:
            raise ValueError('Invalid directed pressure-path edge')
        edges[a].append(dict(inlet_port_guid=a, outlet_port_guid=b, kind=kind,
            product_guid=product, straight_friction_Pa=known))
        indegree[b] += 1
    for row in interfaces:
        add(row['source_port'], row['sink_port'], 'shared_cap_interface')
    for row in straight:
        owned = {g: p for g, p in ports.items() if p['owner_guid'] == row['guid']}
        ins = [g for g, p in owned.items() if p['direction'] == 'SINK']
        outs = [g for g, p in owned.items() if p['direction'] == 'SOURCE']
        if len(ins) != 1 or len(outs) != 1: raise ValueError('One-in/one-out pressure span required')
        add(ins[0], outs[0], 'straight', row['guid'], row['straight_friction_Pa'])
    for row in missing:
        add(row['inlet_port_guid'], row['outlet_port_guid'], 'fitting', row['product_guid'])
    roots = [g for g in boundaries if ports[g]['direction'] == 'SINK']
    leaves = {g for g in boundaries if ports[g]['direction'] == 'SOURCE'}
    if len(roots) != 1 or not leaves or any(n != (0 if g in roots else 1) for g, n in indegree.items()):
        raise ValueError('One-inlet divergent pressure tree required; merging and cycles unsupported')
    if {g for g, rows in edges.items() if not rows} != leaves:
        raise ValueError('Pressure-path leaves must match saved outlet boundaries')
    stack = [(roots[0], [], frozenset())]; paths = []; visited = set()
    while stack:
        node, steps, ancestors = stack.pop()
        if node in ancestors: raise ValueError('Cyclic pressure path')
        visited.add(node)
        if node in leaves:
            paths.append(dict(inlet_port_guid=roots[0], outlet_port_guid=node,
                outlet_flow_m3_s=ports[node]['flow_m3_s'], steps=steps,
                known_straight_friction_Pa=math.fsum(s['straight_friction_Pa'] for s in steps if s['kind'] == 'straight'),
                missing_fitting_path_count=sum(s['kind'] == 'fitting' for s in steps),
                complete_total_pressure_drop_Pa=None, status='pending'))
            if len(paths) > 256: raise ValueError('Local pressure-path budget exceeded')
        for step in sorted(edges[node], key=lambda s: s['outlet_port_guid'], reverse=True):
            stack.append((step['outlet_port_guid'], steps+[step], ancestors|{node}))
    if visited != set(ports) or {s['product_guid'] for p in paths for s in p['steps'] if s['product_guid']} != {p['guid'] for p in products}:
        raise ValueError('Pressure paths do not cover the complete saved model')
    return paths


def calculate(model, assigned, air):
    if not assigned or not model.by_type('IfcDistributionElement') or set(assigned) != {p.GlobalId for p in model.by_type('IfcDistributionPort')}: raise ValueError('Every saved port in a nonempty model requires exactly one source flow')
    if set(air) != {'density_kg_m3', 'viscosity_Pa_s', 'roughness_m'}: raise ValueError('Exact inherited air properties required')
    rho = air['density_kg_m3']
    if any(type(air[k]) not in (int, float) or not math.isfinite(air[k]) or air[k] <= 0 for k in ('density_kg_m3', 'viscosity_Pa_s')) or type(air['roughness_m']) not in (int, float) or not math.isfinite(air['roughness_m']) or air['roughness_m'] < 0: raise ValueError('Finite positive air density/viscosity and nonnegative roughness required')
    ports = {}; products = []; straight = []; missing = []
    for obj in model.by_type('IfcDistributionElement'):
        owned = system.get_ports(obj)
        for port in owned:
            q = assigned[port.GlobalId]['flow_m3_s']
            if type(q) not in (int, float) or not math.isfinite(q) or q <= 0 or port.FlowDirection not in ('SOURCE', 'SINK'): raise ValueError('Positive directed prescribed port flows required')
            w, h = section_at_port(obj, port)
            if any(not math.isfinite(v) or v <= 0 for v in (w, h)): raise ValueError('Positive saved internal section required')
            velocity = q/(w*h)
            if not math.isfinite(velocity) or not math.isfinite(rho*velocity**2/2): raise ValueError('Derived velocity/pressure overflowed')
            ports[port.GlobalId] = dict(**assigned[port.GlobalId], owner_guid=obj.GlobalId, direction=port.FlowDirection,
                width_m=w, height_m=h, actual_velocity_m_s=velocity, actual_velocity_pressure_Pa=rho*velocity**2/2)
        incoming = [p for p in owned if p.FlowDirection == 'SINK']; outgoing = [p for p in owned if p.FlowDirection == 'SOURCE']
        qin = math.fsum(ports[p.GlobalId]['flow_m3_s'] for p in incoming); qout = math.fsum(ports[p.GlobalId]['flow_m3_s'] for p in outgoing)
        if not incoming or not outgoing or not math.isclose(qin, qout, rel_tol=1e-12, abs_tol=1e-12): raise ValueError('Saved product flow is not conserved')
        products.append(dict(guid=obj.GlobalId, ifc_class=obj.is_a(), incoming_flow_m3_s=qin, outgoing_flow_m3_s=qout, continuity_pass=True))
        if obj.is_a('IfcDuctSegment'):
            if len(incoming) != 1 or len(outgoing) != 1: raise ValueError('One-in/one-out straight required')
            source = ports[incoming[0].GlobalId]; width, height = source['width_m'], source['height_m']
            if not np.allclose([width, height], section_at_port(obj, outgoing[0]), atol=1e-10, rtol=0): raise ValueError('Straight saved end sections differ')
            length = obj.Representation.Representations[0].Items[0].Depth
            if not math.isfinite(length) or length <= 0: raise ValueError('Positive saved straight length required')
            friction = straight_friction(flow_m3_s=qin, width_m=width, height_m=height, **air)
            straight.append(dict(guid=obj.GlobalId, source_section=source['source_section'], length_m=length, width_m=width, height_m=height,
                flow_m3_s=qin, calculation=friction, straight_friction_Pa=friction['friction_Pa_m']*length))
        else:
            for inlet in incoming:
                for outlet in outgoing:
                    missing.append(dict(product_guid=obj.GlobalId, ifc_class=obj.is_a(), predefined_type=obj.PredefinedType,
                        inlet_port_guid=inlet.GlobalId, outlet_port_guid=outlet.GlobalId, coefficient=None,
                        inlet_actual_velocity_m_s=ports[inlet.GlobalId]['actual_velocity_m_s'], outlet_actual_velocity_m_s=ports[outlet.GlobalId]['actual_velocity_m_s'],
                        required_basis=['Applicable rectangular fitting/source geometry and flow ratio', 'Total-pressure path coefficient and explicit actual-port reference velocity',
                            'Source citation/edition and applicability', 'Wall-friction inclusion convention for the whole fitting body']))
    links = []; connected = set()
    for relation in model.by_type('IfcRelConnectsPorts'):
        a, b = relation.RelatingPort.GlobalId, relation.RelatedPort.GlobalId
        if a not in ports or b not in ports or ports[a]['direction'] != 'SOURCE' or ports[b]['direction'] != 'SINK' or not math.isclose(ports[a]['flow_m3_s'], ports[b]['flow_m3_s'], rel_tol=1e-12, abs_tol=1e-12): raise ValueError('Saved interface flows/directions disagree')
        if a in connected or b in connected: raise ValueError('One peer per connected port required')
        connected.update((a, b)); links.append(dict(source_port=a, sink_port=b, flow_m3_s=ports[a]['flow_m3_s'], continuity_pass=True))
    boundaries = {g: row for g, row in ports.items() if g not in connected}
    inlet = math.fsum(p['flow_m3_s'] for p in boundaries.values() if p['direction'] == 'SINK')
    outlet = math.fsum(p['flow_m3_s'] for p in boundaries.values() if p['direction'] == 'SOURCE')
    if not math.isclose(inlet, outlet, rel_tol=1e-12, abs_tol=1e-12): raise ValueError('Saved local boundary flows are not conserved')
    paths = boundary_paths(ports, products, links, straight, missing, boundaries)
    return dict(status='pending', port_flows=ports, products=products, interfaces=links, boundary_ports=list(boundaries),
        boundary_inlet_flow_m3_s=inlet, boundary_outlet_flow_m3_s=outlet, flow_continuity_pass=True,
        straight_sections=straight, straight_friction_subtotal_Pa=math.fsum(r['straight_friction_Pa'] for r in straight),
        boundary_paths=paths, boundary_path_accounting_pass=True, critical_path=None,
        boundary_path_scope='Directed local inlet-to-outlet paths; shared-cap edges describe connectivity only. Unknown fitting/joint losses, outlet pressure requirements and fan duty are not inferred. Straight subtotal across products is not a branched-system pressure drop.',
        missing_fitting_path_losses=missing, pressure_budget_complete=False, complete_chain_pressure_drop_Pa=None,
        design_accepted=False, scope='Source-prescribed saved-port flow conservation and isolated saved straight-friction contribution only; fitting total-pressure losses, boundary pressure budget, fan duty, installation and regulatory acceptance pending')


def run(project, directory, out):
    from .workflow import verify
    from fluids import friction_factor
    project, directory, out = [Path(p).resolve() for p in (project, directory, out)]
    if out.exists() or not out.is_relative_to(ROOT) or out == directory or out.is_relative_to(directory) or directory.is_relative_to(out) or out == project or out in project.parents: raise ValueError('New repository-local analysis outside immutable chain/source required')
    versions = {k: importlib.metadata.version(k) for k in ('ifcopenshell', 'manifold3d', 'fluids')}
    if versions != {'ifcopenshell': '0.8.5', 'manifold3d': '3.5.4', 'fluids': '1.3.1'}: raise ValueError('Pinned native/material/friction runtimes required')
    record_path = directory/'chain.json'; record = json.loads(record_path.read_text(encoding='utf-8'))
    if record.get('chain_checks_pass') is not True or record.get('inputs', {}).get(str(project)) != digest(project): raise ValueError('Passing exact source-chain producer required')
    method_file = Path(straight_friction.__code__.co_filename).resolve()
    engine_file = Path(friction_factor.__code__.co_filename).resolve()
    pins = {str(p): digest(p) for p in (project, record_path, directory/'chain.ifc', directory/'source-snapshot.json', Path(__file__), method_file, engine_file)}
    if pins[str(directory/'chain.ifc')] != record['ifc_sha256'] or pins[str(directory/'source-snapshot.json')] != record['snapshot_sha256']: raise ValueError('Saved chain or source snapshot changed')
    for section in ('inputs', 'component_artifacts'):
        for name, sha in record[section].items():
            path = Path(name) if section == 'inputs' else (directory/name).resolve()
            if section == 'component_artifacts' and not path.is_relative_to(directory): raise ValueError('Component artifact escaped source chain')
            if not path.is_file() or digest(path) != sha: raise ValueError('Chain source or component artifact changed')
            pins[str(path)] = sha
    expected = json.loads((directory/'source-snapshot.json').read_text(encoding='utf-8'))
    _, data, _, workflow, _ = span_tool.prepare(project)
    native_checks = chain_tool.inspect(directory/'chain.ifc', data, expected)
    model = ifcopenshell.open(str(directory/'chain.ifc')); assigned, air, schedule, schedule_path, schedule_project = bind_flows(project, directory, model)
    for path in (schedule_path, schedule_project):
        name, sha = str(path), digest(path)
        if name in pins and pins[name] != sha: raise ValueError('Source schedule changed during binding')
        pins[name] = sha
    result = calculate(model, assigned, air)
    for row in result['straight_sections']:
        selected = schedule[row['source_section']]
        if not np.allclose([row['width_m'], row['height_m'], row['flow_m3_s']], [selected['width_m'], selected['height_m'], selected['flow_m3_s']], atol=1e-10, rtol=0): raise ValueError('Saved straight section differs from inherited selected schedule')
    if any(digest(Path(p)) != sha for p, sha in pins.items()) or not verify(workflow)['integrity_pass']: raise ValueError('Chain or native source changed during analysis')
    result.update(inputs=pins, versions=versions, air=air, native_chain_checks=native_checks, same_saved_ifc_verified=True,
        air_source_basis=dict(project=str(schedule_project), sha256=pins[str(schedule_project)], basis=json.loads(schedule_project.read_text(encoding='utf-8')).get('basis'),
            interpretation='Inherited source design conditions and declared assumptions;not new measured environmental/material properties'),
        geometry_basis='Saved model dimensions and separate straight length;not measured installed geometry',
        friction_method_sha256=pins[str(method_file)], friction_engine_sha256=pins[str(engine_file)],
        method='Existing duct_equivalent turbulent equivalent-round friction;actual rectangular velocities retained separately for fitting references')
    out.mkdir(parents=True)
    (out/'analysis.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (out/'index.html').write_text(render(result), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('project'); parser.add_argument('chain_directory'); parser.add_argument('--out', required=True)
    args = parser.parse_args(); result = run(args.project, args.chain_directory, args.out)
    print(result['status'], result['straight_friction_subtotal_Pa'], 'Pa straight contribution;',len(result['missing_fitting_path_losses']),'fitting paths missing'); raise SystemExit(2)
