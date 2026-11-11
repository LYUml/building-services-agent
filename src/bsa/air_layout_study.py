"""Compare declared diffuser positions using existing allocation and bounded throw engines."""
import argparse
import copy
import html
import json
import math
from pathlib import Path
from shapely.geometry import Point,LineString,box,shape
from .air_allocation import prepare,reference_files
from .cli import digest
from .terminal_throw import evaluate,positive

COINCIDENCE_M=1e-7
DIRECTIONS=dict(east=(1,0),west=(-1,0),north=(0,1),south=(0,-1))


def evaluate_variant(boundary,project,catalogue,variant,panel_size_m,ratio_range):
    if set(variant)!={'id','basis','changes'} or any(not isinstance(variant[k],str) or not variant[k].strip() for k in ('id','basis')):
        raise ValueError('Explicit variant identity,basis and changes required')
    if len(panel_size_m)!=2 or len(ratio_range)!=2:raise ValueError('Two panel dimensions and ratio bounds required')
    width,height=map(positive,panel_size_m);low,high=map(positive,ratio_range)
    if low>high:raise ValueError('Ordered diagnostic ratio range required')
    terminals=copy.deepcopy(project['terminals']);by_id={t['id']:t for t in terminals}
    if len(by_id)!=len(terminals):raise ValueError('Unique original terminal inventory required')
    if not isinstance(variant['changes'],list):raise ValueError('Explicit change list required')
    changed=set()
    for row in variant['changes']:
        if set(row)!={'id','center_m'} or row['id'] not in by_id or row['id'] in changed:
            raise ValueError('Each changed terminal must be a unique existing source ID')
        by_id[row['id']]['center_m']=row['center_m'];changed.add(row['id'])
    allocation=prepare(boundary,terminals,project['load_inputs'],project['turndown'])
    space=shape(boundary);span=math.hypot(space.bounds[2]-space.bounds[0],space.bounds[3]-space.bounds[1])*2+1
    panels={t['id']:box(t['center_m'][0]-width/2,t['center_m'][1]-height/2,t['center_m'][0]+width/2,t['center_m'][1]+height/2) for t in terminals}
    outside=[id for id,p in panels.items() if not space.covers(p)]
    pairs=[dict(terminals=[a,b],overlap_m2=panels[a].intersection(panels[b]).area) for i,a in enumerate(panels) for b in list(panels)[i+1:] if panels[a].intersection(panels[b]).area>0]
    cases=[];mismatches=0;ratio_issues=0
    for terminal in allocation['terminals']:
        xy=terminal['center_m'];origin=Point(xy);cell=shape(terminal['geometry'])
        for name,(dx,dy) in DIRECTIONS.items():
            ray=LineString([xy,[xy[0]+dx*span,xy[1]+dy*span]])
            hit=ray.intersection(space.boundary)
            if hit.is_empty:raise ValueError('Missing polygon ray boundary intersection')
            wall=origin.distance(hit);opposing=[]
            for other in terminals:
                vx,vy=[v-u for u,v in zip(xy,other['center_m'])]
                forward=vx*dx+vy*dy;cross=vx*dy-vy*dx
                if forward>COINCIDENCE_M and abs(cross)<=COINCIDENCE_M:
                    opposing.append((forward/2,other['id']))
            aligned=min(opposing) if opposing else None
            length=min(wall,aligned[0]) if aligned else wall
            proxy=origin.distance(ray.intersection(cell.boundary))
            mismatch=not math.isclose(proxy,length,rel_tol=0,abs_tol=COINCIDENCE_M)
            mismatches+=mismatch
            lookup=evaluate(catalogue['rows'],maximum_flow_L_s=terminal['maximum_flow_L_s'],turndown=project['turndown'],characteristic_length_m=length)
            issue=sum(c['ratio'] is None or not low<=c['ratio']<=high for c in lookup['cases'].values());ratio_issues+=issue
            cases.append(dict(terminal=terminal['id'],direction=name,polygon_ray_distance_m=wall,aligned_midpoint_candidate=None if aligned is None else dict(terminal=aligned[1],distance_m=aligned[0]),
                screened_length_m=length,allocation_cell_ray_distance_m=proxy,cell_ray_mismatch=mismatch,lookup=lookup))
    return dict(id=variant['id'],basis=variant['basis'],changes=variant['changes'],allocation=allocation,cases=cases,
        panel_outside_boundary=outside,panel_overlaps=pairs,cell_ray_mismatches=mismatches,diagnostic_ratio_cases_outside_range=ratio_issues,
        geometric_candidate=not(outside or pairs or mismatches or ratio_issues),selected=False,ADPI_verified=False,design_accepted=False,
        pending=['Source wall/column and jet-pattern interpretation','Actual room load and selected criterion applicability','Installation/elevations and ceiling conditions','Revised VAV/flex/rigid connections,sizing and native drawing review'])


