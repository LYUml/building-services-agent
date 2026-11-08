"""Audit actual saved leader/label geometry without invoking the annotation planner."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .route_annotations import geometry, expand

TOL = 1e-8


def raw_space_markers(path):
    """Keep entity group 67 before ezdxf repairs it from layout ownership."""
    from io import StringIO
    from ezdxf.lldxf.tagger import ascii_tags_loader, binary_tags_loader
    from ezdxf.lldxf.tags import group_tags
    data=Path(path).read_bytes()
    # Only ASCII handles, section names and numeric flags are inspected. Latin-1
    # preserves all bytes without guessing legacy text encodings.
    tags=binary_tags_loader(data) if data.startswith(b'AutoCAD Binary DXF') else ascii_tags_loader(StringIO(data.decode('latin1').replace('\r\n','\n')))
    result={};section=None
    for group in group_tags(tags):
        kind=group[0].value
        if kind=='SECTION':section=next((t.value for t in group if t.code==2),None)
        elif kind=='ENDSEC':section=None
        elif section in ('ENTITIES','BLOCKS'):
            handles=[str(t.value).upper() for t in group if t.code==5]
            if len(handles)==1:
                result.setdefault(handles[0],[]).append([str(t.value).strip() for t in group if t.code==67])
    return result


def precise(points):
    if any(not math.isfinite(v) or math.ulp(v)>TOL for p in points for v in p):
        raise ProjectError('annotation coordinates cannot support the saved audit precision')


def enters(a,b,box):
    """Clip in parameter space, then measure physical overlap instead of a fixed t cutoff."""
    precise((a,b));low,high=0.,1.
    for i in (0,1):
        lo,hi=box[i]+TOL,box[i+2]-TOL;delta=b[i]-a[i]
        if not delta:
            if not lo<a[i]<hi:return False
        else:
            start,end=sorted(((lo-a[i])/delta,(hi-a[i])/delta))
            low,high=max(low,start),min(high,end)
    return high>low and math.dist(a,b)*(high-low)>TOL


def label_text(row):
    text = f"{row['name']} ID {row['inner_diameter_m']*1000:g}/OD {row['outside_diameter_m']*1000:g} mm; L {row['length_m']:.6f} m"
    if row['centreline_radius_m'] is not None:
        text += f"; R {row['centreline_radius_m']*1000:g} mm; 90 deg"
    return text


def distance(a, b, c, d):
    """Planar segment distance for crossings, collinear overlaps and clear gaps."""
    precise((a,b,c,d))
    def cross(u,v):return u[0]*v[1]-u[1]*v[0]
    r=[b[i]-a[i] for i in (0,1)];s=[d[i]-c[i] for i in (0,1)]
    den=cross(r,s);delta=[c[i]-a[i] for i in (0,1)]
    if abs(den)>1e-20:
        t,u=cross(delta,s)/den,cross(delta,r)/den
        if 0<=t<=1 and 0<=u<=1:return 0.
    def point(p,x,y):
        v=[y[i]-x[i] for i in (0,1)];length=sum(k*k for k in v)
        t=max(0.,min(1.,sum((p[i]-x[i])*v[i] for i in (0,1))/length)) if length else 0.
        return math.dist(p,[x[i]+t*v[i] for i in (0,1)])
    return min(point(a,c,d),point(b,c,d),point(c,a,b),point(d,a,b))


def audit_saved(dxf, rows, axes, height, report):
    """Rows must already be source-checked; planner Boolean claims are ignored."""
    import ezdxf
    expected={r['guid']:geometry(r,axes,height) for r in rows}
    if len(expected)!=len(rows) or not expected:raise ProjectError('unique complete source pieces required for saved annotation audit')
    plans=report.get('pieces') if isinstance(report,dict) else None
    if not isinstance(plans,list) or any(not isinstance(p,dict) or not isinstance(p.get('guid'),str) or p.get('guid') not in expected for p in plans) or len(plans)!=len(expected) or len({p['guid'] for p in plans})!=len(expected):
        raise ProjectError('saved annotation audit requires exact piece coverage')
    margin=height/2;column=max(p['bounds_m'][2] for p in expected.values())+4*height
    def vector(p):
        if not isinstance(p,(list,tuple)) or len(p)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in p):raise ProjectError('finite planar annotation coordinates required')
        return list(p)
    paths={};labels={}
    for plan in plans:
        guid=plan['guid'];source=expected[guid]
        points=plan.get('leader_points_m')
        if not isinstance(points,list) or len(points)<3:raise ProjectError('complete saved outward stub and routed tail required')
        points=[vector(p) for p in points];position=vector(plan.get('label_position_m'))
        if math.dist(points[0],source['anchor_m'])>TOL or math.dist(points[1],source['escape_m'])>TOL:
            raise ProjectError('saved annotation lost source OD anchor/outward escape')
        if abs(position[0]-column)>TOL or math.dist(points[-1],[position[0]-height,position[1]])>TOL:
            raise ProjectError('saved leader does not terminate at source label column')
        for index,(a,b) in enumerate(zip(points,points[1:])):
            if math.dist(a,b)<=TOL:raise ProjectError('nonzero saved leader segments required')
            for key,piece in expected.items():
                if index==0 and key==guid:continue  # Recomputed outward OD normal ray proves this one stub.
                if enters(a,b,expand(piece['bounds_m'],margin)):
                    raise ProjectError('saved leader enters conservative route obstacle')
        segments=list(zip(points,points[1:]))
        for a,b,c in zip(points,points[1:],points[2:]):
            u=[b[i]-a[i] for i in (0,1)];v=[c[i]-b[i] for i in (0,1)]
            if abs(u[0]*v[1]-u[1]*v[0])<=TOL*max(math.dist(a,b),math.dist(b,c)) and sum(x*y for x,y in zip(u,v))<0:
                raise ProjectError('saved leader doubles back on itself')
        for i,(a,b) in enumerate(segments):
            for c,d in segments[i+2:]:
                if distance(a,b,c,d)<TOL:raise ProjectError('saved leader crosses itself')
        paths[guid]=points;labels[guid]=position
    heights=sorted(p[1] for p in labels.values())
    if any(b-a<2.2*height-TOL for a,b in zip(heights,heights[1:])):raise ProjectError('saved linked labels overlap their required row spacing')
    minimum=None
    for i,(guid,points) in enumerate(paths.items()):
        for other in list(paths.values())[i+1:]:
            for a,b in zip(points,points[1:]):
                for c,d in zip(other,other[1:]):
                    gap=distance(a,b,c,d);minimum=gap if minimum is None else min(minimum,gap)
                    if gap<margin-TOL:raise ProjectError('saved leader pair crosses or violates graphic margin')
    raw_markers=raw_space_markers(dxf)
    doc=ezdxf.readfile(dxf)
    if doc.header.get('$INSUNITS')!=6:raise ProjectError('saved annotation drawing must use metres')
    def visible_flags(entity):
        records=raw_markers.get(entity.dxf.handle.upper(),[])
        if len(records)!=1 or records[0] not in ([],['0']):
            raise ProjectError('linked annotation raw paper-space marker must be absent or uniquely zero')
        if entity.dxf.invisible!=0 or entity.dxf.paperspace!=0:
            raise ProjectError('linked annotation must not be hidden or marked as paper space')
        if not doc.layers.has_entry(entity.dxf.layer):raise ProjectError('linked annotation layer definition required')
        layer=doc.layers.get(entity.dxf.layer)
        if layer.is_off() or layer.is_frozen() or layer.dxf.plot!=1:
            raise ProjectError('linked annotation layer must be on, thawed and enabled for plotting')
    def linked(e):
        tags=[(t.code,t.value) for t in e.get_xdata('BSA_IFC')] if e.has_xdata('BSA_IFC') else []
        if len(tags)!=1 or tags[0][0]!=1000 or tags[0][1] not in expected:raise ProjectError('saved annotation has missing/unknown IFC identity')
        return tags[0][1]
    def key(guid,a,b):
        ends=sorted((tuple(round(v,9) for v in a),tuple(round(v,9) for v in b)))
        return (guid,*ends)
    found=Counter();text={}
    source_rows={r['guid']:r for r in rows}
    for entity in doc.modelspace():
        if entity.dxf.layer=='BSA_LEADER':
            guid=linked(entity)
            visible_flags(entity)
            if entity.dxftype()!='LINE' or any(not math.isfinite(v) for v in (*entity.dxf.start,*entity.dxf.end)) or abs(entity.dxf.start.z)>TOL or abs(entity.dxf.end.z)>TOL:
                raise ProjectError('finite WCS XY saved leader LINE required')
            found[key(guid,list(entity.dxf.start)[:2],list(entity.dxf.end)[:2])]+=1
        elif entity.dxf.layer=='BSA_LABEL' and entity.has_xdata('BSA_IFC'):
            guid=linked(entity)
            visible_flags(entity)
            if guid in text or entity.dxftype()!='TEXT':raise ProjectError('one saved linked TEXT per source piece required')
            position=entity.dxf.insert
            if any(not math.isfinite(v) for v in (*position,entity.dxf.height,entity.dxf.rotation,entity.dxf.width,entity.dxf.oblique)) or abs(position.z)>TOL or math.dist(list(position)[:2],labels[guid])>TOL or abs(entity.dxf.height-height)>TOL or abs(entity.dxf.rotation)>TOL or abs(entity.dxf.width-1)>TOL or abs(entity.dxf.oblique)>TOL or entity.dxf.halign or entity.dxf.valign or not entity.dxf.extrusion.isclose((0,0,1),abs_tol=TOL):
                raise ProjectError('saved linked label placement/style differs from checked layout')
            if entity.dxf.text!=label_text(source_rows[guid]):raise ProjectError('saved label dimensions/text differ from source')
            text[guid]=True
    wanted=Counter(key(guid,a,b) for guid,points in paths.items() for a,b in zip(points,points[1:]))
    if found!=wanted or set(text)!=set(expected):raise ProjectError('actual saved annotation paths/label coverage differ from checked layout')
    return dict(scope='actual GUID-linked DXF leaders and labels; source OD stub/obstacle geometry, segment distances and row placement; no planner invocation',
                dxf_sha256=digest(Path(dxf)),piece_count=len(rows),leader_segment_count=sum(found.values()),graphic_margin_m=margin,coordinate_tolerance_m=TOL,
                minimum_leader_pair_gap_m=minimum,leader_body_checks_pass=True,leader_pair_checks_pass=True,
                saved_paths_match=True,saved_labels_match=True,calculated_checks_pass=True,design_accepted=False,
                linked_annotation_visibility_flags_pass=True,
                checked_visibility_flags=['entity invisible','raw and loaded entity paper-space marker','layer off','layer frozen','layer plot'],
                pending=['unlinked legends and font glyph extents','native pipe geometry/print/BIM viewer and complete engineering acceptance'])


def run(ifc,model,settings,dxf,layout,out):
    from .ifc_route_drawing import extract,validate_settings
    paths=[Path(p).resolve() for p in (ifc,model,settings,dxf,layout)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('annotation audit output must not contain sources')
    before={str(p):digest(p) for p in paths}
    config=validate_settings(json.loads(paths[2].read_text(encoding='utf-8-sig')))
    rows=extract(paths[0],json.loads(paths[1].read_text(encoding='utf-8-sig')),config)
    result=audit_saved(paths[3],rows,[{'X':0,'Y':1,'Z':2}[a] for a in config['projection_axes']],config['annotation_height_m'],json.loads(paths[4].read_text(encoding='utf-8-sig')))
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('annotation audit source changed')
    result.update(inputs=before,inputs_unchanged=True)
    out.mkdir(parents=True,exist_ok=False);(out/'annotation-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ifc',type=Path)
    for name in ('model','settings','dxf','layout','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=run(a.ifc,a.model,a.settings,a.dxf,a.layout,a.out)
    print(json.dumps({'calculated_checks_pass':result['calculated_checks_pass'],'design_accepted':False}))


if __name__=='__main__':main()
