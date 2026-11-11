"""Revise explicit planar terminal symbols,ID labels and centreline flex endpoints."""
import argparse
import json
import math
from pathlib import Path
import ezdxf
from .air_terminal_drawing import inspect
from .cad_intake import METRES_PER_UNIT
from .cli import digest
from .duct_sheet import snapshot


def run(drawing,old_allocation,new_allocation,duct_project,binding,settings,output):
    paths=[Path(p).resolve() for p in (drawing,old_allocation,new_allocation,duct_project,binding,settings)]
    output=Path(output).resolve()
    pins={str(p):digest(p) for p in paths}
    from . import air_terminal_drawing,air_tree_flow,duct_sheet
    for module in (air_terminal_drawing,air_tree_flow,duct_sheet):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    if output.exists() or any(output==Path(p) or output in Path(p).parents for p in pins):raise ValueError('New revision output separate from all source files required')
    old,new,project,spec,config=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths[1:]]
    if set(config)!={'layers','labels','basis'} or not isinstance(config['basis'],str) or not config['basis'].strip():raise ValueError('Explicit layers,ID-label bindings and revision basis required')
    if spec.get('source_sha256')!=pins[str(paths[0])]:raise ValueError('Original drawing binding hash differs')
    if old['load']!=new['load'] or old['turndown']!=new['turndown']:raise ValueError('Position-only revision cannot replace source load or turndown')
    for allocation in (old,new):
        if not math.isclose(math.fsum(t['maximum_flow_L_s'] for t in allocation['terminals']),allocation['load']['supply_flow_L_s'],rel_tol=1e-12):
            raise ValueError('Terminal allocation must conserve the unchanged total airflow')
    old_points={t['id']:t['center_m'] for t in old['terminals']};new_points={t['id']:t['center_m'] for t in new['terminals']}
    if len(old_points)!=len(old['terminals']) or len(new_points)!=len(new['terminals']) or set(old_points)!=set(new_points):raise ValueError('Exact unique original/new terminal identity coverage required')
    if set(config['labels'])!=set(old_points):raise ValueError('Complete explicit terminal ID-label inventory required')
    doc=ezdxf.readfile(paths[0]);before=snapshot(doc)
    prior=inspect(doc,old,project['tree'],spec,config['layers']);scale=METRES_PER_UNIT[doc.units]
    routes={r['terminal']:r for g in prior['groups'] for r in g['routes']}
    used=set();allowed=set();changes=[]
    for tid,point in old_points.items():
        label=config['labels'][tid]
        if not isinstance(label,dict) or set(label)!={'handle','expected_text'} or label['expected_text']!=tid:raise ValueError('Exact original ID label required')
        entity=doc.entitydb.get(label['handle'])
        if entity is None or entity.dxftype()!='TEXT' or entity.dxf.handle not in before or entity.dxf.handle in used or entity.dxf.text!=tid:
            raise ValueError('Unique modelspace TEXT ID label correspondence required')
        used.add(entity.dxf.handle)
        new_point=new_points[tid]
        if len(new_point)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in new_point):raise ValueError('Finite new planar metre centre required')
        dx,dy=[(v-u)/scale for u,v in zip(point,new_point)]
        if dx==0 and dy==0:continue
        route=routes[tid];panel=doc.entitydb[route['terminal_handle']];flex=doc.entitydb[route['flex_handle']]
        old_xyz=tuple(point)+(0.,);new_xyz=tuple(v/scale for v in new_point)+(0.,)
        if math.dist([v*scale for v in flex.dxf.start],old_xyz)<=1e-8:flex.dxf.start=new_xyz
        elif math.dist([v*scale for v in flex.dxf.end],old_xyz)<=1e-8:flex.dxf.end=new_xyz
        else:raise ValueError('Flex endpoint does not match original terminal')
        # Explicit XY vertices avoid introducing default elevation/extrusion
        # attributes that ezdxf legitimately omits again during serialization.
        panel.set_points([(x+dx,y+dy,start_width,end_width,bulge) for x,y,start_width,end_width,bulge in panel.get_points()])
        entity.translate(dx,dy,0)
        handles=[panel.dxf.handle,flex.dxf.handle,entity.dxf.handle]
        if allowed.intersection(handles):raise ValueError('Changed terminal geometry bindings overlap')
        allowed.update(handles);changes.append(dict(terminal=tid,old_center_m=point,new_center_m=new_point,handles=handles))
    after=snapshot(doc)
    if set(before)!=set(after) or any(tags!=after[h] for h,tags in before.items() if h not in allowed):raise ValueError('Unbound source entity changed during terminal revision')
    revised=inspect(doc,new,project['tree'],spec,config['layers'])
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Terminal revision source changed during preparation')
    output.mkdir(parents=True);target=output/'Supply Air Distribution.dxf';doc.saveas(target)
    reopened=ezdxf.readfile(target)
    if snapshot(reopened)!=after:raise ValueError('Saved terminal revision differs from expected entities')
    saved=inspect(reopened,new,project['tree'],spec,config['layers'])
    if saved!=revised:raise ValueError('Saved terminal/group/route correspondence differs')
    result=dict(inputs=pins,dxf_sha256=digest(target),changes=changes,changed_entity_count=len(allowed),unchanged_unbound_modelspace=True,
        old_correspondence=prior,new_correspondence=saved,basis=config['basis'],saved_dxf_correspondence=True,
        native_reopen_pass=False,plot_visual_review='pending',design_accepted=False,
        scope='Explicit planar terminal symbol and ID-label translation;straight flex centreline endpoint revision only. Original rigid/VAV geometry and other entities preserved. New airflow sizing,native drawing,physical flex/products,elevations,obstacles and full engineering review remain separate.')
    (output/'revision.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('drawing','old_allocation','new_allocation','duct_project','binding','settings'):p.add_argument(name)
    p.add_argument('--out',required=True);a=p.parse_args()
    r=run(a.drawing,a.old_allocation,a.new_allocation,a.duct_project,a.binding,a.settings,a.out)
    print(len(r['changes']),'terminals revised in saved DXF;native and engineering acceptance pending')
