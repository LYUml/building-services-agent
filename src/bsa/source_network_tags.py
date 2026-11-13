"""Finite source-keyed annotation placement using existing graphic checks and MILP."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import ezdxf
from shapely import Polygon,LineString,Point,box,STRtree
from shapely.ops import nearest_points
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_array
from . import view_tags,route_annotations,elbow_radius_selection
from .cli import digest
from .workspace import allowed
from .engine import ProjectError


def shapes(doc):
    result={}
    for e in doc.modelspace().query('LWPOLYLINE'):
        if not e.has_xdata('BSA_IFC'):raise ValueError('Source contour model identity required')
        guid=e.get_xdata('BSA_IFC')[0].value
        result[guid]=result.get(guid,Polygon()).symmetric_difference(Polygon(list(e.get_points('xy'))))
    return result


def candidates(geometry,tags,reserved,window,height,per_side=8):
    if not math.isfinite(height) or height<=0:raise ValueError('Positive finite model text height required')
    result=[]
    for guid in sorted(geometry):
        shape=geometry[guid];x0,y0,x1,y1=shape.bounds;cx,cy=(x0+x1)/2,(y0+y1)/2
        text=tags[guid];width=len(text)*height*.8
        main=max(shape.geoms,key=lambda p:p.area) if shape.geom_type=='MultiPolygon' else shape
        coordinates=list(main.exterior.coords)
        exposed=[]
        for a,b in zip(coordinates,coordinates[1:]):
            anchor=Point((a[0]+b[0])/2,(a[1]+b[1])/2)
            if all(g==guid or p.distance(anchor)>1e-8 for g,p in geometry.items()):exposed.append(anchor)
        for side in range(4):
            choices=[]
            for distance in (1,2,3,5,8,12):
                for shift in (0,-1,1,-2,2):
                    d=distance*height;s=shift*width
                    point=([cx-width/2+s,y1+d] if side==0 else [cx-width/2+s,y0-d-1.3*height] if side==1 else [x1+d,cy-height/2+s] if side==2 else [x0-d-width,cy-height/2+s])
                    item=dict(point=point,text=text)
                    try:view_tags.audit_positions([item],[],reserved,window,height)
                    except ProjectError:continue
                    rectangle=view_tags.rectangle(point,text,height);target=box(*rectangle)
                    if any(target.intersects(p.buffer(height*.125)) for p in geometry.values()):continue
                    near=nearest_points(shape,target)[0]
                    anchors=sorted([near,*exposed],key=lambda p:p.distance(target))
                    for a in anchors[:12]:
                        b=nearest_points(a,target)[1];start=list(a.coords)[0];end=list(b.coords)[0];line=LineString([start,end])
                        if line.length<=height*.2 or line.intersection(shape).length>1e-8:continue
                        if any(g!=guid and (line.intersection(p).length>1e-8 or p.distance(a)<1e-8) for g,p in geometry.items()):continue
                        if not route_annotations.clear(start,end,reserved):continue
                        choices.append(dict(guid=guid,tag=text,point=point,anchor=list(start),end=list(end),rectangle=rectangle,cost=line.length));break
            choices.sort(key=lambda r:(r['cost'],r['point']))
            result.extend(choices[:per_side])
    return result


def conflict(a,b,height):
    if view_tags.overlap(route_annotations.expand(a['rectangle'],height*.125),route_annotations.expand(b['rectangle'],height*.125)):return True
    if route_annotations.crosses(a['anchor'],a['end'],route_annotations.expand(b['rectangle'],height*.125)) or route_annotations.crosses(b['anchor'],b['end'],route_annotations.expand(a['rectangle'],height*.125)):return True
    return LineString([a['anchor'],a['end']]).intersects(LineString([b['anchor'],b['end']]))


def audit_selection(geometry,tags,reserved,window,height,selected):
    """Replay coverage and geometry without trusting candidate/solver flags."""
    if selected is None or len(selected)!=len(tags):raise ValueError('Complete annotation coverage required')
    if {r['guid'] for r in selected}!=set(tags):raise ValueError('Exact annotation identity required')
    view_tags.audit_positions([dict(point=r['point'],text=r['tag']) for r in selected],[],reserved,window,height)
    for i,r in enumerate(selected):
        if r['tag']!=tags[r['guid']]:raise ValueError('Schedule tag mismatch')
        rectangle=view_tags.rectangle(r['point'],r['tag'],height)
        if list(rectangle)!=list(r['rectangle']):raise ValueError('Changed annotation rectangle')
        target=box(*rectangle);anchor=Point(r['anchor']);end=Point(r['end']);line=LineString([anchor,end])
        own=geometry[r['guid']]
        if own.boundary.distance(anchor)>1e-8 or target.boundary.distance(end)>1e-8:raise ValueError('Leader endpoint off boundary')
        if line.length<=height*.2 or not route_annotations.clear(r['anchor'],r['end'],reserved):raise ValueError('Invalid leader clearance')
        for guid,shape in geometry.items():
            if target.intersects(shape.buffer(height*.125)):raise ValueError('Tag obscures model')
            if line.intersection(shape).length>1e-8 or (guid!=r['guid'] and shape.distance(anchor)<1e-8):raise ValueError('Leader obscures model')
        if any(conflict(r,s,height) for s in selected[:i]):raise ValueError('Conflicting annotations')
    return dict(component_count=len(selected),graphic_checks_passed=True,ancestry_verified=False,design_accepted=False)


def audit_saved(source,saved,selected,height):
    """Preserve the base drawing and check every added saved entity."""
    from .cad_overlay import snapshot,equivalent
    from .ifc_native import identity
    before=ezdxf.readfile(source);after=ezdxf.readfile(saved)
    def plain(v):
        if isinstance(v,dict):return {k:plain(x) for k,x in v.items()}
        if isinstance(v,list):return [plain(x) for x in v]
        return v.item() if isinstance(v,np.generic) else v
    a,b=plain(snapshot(before)),plain(snapshot(after))
    if any(k not in b or not equivalent(v,b[k]) for k,v in a.items()):raise ValueError('Base drawing changed')
    ia,ib=identity(before),identity(after)
    if any(ib.get(k)!=v for k,v in ia.items()):raise ValueError('Base drawing identity changed')
    extra=[e for e in after.modelspace() if e.dxf.handle not in ia]
    if len(extra)!=2*len(selected):raise ValueError('Unexpected annotation entity count')
    wanted={(r['guid'],kind):r for r in selected for kind in ('TEXT','LINE')};seen=set()
    for e in extra:
        ids=ib[e.dxf.handle]
        if len(ids)!=1 or ids[0][0]!=1000:raise ValueError('Exact annotation identity required')
        key=(ids[0][1],e.dxftype())
        if key not in wanted or key in seen:raise ValueError('Unexpected or duplicate annotation')
        seen.add(key);r=wanted[key]
        if e.dxftype()=='TEXT':
            correct=e.dxf.layer=='BSA_COMPONENT_TAG' and e.dxf.text==r['tag'] and e.dxf.style=='BSA_REVIEW_NOTES' and e.dxf.rotation==0 and e.dxf.width==1 and e.dxf.oblique==0 and e.dxf.halign==e.dxf.valign==0 and math.isclose(e.dxf.height,height,abs_tol=1e-8) and e.dxf.insert.isclose((*r['point'],0),abs_tol=1e-8,rel_tol=0)
        else:correct=e.dxf.layer=='BSA_TAG_LEADER' and e.dxf.start.isclose((*r['anchor'],0),abs_tol=1e-8,rel_tol=0) and e.dxf.end.isclose((*r['end'],0),abs_tol=1e-8,rel_tol=0)
        if not correct or e.dxf.invisible:raise ValueError('Saved annotation differs from audited placement')
    return dict(base_entities_preserved=len(ia),added_tags=len(selected),added_leaders=len(selected),saved_dxf_checked=True)


def select(geometry,tags,reserved,window,height,per_side=8):
    versions,pins=elbow_radius_selection.runtime();rows=candidates(geometry,tags,reserved,window,height,per_side)
    groups={g:[i for i,r in enumerate(rows) if r['guid']==g] for g in geometry}
    missing=[g for g,indexes in groups.items() if not indexes]
    if missing:return dict(selected=None,missing_candidate_guids=missing,candidate_count=len(rows),versions=versions)
    envelopes=[box(min(r['rectangle'][0],r['anchor'][0]),min(r['rectangle'][1],r['anchor'][1]),max(r['rectangle'][2],r['anchor'][0]),max(r['rectangle'][3],r['anchor'][1])).buffer(height*.25).envelope for r in rows]
    tree=STRtree(envelopes);pairs=[]
    for i,e in enumerate(envelopes):
        for j in tree.query(e):
            j=int(j)
            if j>i and rows[i]['guid']!=rows[j]['guid'] and conflict(rows[i],rows[j],height):pairs.append((i,j))
    ri=[];ci=[];values=[];lower=[];upper=[]
    for indexes in groups.values():
        row=len(lower);lower.append(1.);upper.append(1.)
        for i in indexes:ri.append(row);ci.append(i);values.append(1.)
    for i,j in pairs:
        row=len(lower);lower.append(-np.inf);upper.append(1.)
        ri.extend([row,row]);ci.extend([i,j]);values.extend([1.,1.])
    matrix=coo_array((values,(ri,ci)),shape=(len(lower),len(rows))).tocsc()
    solved=milp(np.array([r['cost']+i*1e-7 for i,r in enumerate(rows)]),integrality=np.ones(len(rows)),bounds=Bounds(0,1),constraints=LinearConstraint(matrix,lower,upper),options={'time_limit':45.,'mip_rel_gap':0.0})
    selected=None
    if solved.x is not None:
        indexes={i for i,v in enumerate(solved.x) if v>.5}
        if all(len(indexes.intersection(v))==1 for v in groups.values()) and not any(i in indexes and j in indexes for i,j in pairs):
            selected=[rows[i] for i in sorted(indexes)]
            view_tags.audit_positions([dict(point=r['point'],text=r['tag']) for r in selected],[],reserved,window,height)
    return dict(selected=selected,candidate_count=len(rows),conflict_pairs=len(pairs),solver_status=int(solved.status),optimal=bool(solved.success),versions=versions,runtime_inputs=pins)


def study(delivery,schedule,out):
    delivery,schedule,out=map(lambda p:Path(p).resolve(),(delivery,schedule,out))
    if not all(allowed(p) for p in (delivery,schedule,out)) or out.exists() or any(out.is_relative_to(p) or p.is_relative_to(out) for p in (delivery,schedule)):raise ValueError('Fresh separate host-selected annotation study required')
    source=delivery/'layout/Supply Network Geometry.dxf';sheet_path=delivery/'layout/sheet.json';table=schedule/'Network Parameter Schedule.json'
    doc=ezdxf.readfile(source);data=json.loads(table.read_text());sheet=json.loads(sheet_path.read_text());geometry=shapes(doc);tags={r['guid']:r['tag'] for r in data['components']}
    if set(geometry)!=set(tags):raise ValueError('Exact schedule/drawing model identity required')
    height=sheet['scale_denominator']*.0025
    reserved=[view_tags.rectangle([e.dxf.insert.x,e.dxf.insert.y],e.dxf.text,e.dxf.height) for e in doc.modelspace().query('TEXT')]
    for e in doc.modelspace().query('LINE'):
        reserved.append(route_annotations.expand([min(e.dxf.start.x,e.dxf.end.x),min(e.dxf.start.y,e.dxf.end.y),max(e.dxf.start.x,e.dxf.end.x),max(e.dxf.start.y,e.dxf.end.y)],height*.15))
    result=select(geometry,tags,reserved,sheet['window_drawing_units'],height)
    if result['selected'] is not None:result['graphic_audit']=audit_selection(geometry,tags,reserved,sheet['window_drawing_units'],height,result['selected'])
    result.update(source_delivery=str(delivery),source_schedule=str(schedule),text_height_m=height,source_hashes={str(p):digest(p) for p in (source,sheet_path,table,Path(__file__))},ancestry_verified=False,design_accepted=False)
    out.mkdir(parents=True);(out/'placement.json').write_text(json.dumps(result,indent=2))
    if result['selected'] is not None:
        doc.layers.new('BSA_COMPONENT_TAG');doc.layers.new('BSA_TAG_LEADER')
        for r in result['selected']:
            text=doc.modelspace().add_text(r['tag'],dxfattribs={'height':height,'insert':r['point'],'style':'BSA_REVIEW_NOTES','layer':'BSA_COMPONENT_TAG'})
            leader=doc.modelspace().add_line(r['anchor'],r['end'],dxfattribs={'layer':'BSA_TAG_LEADER'})
            for entity in (text,leader):entity.set_xdata('BSA_IFC',[(1000,r['guid'])])
        doc.saveas(out/'Tagged Network Study.dxf')
        result['saved_audit']=audit_saved(source,out/'Tagged Network Study.dxf',result['selected'],height)
        (out/'placement.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('delivery');p.add_argument('schedule');p.add_argument('--out',required=True);a=p.parse_args();r=study(a.delivery,a.schedule,a.out);print(json.dumps(dict(selected=None if r['selected'] is None else len(r['selected']),candidate_count=r['candidate_count'],solver_status=r.get('solver_status'),missing_candidates=len(r.get('missing_candidate_guids',[])),ancestry_verified=False,design_accepted=False),indent=2));raise SystemExit(2)