def run(allocation_project,lookup_project,study,output):
    allocation_project,lookup_project,study,output=[Path(p).resolve() for p in (allocation_project,lookup_project,study,output)]
    initial={str(p):digest(p) for p in (allocation_project,lookup_project,study)}
    project=json.loads(allocation_project.read_text(encoding='utf-8-sig'));lookup=json.loads(lookup_project.read_text(encoding='utf-8-sig'));spec=json.loads(study.read_text(encoding='utf-8-sig'))
    if set(spec)!={'basis','panel_size_m','ratio_range','references','variants'} or not isinstance(spec['basis'],str) or not spec['basis'].strip():
        raise ValueError('Exact source-backed study fields required')
    if not isinstance(spec['variants'],list) or not 1<=len(spec['variants'])<=100 or len({v['id'] for v in spec['variants']})!=len(spec['variants']):
        raise ValueError('One to100 uniquely identified declared variants required')
    boundary=(allocation_project.parent/project['boundary']).resolve();catalogue=(lookup_project.parent/lookup['catalogue']).resolve()
    pins=dict(initial);pins.update({str(p):sha for p,sha in reference_files(allocation_project,project).items()})
    pins.update({str(p):sha for p,sha in reference_files(study,spec).items()})
    pins.update({str(boundary):project['boundary_sha256'],str(catalogue):lookup['catalogue_sha256']})
    from . import air_allocation,air_load,service_areas,terminal_throw
    for module in (air_allocation,air_load,service_areas,terminal_throw):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Layout study source hash mismatch')
    if output.exists() or any(output==Path(p) or output in Path(p).parents for p in pins):raise ValueError('New study output separate from all inputs required')
    boundary_data=json.loads(boundary.read_text(encoding='utf-8-sig'));catalogue_data=json.loads(catalogue.read_text(encoding='utf-8-sig'))
    variants=[evaluate_variant(boundary_data,project,catalogue_data,v,spec['panel_size_m'],spec['ratio_range']) for v in spec['variants']]
    result=dict(inputs=pins,basis=spec['basis'],panel_size_m=spec['panel_size_m'],diagnostic_ratio_range=spec['ratio_range'],variants=variants,
        coincidence_tolerance_m=COINCIDENCE_M,selected_variant=None,ADPI_verified=False,design_accepted=False,
        scope='Declared planar variants only. Cardinal rays to interpreted polygon boundaries or aligned opposing midpoints are geometric diagnostics,not authenticated physical characteristic lengths. Allocation cells are not jet boundaries. Numerical coincidence tolerance is not an installation tolerance. No CAD/model writes or final selection.')
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Layout study inputs changed during evaluation')
    output.mkdir(parents=True);(output/'study.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    page='<!doctype html><meta charset="utf-8"><title>Diffuser Layout Comparison</title><style>body{font:16px/1.5 Arial;margin:30px;color:#20343c}table{border-collapse:collapse}td,th{padding:10px;border:1px solid #ccd}</style><h1>Diffuser Layout Comparison</h1>'
    page+=''.join('<p>'+html.escape(result[k])+'</p>' for k in ('basis','scope'))
    page+='<table><tr>'+''.join('<th>'+h+'</th>' for h in ('Variant','Changed IDs','Panels outside','Panel overlaps','Length mismatches','Ratio issues','Geometric candidate'))+'</tr>'
    for v in variants:
        values=[v['id'],len(v['changes']),len(v['panel_outside_boundary']),len(v['panel_overlaps']),v['cell_ray_mismatches'],v['diagnostic_ratio_cases_outside_range'],v['geometric_candidate']]
        page+='<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in values)+'</tr>'
    (output/'index.html').write_text(page+'</table><p>All variants remain unselected;full engineering acceptance pending.</p>',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('allocation_project','lookup_project','study'):p.add_argument(name)
    p.add_argument('--out',required=True);a=p.parse_args()
    r=run(a.allocation_project,a.lookup_project,a.study,a.out)
    print(len(r['variants']),'declared layouts evaluated;engineering applicability and selection pending')
