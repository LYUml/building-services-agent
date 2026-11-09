"""Independent saved cable DXF entity audit against already source-checked geometry."""
from collections import Counter
import math
from pathlib import Path
import numpy as np
from .cli import digest
from .engine import ProjectError


def inputs():
    from . import route_drawing_qa
    return {Path(__file__).resolve(),Path(route_drawing_qa.__file__).resolve()}


def audit_saved(path,cable,geometry,settings,obstacles=()):
    import ezdxf
    from .route_drawing_qa import raw_space_markers,precise
    path=Path(path);before=digest(path)
    doc=ezdxf.readfile(path);raw=raw_space_markers(path)
    if doc.header.get('$INSUNITS')!=6:raise ProjectError('cable audit requires saved metre units')
    p=np.array(geometry['points_m'],dtype=float);centre=np.array(geometry['centre_m'],dtype=float)
    if p.shape!=(4,2) or centre.shape!=(2,):raise ProjectError('checked quarter/straight geometry required')
    precise(p.tolist()+[centre.tolist()])
    radius=float(cable['bend_radius_m']);envelope=float(cable['envelope_radius_m']);height=settings['annotation_height_m']
    if not np.allclose(np.linalg.norm(p[:3]-centre,axis=1),radius,atol=1e-8,rtol=0):raise ProjectError('checked circular source points required')
    angle=lambda q:math.degrees(math.atan2(q[1]-centre[1],q[0]-centre[0]))%360
    start,middle,end=[angle(q) for q in p[:3]]
    if not math.isclose((end-start)%360,90,abs_tol=1e-7):start,end=end,start
    if not math.isclose((end-start)%360,90,abs_tol=1e-7) or not math.isclose((middle-start)%360,45,abs_tol=1e-7):raise ProjectError('checked exact quarter source required')
    length=float(np.linalg.norm(p[3]-p[2]));guid=cable['element_guid']
    if length<=0 or not math.isclose(length+radius*math.pi/2,cable['observed_length_m'],abs_tol=1e-8,rel_tol=0):raise ProjectError('checked total route length required')
    expected=Counter();actual=Counter()
    def coords(v):return tuple(round(float(x),8) for x in v)
    def line(layer,g,a,b):return ('LINE',layer,g,*sorted([coords(a),coords(b)]))
    def arc(layer,g,c,r,a,b):return ('ARC',layer,g,coords(c),round(float(r),8),round(a%360,7)%360,round(b%360,7)%360)
    def text(g,value,point):return ('TEXT','BSA_LABEL',g,value,coords(point))
    for r,layer in [(radius,'BSA_CABLE_AXIS'),(radius-envelope,'BSA_CABLE_OUTLINE'),(radius+envelope,'BSA_CABLE_OUTLINE')]:expected[arc(layer,guid,centre,r,start,end)]+=1
    expected[line('BSA_CABLE_AXIS',guid,p[2],p[3])]+=1
    tangent=(p[3]-p[2])/length;normal=np.array([-tangent[1],tangent[0]])
    for sign in (-1,1):expected[line('BSA_CABLE_OUTLINE',guid,p[2]+sign*envelope*normal,p[3]+sign*envelope*normal)]+=1
    offset=max(4*height,3*envelope);a,b=p[2]+normal*offset,p[3]+normal*offset
    for x,y in [(p[2],a+normal*height),(p[3],b+normal*height),(a,b),(centre,p[1])]:expected[line('BSA_DIMENSION',guid,x,y)]+=1
    expected[text(guid,f'Straight L={length:.6f} m',(a+b)/2+normal*2*height)]+=1
    notes=[(guid,f"{cable['id']} / IFC {guid}"),
        (guid,f"True total L={cable['observed_length_m']:.6f} m; envelope OD={2*envelope:.6f} m"),
        (guid,f'Quarter R={radius:.6f} m; angle=90 deg; arc L={radius*math.pi/2:.6f} m'),
        (guid,f"{'/'.join(settings['projection_axes'])} plane {geometry['plane_coordinate_m']:.6f} m; coordinates m"),
        (guid,'Cable and sourced boxes projected; depth intervals below; not an installation drawing' if obstacles else 'Selected cable geometry only; other elements omitted; not an installation drawing')]
    for obstacle in obstacles:
        x0,y0,x1,y1=obstacle['projected_bounds_m'];corners=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
        for x,y in zip(corners,corners[1:]+corners[:1]):expected[line('BSA_OBSTACLE',obstacle['guid'],x,y)]+=1
        low,high=obstacle['depth_interval_m']
        notes.append((obstacle['guid'],f"Box {obstacle['id']}: {obstacle['depth_axis']}=[{low:.6f},{high:.6f}] m; projection is not a clash test"))
    top=float(p[:,1].max())+5*height;left=float(p[:,0].min())
    for i,(g,note) in enumerate(notes):expected[text(g,note,[left,top+(len(notes)-i)*1.8*height])]+=1
    for entity in doc.modelspace():
        records=raw.get(entity.dxf.handle.upper(),[])
        if len(records)!=1 or records[0] not in ([],['0']) or entity.dxf.invisible or entity.dxf.paperspace:raise ProjectError('saved cable entities must be visible in model space')
        layer=doc.layers.get(entity.dxf.layer)
        if layer.is_off() or layer.is_frozen() or layer.dxf.plot!=1:raise ProjectError('saved cable layers must be visible and plot enabled')
        tags=[(t.code,t.value) for t in entity.get_xdata('BSA_IFC')] if entity.has_xdata('BSA_IFC') else []
        if len(tags)!=1 or tags[0][0]!=1000:raise ProjectError('exact saved IFC identity required')
        g=tags[0][1];kind=entity.dxftype()
        if kind=='LINE':
            precise([list(entity.dxf.start),list(entity.dxf.end)])
            if abs(entity.dxf.start.z)>1e-8 or abs(entity.dxf.end.z)>1e-8:raise ProjectError('planar saved cable LINE required')
            actual[line(entity.dxf.layer,g,list(entity.dxf.start)[:2],list(entity.dxf.end)[:2])]+=1
        elif kind=='ARC':
            precise([list(entity.dxf.center),[entity.dxf.radius,entity.dxf.start_angle,entity.dxf.end_angle]])
            if abs(entity.dxf.center.z)>1e-8 or not entity.dxf.extrusion.isclose((0,0,1),abs_tol=1e-8):raise ProjectError('WCS XY saved cable ARC required')
            actual[arc(entity.dxf.layer,g,list(entity.dxf.center)[:2],entity.dxf.radius,entity.dxf.start_angle,entity.dxf.end_angle)]+=1
        elif kind=='TEXT':
            precise([list(entity.dxf.insert),[entity.dxf.height,entity.dxf.rotation,entity.dxf.width,entity.dxf.oblique]])
            if abs(entity.dxf.insert.z)>1e-8 or abs(entity.dxf.height-height)>1e-8 or abs(entity.dxf.rotation)>1e-8 or abs(entity.dxf.width-1)>1e-8 or abs(entity.dxf.oblique)>1e-8 or entity.dxf.halign or entity.dxf.valign or not entity.dxf.extrusion.isclose((0,0,1),abs_tol=1e-8):raise ProjectError('checked saved text placement/style required')
            actual[text(g,entity.dxf.text,list(entity.dxf.insert)[:2])]+=1
        else:raise ProjectError('unsupported saved cable drawing entity')
    if expected!=actual:raise ProjectError('actual saved cable geometry, dimensions, notes or IFC coverage differ from checked source')
    if digest(path)!=before:raise ProjectError('saved cable DXF changed during audit')
    return dict(dxf_sha256=before,entity_count=sum(actual.values()),saved_geometry_text_identity_pass=True,visibility_flags_pass=True,design_accepted=False,
        scope='Actual DXF entities versus already source-checked cable/box geometry and prescribed dimension/notes; no writer invocation or success flags used; font glyphs, crowded layout, native print and installation acceptance separate')
