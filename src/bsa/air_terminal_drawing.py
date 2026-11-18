"""Read-only correspondence of planar terminal symbols and straight flex lines."""
import argparse
import json
import math
from pathlib import Path
import ezdxf
from .air_tree_flow import aggregate
from .cad_intake import METRES_PER_UNIT
from .cli import digest


def inspect(doc, allocation, tree, binding, layers):
    if (set(layers) != {'supply', 'vav', 'terminal', 'flex'}
            or any(not isinstance(layer, str) or not layer for layer in layers.values())
            or len({layer.casefold() for layer in layers.values()}) != 4):
        raise ValueError('Four distinct scoped layers required')
    if doc.units not in METRES_PER_UNIT:
        raise ValueError('Known drawing units required')
    scale = METRES_PER_UNIT[doc.units]
    def point(p):
        q = tuple(float(v) * scale for v in p)
        if len(q) != 3 or not all(math.isfinite(v) for v in q) or abs(q[2]) > 1e-8:
            raise ValueError('Finite world-XY planar geometry required')
        return q
    def near(a,b):
        return math.dist(a,b) <= 1e-8
    def take(pool, predicate, expected, *, center_of=None, target=None):
        matches = [e for e in pool if predicate(e)]
        if len(matches) != 1:
            message = f'Missing or ambiguous saved geometry correspondence for {expected}; found {len(matches)} matches'
            if center_of is not None:
                candidates = (
                    (math.dist(center, target), entity.dxf.handle, center)
                    for entity in pool if (center := center_of(entity)) is not None
                )
                nearest = min(candidates, default=None)
                if nearest is not None:
                    gap, handle, center = nearest
                    message += f'; nearest saved candidate handle {handle} at {center} m, deviation {gap:.6g} m'
            raise ValueError(message)
        pool.remove(matches[0])
        return matches[0]
    pools = {k:[e for e in doc.modelspace() if e.dxf.layer.casefold() == layer.casefold()]
             for k,layer in layers.items()}
    kinds = dict(supply='LINE',vav='CIRCLE',terminal='LWPOLYLINE',flex='LINE')
    if any(e.dxftype() != kinds[k] for k,es in pools.items() for e in es):
        raise ValueError('Unsupported entity on scoped layer')
    aggregation = aggregate(tree, allocation['terminals'])
    if set(binding['sections']) != {s['id'] for s in tree['sections']}:
        raise ValueError('Complete rigid section binding required')
    nodes = {}
    node_sections = {}
    rigid_sections = []
    for section in tree['sections']:
        b = binding['sections'][section['id']]
        pair = (b['from_node'],b['to_node'])
        if pair not in ((section['from'],section['to']),(section['to'],section['from'])):
            raise ValueError('Rigid binding differs from tree')
        a,z = tuple(b['from_m']),tuple(b['to_m'])
        if any(len(p)!=3 or not all(type(v) in (int,float) and math.isfinite(v) for v in p) or abs(p[2])>1e-8 for p in (a,z)):
            raise ValueError('Finite planar binding required')
        line = take(pools['supply'],lambda e:(near(point(e.dxf.start),a) and near(point(e.dxf.end),z)) or (near(point(e.dxf.start),z) and near(point(e.dxf.end),a)),
             f"section {section['id']} from {a} to {z} m on {layers['supply']}")
        saved_start, saved_end = point(line.dxf.start), point(line.dxf.end)
        if near(a, z) or near(saved_start, saved_end):
            raise ValueError(f"Rigid section {section['id']} (handle {line.dxf.handle}) has no distinct planar endpoints")
        if not (near(saved_start, a) and near(saved_end, z)):
            saved_start, saved_end = saved_end, saved_start
        rigid_sections.append(dict(section=section['id'], handle=line.dxf.handle,
                                   from_node=pair[0], to_node=pair[1],
                                   saved_from_m=list(saved_start), saved_to_m=list(saved_end),
                                   saved_plan_length_m=math.dist(saved_start, saved_end)))
        for node,p in zip(pair,(saved_start,saved_end)):
            incident = node_sections.setdefault(node, [])
            for prior_section, prior_handle, prior_point in incident:
                if not near(prior_point, p):
                    raise ValueError(f"Disconnected rigid node {node}: section {prior_section} "
                                     f"(handle {prior_handle}) at {prior_point} m and section {section['id']} "
                                     f"(handle {line.dxf.handle}) at {p} m, gap {math.dist(prior_point, p):.6g} m")
            incident.append((section['id'], line.dxf.handle, p))
        for node, expected in zip(pair, (a, z)):
            nodes.setdefault(node, expected)
    centers = {}
    for terminal in allocation['terminals']:
        p = tuple(terminal['center_m'])+(0.,)
        if len(p)!=3 or not all(math.isfinite(v) for v in p):
            raise ValueError('Finite planar terminal centre required')
        centers[terminal['id']] = p
    def symbol_center(e):
        pts = list(e.get_points())
        if not e.closed or len(pts)!=4 or any(any(v!=0 for v in p[2:]) for p in pts) or tuple(e.dxf.extrusion)!=(0.,0.,1.):
            raise ValueError('Closed axis-aligned four-corner terminal symbols required')
        xyz = [point((p[0],p[1],e.dxf.elevation)) for p in pts]
        xs,ys = {p[0] for p in xyz},{p[1] for p in xyz}
        if len(xs)!=2 or len(ys)!=2 or len(set(xyz))!=4 or any(a[0]!=b[0] and a[1]!=b[1] for a,b in zip(xyz,xyz[1:]+xyz[:1])):
            raise ValueError('Rectangular terminal symbol required')
        return ((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,xyz[0][2])
    # Read every candidate before matching, including otherwise-unused symbols.
    symbol_centers = {e.dxf.handle:symbol_center(e) for e in pools['terminal']}
    terminals = {tid:take(pools['terminal'],lambda e:near(symbol_centers[e.dxf.handle],p),
                          f"terminal {tid} at {p} m on {layers['terminal']}",
                          center_of=lambda e:symbol_centers[e.dxf.handle],target=p).dxf.handle for tid,p in centers.items()}
    flex_ends = {line.dxf.handle: (point(line.dxf.start), point(line.dxf.end)) for line in pools['flex']}
    groups = []
    for leaf,members in tree['leaf_terminals'].items():
        start = nodes[leaf]
        circle = take(pools['vav'],lambda e:tuple(e.dxf.extrusion)==(0.,0.,1.) and near(point(e.dxf.center),start),
                      f"VAV {leaf} at {start} m on {layers['vav']}", target=start,
                      center_of=lambda e:point(e.dxf.center) if tuple(e.dxf.extrusion)==(0.,0.,1.) else None)
        if not math.isfinite(circle.dxf.radius) or circle.dxf.radius <= 0:
            raise ValueError(f"VAV {leaf} (handle {circle.dxf.handle}) has an invalid symbol radius")
        saved_vav = point(circle.dxf.center)
        for section_id, handle, saved_endpoint in node_sections[leaf]:
            if not near(saved_endpoint, saved_vav):
                raise ValueError(f"VAV {leaf} (handle {circle.dxf.handle}) is separated from section "
                                 f"{section_id} (handle {handle}) by {math.dist(saved_endpoint, saved_vav):.6g} m")
        routes = []
        for tid in members:
            end = centers[tid]
            def matches(line):
                a, b = flex_ends[line.dxf.handle]
                return (near(a, start) and near(b, end)) or (near(a, end) and near(b, start))

            expected = f"VAV {leaf} to terminal {tid} from {start} to {end} m on {layers['flex']}"
            try:
                line = take(pools['flex'], matches, expected)
            except ValueError as error:
                observed = []
                for handle, (a, b) in flex_ends.items():
                    for terminal_side, far_side in ((a, b), (b, a)):
                        if near(terminal_side, end):
                            groups_at_end = [group for group in tree['leaf_terminals'] if near(nodes[group], far_side)]
                            peers = ', '.join(groups_at_end) or 'none'
                            observed.append(f'{handle} to {far_side} m (declared VAV centres: {peers})')
                details = '; '.join(observed) or 'none'
                vav_candidates = []
                if not observed:
                    other_terminals = [centers[peer] for peer in members if peer != tid]
                    for candidate in pools['flex']:
                        handle = candidate.dxf.handle
                        a, b = flex_ends[handle]
                        for vav_side, far_side in ((a, b), (b, a)):
                            if near(vav_side, start) and not any(near(far_side, peer) for peer in other_terminals):
                                offset = math.dist(far_side, end)
                                vav_candidates.append(f'{handle} to {far_side} m ({offset:.6g} m from {tid})')
                hint = ''
                if vav_candidates:
                    hint = f"; unmatched lines at VAV {leaf}: {'; '.join(vav_candidates)}"
                raise ValueError(f'{error}; saved lines at terminal {tid}: {details}{hint}') from error
            if near(start,end):raise ValueError('Zero-length terminal connection')
            saved_start, saved_end = flex_ends[line.dxf.handle]
            if near(saved_start, saved_end):
                raise ValueError(f"Flex handle {line.dxf.handle} for VAV {leaf} to terminal {tid} "
                                 "has no distinct saved endpoints")
            if not (near(saved_start, start) and near(saved_end, end)):
                saved_start, saved_end = saved_end, saved_start
            for peer, handle, actual, symbol in (
                (leaf, circle.dxf.handle, saved_start, saved_vav),
                (tid, terminals[tid], saved_end, symbol_centers[terminals[tid]]),
            ):
                if not near(actual, symbol):
                    raise ValueError(f"Flex handle {line.dxf.handle} endpoint {actual} m is separated from "
                                     f"{peer} (handle {handle}) at {symbol} m by {math.dist(actual, symbol):.6g} m")
            routes.append(dict(terminal=tid,terminal_handle=terminals[tid],flex_handle=line.dxf.handle,
                               plan_length_m=math.dist(start,end),
                               saved_plan_length_m=math.dist(saved_start,saved_end),
                               saved_terminal_center_m=list(symbol_centers[terminals[tid]]),
                               saved_vav_endpoint_m=list(saved_start),
                               saved_terminal_endpoint_m=list(saved_end),
                               vav_endpoint_gap_m=math.dist(saved_start,saved_vav),
                               terminal_endpoint_gap_m=math.dist(saved_end,symbol_centers[terminals[tid]])))
        groups.append(dict(id=leaf,vav_handle=circle.dxf.handle,saved_vav_center_m=list(saved_vav),
                           outlet_count=len(members),maximum_flow_L_s=aggregation['leaf_flow_L_s'][leaf],routes=routes))
    if any(pools.values()):
        details = []
        for role, entities in pools.items():
            if not entities:
                continue
            handles = []
            for entity in entities[:10]:
                handle = entity.dxf.handle
                if role == 'flex':
                    start, end = flex_ends[handle]
                    handle = f'{handle} from {start} to {end} m'
                handles.append(handle)
            details.append(f"{layers[role]} ({len(entities)}): {', '.join(handles)}")
        raise ValueError(f"Unbound entities remain on scoped layers: {'; '.join(details)}")
    return dict(groups=groups,terminal_count=len(centers),rigid_section_count=len(tree['sections']),
                rigid_sections=rigid_sections,
                correspondence_tolerance_m=1e-8,correspondence_pass=True,
                maximum_plan_length_m=max(r['plan_length_m'] for g in groups for r in g['routes']),design_accepted=False,
                scope='Declared group membership matches saved planar symbols and straight centre-to-centre lines. Not physical ports, installed flex length, labels, 3D coordination or regulation acceptance.')


def _inspect_files(paths, layers):
    pins={str(p):digest(p) for p in paths}
    data=[json.loads(p.read_text(encoding='utf-8')) for p in paths[1:]]
    result=inspect(ezdxf.readfile(paths[0]),data[0],data[1]['tree'],data[2],layers)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Source changed during inspection')
    result.update(inputs=pins,layers=layers)
    return result


def _save(output, result):
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)


