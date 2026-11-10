"""Nominal-width straight duct footprints against explicitly bound planar obstacles."""
import json
import math
from pathlib import Path

import ezdxf
from shapely.geometry import LineString, Polygon, mapping
from shapely import union_all

from .cad_intake import METRES_PER_UNIT
from .cli import digest


def inspect(doc, schedule, binding, specification):
    scale=METRES_PER_UNIT.get(doc.units)
    if scale is None:raise ValueError('Known drawing units required')
    if set(specification)!={'drawing_sha256','schedule_sha256','binding_sha256','clearance_m','basis','obstacles'}:
        raise ValueError('Exact source pins, clearance, basis and obstacle inventory required')
    clearance=specification['clearance_m']
    if type(clearance) not in (int,float) or not math.isfinite(clearance) or clearance<0:
        raise ValueError('Explicit nonnegative finite planar target required')
    if not isinstance(specification['basis'],str) or not specification['basis'].strip():raise ValueError('Scope/target basis required')
    if not isinstance(specification['obstacles'],list) or not specification['obstacles']:raise ValueError('Nonempty explicit obstacle inventory required')
    if schedule.get('status')!='pass':raise ValueError('Passing nominal section schedule required')
    rows=schedule['sections'];ids=[r['id'] for r in rows]
    if not rows or any(r.get('failures') or not r.get('calculation') for r in rows):raise ValueError('Computed selected sections without failures required')
    if len(set(ids))!=len(ids) or set(ids)!=set(binding['sections']):raise ValueError('Exact section identity coverage required')
    obstacles=[];seen=set();used=set()
    def point(p):
        if len(p)!=3 or any(not math.isfinite(v) for v in p) or abs(p[2]*scale)>1e-8:raise ValueError('Planar finite source geometry required')
        return (p[0]*scale,p[1]*scale)
    for item in specification['obstacles']:
        if set(item)!={'id','polygon_m','source_handles','source'}:raise ValueError('Exact obstacle identity/polygon/handles/source required')
        if not isinstance(item['id'],str) or not item['id'].strip() or item['id'] in seen:raise ValueError('Unique obstacle identities required')
        seen.add(item['id'])
        if not isinstance(item['source'],str) or not item['source'].strip():raise ValueError('Obstacle interpretation source required')
        coordinates=item['polygon_m']
        if not isinstance(coordinates,list) or any(len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in coordinates):raise ValueError('Finite metre XY polygon required')
        polygon=Polygon(coordinates)
        if polygon.is_empty or not polygon.is_valid or polygon.area<=0:raise ValueError('Valid positive obstacle polygon required')
        handles=item['source_handles']
        if not isinstance(handles,list) or not handles or any(not isinstance(h,str) or not h for h in handles) or len(set(handles))!=len(handles):raise ValueError('Unique nonempty obstacle source handles required')
        boundaries=[]
        for handle in handles:
            if handle in used:raise ValueError('Obstacle handles reused')
            used.add(handle);entity=doc.entitydb.get(handle)
            if entity is None or entity not in doc.modelspace():raise ValueError('Obstacle source entity missing')
            if entity.dxftype()=='LINE':boundaries.append(LineString([point(entity.dxf.start),point(entity.dxf.end)]))
            elif entity.dxftype()=='LWPOLYLINE' and entity.closed and not entity.has_arc and tuple(entity.dxf.extrusion)==(0,0,1):
                vertices=[point((x,y,entity.dxf.elevation)) for x,y,*_ in entity.get_points()]
                boundaries.append(LineString(vertices+[vertices[0]]))
            else:raise ValueError('Only straight closed planar obstacle outlines supported')
        actual=union_all(boundaries)
        if actual.hausdorff_distance(polygon.boundary)>1e-8 or abs(actual.length-polygon.length)>1e-8:
            raise ValueError('Obstacle polygon differs from saved drawing outlines')
        obstacles.append((item,polygon))
    sections=[];checks=[]
    for row in rows:
        name=row['id'];entry=binding['sections'][name]
        entity=doc.entitydb.get(entry['line_handle'])
        if entity is None or entity.dxftype()!='LINE' or entity not in doc.modelspace():raise ValueError('Saved section LINE required')
        start,end=point(entity.dxf.start),point(entity.dxf.end)
        if any(math.dist(actual,expected[:2])>1e-8 for actual,expected in [(start,entry['from_m']),(end,entry['to_m'])]):raise ValueError('Saved section endpoint differs from binding')
        width=row['inputs']['width_m']
        if type(width) not in (int,float) or not math.isfinite(width) or width<=0:raise ValueError('Positive nominal width required')
        if math.dist(start,end)<=0:raise ValueError('Nonzero straight section required')
        footprint=LineString([start,end]).buffer(width/2,cap_style='flat')
        sections.append(dict(id=name,nominal_width_m=width,geometry=mapping(footprint)))
        for item,polygon in obstacles:
            area=footprint.intersection(polygon).area;distance=footprint.distance(polygon)
            status=('projected_overlap' if area>1e-10 else 'touching' if distance<=1e-8 else
                    'below_planar_target' if distance<clearance else 'clear_in_tested_projection')
            checks.append(dict(section=name,obstacle=item['id'],overlap_area_m2=area,distance_m=distance,status=status))
    return dict(sections=sections,checks=checks,obstacle_count=len(obstacles),clearance_m=clearance,basis=specification['basis'],
                planar_target_met=all(r['status']=='clear_in_tested_projection' for r in checks),
                status='review_required',design_accepted=False,
                scope='Nominal-width flat-ended straight footprints only; wall/insulation, fittings, heights, obstacle completeness and physical/code clearance not established')


def run(drawing,schedule,binding,specification,output):
    paths=[Path(p).resolve() for p in (drawing,schedule,binding,specification)]
    output=Path(output).resolve();pins={str(p):digest(p) for p in paths}
    if output.exists() or any(output==p or output in p.parents for p in paths):raise ValueError('New output outside sources required')
    data=[json.loads(p.read_text(encoding='utf-8')) for p in paths[1:]]
    for key,path in zip(('drawing_sha256','schedule_sha256','binding_sha256'),paths):
        if data[2].get(key)!=pins[str(path)]:raise ValueError('Plan clearance source pin mismatch')
    result=inspect(ezdxf.readfile(paths[0]),*data)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Clearance source changed')
    result.update(inputs=pins,generator_sha256=digest(Path(__file__)))
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
