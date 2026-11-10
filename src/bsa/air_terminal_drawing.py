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
    if set(layers) != {'supply', 'vav', 'terminal', 'flex'} or len(set(layers.values())) != 4:
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
    def take(pool, predicate):
        matches = [e for e in pool if predicate(e)]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous saved geometry correspondence')
        pool.remove(matches[0])
        return matches[0]
    pools = {k:[e for e in doc.modelspace() if e.dxf.layer == layer] for k,layer in layers.items()}
    kinds = dict(supply='LINE',vav='CIRCLE',terminal='LWPOLYLINE',flex='LINE')
    if any(e.dxftype() != kinds[k] for k,es in pools.items() for e in es):
        raise ValueError('Unsupported entity on scoped layer')
    aggregation = aggregate(tree, allocation['terminals'])
    if set(binding['sections']) != {s['id'] for s in tree['sections']}:
        raise ValueError('Complete rigid section binding required')
    nodes = {}
    for section in tree['sections']:
        b = binding['sections'][section['id']]
        pair = (b['from_node'],b['to_node'])
        if pair not in ((section['from'],section['to']),(section['to'],section['from'])):
            raise ValueError('Rigid binding differs from tree')
        a,z = tuple(b['from_m']),tuple(b['to_m'])
        if any(len(p)!=3 or not all(type(v) in (int,float) and math.isfinite(v) for v in p) or abs(p[2])>1e-8 for p in (a,z)):
            raise ValueError('Finite planar binding required')
        take(pools['supply'],lambda e:(near(point(e.dxf.start),a) and near(point(e.dxf.end),z)) or (near(point(e.dxf.start),z) and near(point(e.dxf.end),a)))
        for node,p in zip(pair,(a,z)):
            if node in nodes and not near(nodes[node],p):
                raise ValueError('Disconnected rigid node')
            nodes[node] = p
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
        return ((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,0.)
    # Read every candidate before matching, including otherwise-unused symbols.
    symbol_centers = {e.dxf.handle:symbol_center(e) for e in pools['terminal']}
    terminals = {tid:take(pools['terminal'],lambda e:near(symbol_centers[e.dxf.handle],p)).dxf.handle for tid,p in centers.items()}
    groups = []
    for leaf,members in tree['leaf_terminals'].items():
        start = nodes[leaf]
        circle = take(pools['vav'],lambda e:tuple(e.dxf.extrusion)==(0.,0.,1.) and near(point(e.dxf.center),start))
        routes = []
        for tid in members:
            end = centers[tid]
            line = take(pools['flex'],lambda e:(near(point(e.dxf.start),start) and near(point(e.dxf.end),end)) or (near(point(e.dxf.start),end) and near(point(e.dxf.end),start)))
            if near(start,end):raise ValueError('Zero-length terminal connection')
            routes.append(dict(terminal=tid,terminal_handle=terminals[tid],flex_handle=line.dxf.handle,plan_length_m=math.dist(start,end)))
        groups.append(dict(id=leaf,vav_handle=circle.dxf.handle,outlet_count=len(members),maximum_flow_L_s=aggregation['leaf_flow_L_s'][leaf],routes=routes))
    if any(pools.values()):raise ValueError('Unbound entities remain on scoped layers')
    return dict(groups=groups,terminal_count=len(centers),rigid_section_count=len(tree['sections']),correspondence_pass=True,
                maximum_plan_length_m=max(r['plan_length_m'] for g in groups for r in g['routes']),design_accepted=False,
                scope='Declared group membership matches saved planar symbols and straight centre-to-centre lines. Not physical ports, installed flex length, labels, 3D coordination or regulation acceptance.')


def run(drawing,allocation,project,binding,output,*,layers):
    paths=[Path(p).resolve() for p in (drawing,allocation,project,binding)]
    output=Path(output).resolve()
    if output.exists() or any(output==p or output in p.parents for p in paths):
        raise ValueError('New output separate from sources required')
    pins={str(p):digest(p) for p in paths}
    data=[json.loads(p.read_text(encoding='utf-8')) for p in paths[1:]]
    result=inspect(ezdxf.readfile(paths[0]),data[0],data[1]['tree'],data[2],layers)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Source changed during inspection')
    result.update(inputs=pins,layers=layers)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def from_workflow(plan,directory,native_task,output,*,layers):
    """Resolve a complete native -> sheet -> schedule -> allocation ancestry."""
    from .workflow import verify,local_path
    plan,directory,output=(Path(p).resolve() for p in (plan,directory,output))
    if output==directory or directory in output.parents or output in directory.parents:
        raise ValueError('Review output must be outside immutable workflow')
    if not verify(directory)['integrity_pass']:
        raise ValueError('Workflow source or artifact evidence changed')
    manifest=directory/'workflow.json'
    workflow=json.loads(manifest.read_text(encoding='utf-8'))
    if workflow['inputs'].get(str(plan))!=digest(plan):
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
    schedule_file=directory/schedule[0]/'results.json'
    saved=json.loads(schedule_file.read_text(encoding='utf-8'))
    if saved['input_sha256']!=digest(project):
        raise ValueError('Schedule project correspondence changed')
    before=digest(manifest)
    result=run(directory/native[0]/'reopened/source-export.dxf',directory/allocation[0]/'allocation.json',
               project,local_path(plan.parent,sheet[1]['binding']),output,layers=layers)
    if digest(manifest)!=before or not verify(directory)['integrity_pass']:
        raise ValueError('Workflow changed during terminal review')
    result.update(workflow_sha256=before,plan_sha256=digest(plan),schedule_sha256=digest(schedule_file),
                  lineage=[name for name,_ in lineage],workflow_integrity_pass=True,
                  generator_sha256=digest(Path(__file__)))
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('drawing','allocation','project','binding'):p.add_argument(name)
    p.add_argument('--out',required=True)
    for name in ('supply','vav','terminal','flex'):p.add_argument('--'+name+'-layer',required=True)
    a=p.parse_args()
    r=run(a.drawing,a.allocation,a.project,a.binding,a.out,layers={k:getattr(a,k+'_layer') for k in ('supply','vav','terminal','flex')})
    print(r['terminal_count'],'terminal correspondences; installed geometry acceptance pending')
