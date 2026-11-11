"""Compact source-keyed view tags;graphic avoidance is not service clearance."""
import math
from .engine import ProjectError
from .route_annotations import expand


def rectangle(point,text,height):
    return [point[0],point[1]-.3*height,point[0]+len(text)*height*.8,point[1]+1.3*height]


def overlap(a,b):
    return max(a[0],b[0])<min(a[2],b[2])-1e-10 and max(a[1],b[1])<min(a[3],b[3])-1e-10


def context(rows,axes,height,radius,window,texts):
    projected=[];bounds=[]
    for row in rows:
        a,b=[[p[i] for i in axes] for p in (row['start_world_m'],row['end_world_m'])];middle=[(a[i]+b[i])/2 for i in (0,1)]
        extent=radius if math.dist(a,b)<1e-9 else row['outside_diameter_m']/2
        bounds.append(expand([min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])],extent+height*.25))
        projected.append((row,a,b,middle))
    x=max(pt[0] for _,a,b,_ in projected for pt in (a,b))+4*height
    ordered=sorted(projected,key=lambda r:(-r[3][1],r[0]['guid']))
    reserved=[rectangle([x,window[3]-2-i*3*height],texts[r['guid']],height) for i,(r,*_) in enumerate(ordered)]
    reserved.append([window[0],window[3]-7*height,window[2],window[3]])
    return ordered,bounds,reserved


def audit_positions(items,bounds,reserved,window,height):
    boxes=[]
    for item in items:
        box=rectangle(item['point'],item['text'],height)
        if any(not math.isfinite(v) for v in box) or box[0]<window[0] or box[1]<window[1] or box[2]>window[2] or box[3]>window[3]:raise ProjectError('View tag outside declared window')
        if any(overlap(box,b) for b in bounds+reserved+boxes):raise ProjectError('View tag intersects graphic or annotation bounds')
        boxes.append(expand(box,height*.25))
    return True


def layout(rows,axes,height,radius,window,texts,tags):
    ordered,bounds,reserved=context(rows,axes,height,radius,window,texts)
    result={};occupied=[]
    for row,a,b,middle in ordered:
        guid=row['guid'];text=tags[guid];width=len(text)*height*.8;found=None
        for multiplier in (2,3,4,6,8):
            distance=multiplier*height
            candidates=[[middle[0]-width/2,middle[1]+distance],[middle[0]-width/2,middle[1]-distance-height],
                        [middle[0]+distance,middle[1]-height/2],[middle[0]-width-distance,middle[1]-height/2]]
            for point in candidates:
                item=dict(point=point,text=text)
                try:audit_positions([item],bounds,reserved+occupied,window,height)
                except ProjectError:continue
                found=item;break
            if found:break
        if found is None:raise ProjectError('No proven view-tag position within bounded graphic search')
        result[guid]=found;occupied.append(expand(rectangle(found['point'],text,height),height*.25))
    audit_positions(list(result.values()),bounds,reserved,window,height)
    return result