def run(drawing,allocation,project,binding,output,*,layers):
    paths=[Path(p).resolve() for p in (drawing,allocation,project,binding)]
    output=Path(output).resolve()
    if output.exists() or any(output==p or output in p.parents for p in paths):
        raise ValueError('New output separate from sources required')
    result = _inspect_files(paths, layers)
    _save(output, result)
    return result


def from_workflow(plan,directory,native_task,output,*,layers):
    """Resolve a complete native -> sheet -> schedule -> allocation ancestry."""
    from .workflow import verify,local_path
    plan,directory,output=(Path(p).resolve() for p in (plan,directory,output))
    if output==directory or directory in output.parents or output in directory.parents:
        raise ValueError('Review output must be outside immutable workflow')
    if output.exists():
        raise ValueError('New output separate from sources required')
    manifest=directory/'workflow.json'
    before=digest(manifest)
    plan_sha256=digest(plan)
    if not verify(directory)['integrity_pass']:
        raise ValueError('Workflow source or artifact evidence changed')
    workflow=json.loads(manifest.read_text(encoding='utf-8'))
    if workflow['inputs'].get(str(plan))!=plan_sha256:
        raise ValueError('Plan does not belong to this workflow')
    tasks={t['id']:t for t in json.loads(plan.read_text(encoding='utf-8'))['tasks']}
    lineage=[];name=native_task
    for kind in ('duct_sheet_native','duct_sheet','duct_schedule','air_allocation'):
        task=tasks.get(name,{})
        recorded=workflow['tasks'].get(name,{})
        if task.get('kind')!=kind or recorded.get('kind')!=kind or recorded.get('status')!='pass':
            raise ValueError('Passing native/sheet/schedule/allocation ancestry required')
        lineage.append((name,task));name=task.get('depends_on')
    native,sheet,schedule,allocation=lineage
    project=local_path(plan.parent,schedule[1]['project'])
    schedule_file=(directory/schedule[0]/'results.json').resolve()
    if not schedule_file.is_relative_to(directory):
        raise ValueError('Inherited artifacts must stay inside the verified workflow')
    schedule_sha256=digest(schedule_file)
    saved=json.loads(schedule_file.read_text(encoding='utf-8'))
    if saved['input_sha256']!=digest(project):
        raise ValueError('Schedule project correspondence changed')
    paths=(directory/native[0]/'reopened/source-export.dxf',directory/allocation[0]/'allocation.json',
           project,local_path(plan.parent,sheet[1]['binding']))
    drawing, allocation_file, project, binding = (path.resolve() for path in paths)
    if not all(path.is_relative_to(directory) for path in (drawing, allocation_file)):
        raise ValueError('Inherited artifacts must stay inside the verified workflow')
    result=_inspect_files([drawing, allocation_file, project, binding], layers)
    artifacts = workflow['artifact_hashes']
    if (any(artifacts.get(path.relative_to(directory).as_posix()) != result['inputs'][str(path)]
            for path in (drawing, allocation_file))
            or artifacts.get(schedule_file.relative_to(directory).as_posix()) != schedule_sha256
            or any(workflow['inputs'].get(str(path)) != result['inputs'][str(path)] for path in (project, binding))):
        raise ValueError('Terminal review sources are missing from the verified workflow evidence')
    if (not verify(directory)['integrity_pass'] or digest(manifest)!=before
            or digest(plan)!=plan_sha256 or digest(schedule_file)!=schedule_sha256):
        raise ValueError('Workflow changed during terminal review')
    result.update(workflow_sha256=before,plan_sha256=plan_sha256,schedule_sha256=schedule_sha256,
                  lineage=[name for name,_ in lineage],workflow_integrity_pass=True,
                  generator_sha256=digest(Path(__file__)))
    _save(output, result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('drawing','allocation','project','binding'):p.add_argument(name)
    p.add_argument('--out',required=True)
    for name in ('supply','vav','terminal','flex'):p.add_argument('--'+name+'-layer',required=True)
    a=p.parse_args()
    r=run(a.drawing,a.allocation,a.project,a.binding,a.out,layers={k:getattr(a,k+'_layer') for k in ('supply','vav','terminal','flex')})
    print(r['terminal_count'],'terminal correspondences; installed geometry acceptance pending')
