"""Conservative DXF text-box drafting checks; actual font/plot review stays separate."""
import math
import numpy as np
from .engine import ProjectError


def text_box(entity):
    from ezdxf import bbox
    box=bbox.extents([entity])
    if not box.has_data:raise ProjectError('finite measurable text box required')
    result=np.array([box.extmin.x,box.extmin.y,box.extmax.x,box.extmax.y])
    if not np.isfinite(result).all() or result[2]<=result[0] or result[3]<=result[1]:raise ProjectError('positive finite text box required')
    return result


def audit_label_associations(entities, anchors, max_distance, ambiguity_margin):
    """Unique nearest-anchor screen in caller drawing units; not leader verification."""
    if not anchors or any(type(v) not in (int,float) or not math.isfinite(v) or v <= 0
                          for v in (max_distance, ambiguity_margin)):
        raise ProjectError('nonempty anchors and positive finite distance limits required')
    for name, point in anchors.items():
        if not isinstance(name,str) or not name.strip() or len(point)!=2 or any(
                type(v) not in (int,float) or not math.isfinite(v) for v in point):
            raise ProjectError('named finite planar anchors required')
    seen=set(); results=[]
    for entity in entities:
        name=entity.dxf.text
        if name not in anchors or name in seen:
            raise ProjectError('unexpected or duplicate device label')
        seen.add(name); bounds=text_box(entity); center=(bounds[:2]+bounds[2:])/2
        distance=math.dist(center,anchors[name])
        competitors=[math.dist(center,p) for k,p in anchors.items() if k!=name]
        if distance>max_distance or any(d<=distance+ambiguity_margin for d in competitors):
            raise ProjectError('device label too distant or nearest association ambiguous')
        results.append(dict(label=name,distance=float(distance)))
    if seen!=set(anchors):raise ProjectError('missing device labels')
    return dict(associations=results,association_screen_pass=True,
                scope='Approximate text-box centre nearest-anchor screen only; source identity and visual association remain separate')


def place_outward(entity,midpoint,normal,height):
    """Place whole axis-aligned font box outside the dimension line, centred along it."""
    box=text_box(entity);centre=(box[:2]+box[2:])/2
    normal=np.asarray(normal,dtype=float);midpoint=np.asarray(midpoint,dtype=float)
    if normal.shape!=(2,) or midpoint.shape!=(2,) or not np.isfinite(normal).all() or not np.isfinite(midpoint).all() or not math.isclose(float(np.linalg.norm(normal)),1,abs_tol=1e-9):raise ProjectError('unit planar dimension normal required')
    support=float(np.dot(np.abs(normal),(box[2:]-box[:2])/2))
    delta=midpoint+normal*(support+2*height)-centre
    entity.dxf.insert=(entity.dxf.insert.x+delta[0],entity.dxf.insert.y+delta[1],0.)


def check_dimension_box(entity,midpoint,normal,height):
    box=text_box(entity);normal=np.asarray(normal);midpoint=np.asarray(midpoint)
    corners=np.array([[box[i],box[j]] for i in (0,2) for j in (1,3)])
    gap=float(np.min((corners-midpoint)@normal))
    tangent=np.array([-normal[1],normal[0]])
    along=abs(float(np.dot((box[:2]+box[2:])/2-midpoint,tangent)))
    if not .75*height<=gap<=3.25*height or along>height/4+1e-8:raise ProjectError('dimension text placement differs from source graphical region')


def audit_graphics(doc,height):
    from ezdxf import bbox
    from .route_drawing_qa import enters
    text=list(doc.modelspace().query('TEXT'));graphics=list(doc.modelspace().query('LINE ARC'))
    margin=height/5;boxes=[text_box(e)+[-margin,-margin,margin,margin] for e in text]
    def overlap(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-8 and min(a[3],b[3])-max(a[1],b[1])>1e-8
    for i,box in enumerate(boxes):
        if any(overlap(box,other) for other in boxes[i+1:]):raise ProjectError('saved text boxes overlap at declared graphic margin')
        for entity in graphics:
            if entity.dxftype()=='LINE':
                hit=enters(list(entity.dxf.start)[:2],list(entity.dxf.end)[:2],box)
            else:
                bounds=bbox.extents([entity]);hit=overlap(box,[bounds.extmin.x,bounds.extmin.y,bounds.extmax.x,bounds.extmax.y])
            if hit:raise ProjectError('saved text box intersects line or conservative arc bounds')
    return dict(text_count=len(text),graphic_count=len(graphics),graphic_margin_m=margin,text_graphics_checks_pass=True,
        scope='ezdxf approximate font AABBs, actual LINE clipping and conservative ARC bounds; not exact glyph collision or general layout optimisation')
