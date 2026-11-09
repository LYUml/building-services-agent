"""Read saved rectangular-sheet entities against independently source-checked model facts."""
from collections import Counter
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError


def audit(path,rows,axes,height):
    import ezdxf
    from .route_drawing_qa import raw_space_markers,precise
    from .cad_text_layout import audit_graphics
    path=Path(path);before=digest(path);doc=ezdxf.readfile(path);raw=raw_space_markers(path)
    if doc.header.get('$INSUNITS')!=6:raise ProjectError('saved rectangular sheet must use metres')
    indices={'XY':(0,1),'XZ':(0,2),'YZ':(1,2)}[axes]
    expected=Counter();actual=Counter()
    def point(p):return tuple(round(float(x),8) for x in p)
    def line(layer,g,a,b):return ('LINE',layer,g,*sorted((point(a),point(b))))
    def arc(layer,g,c,r,a,b):return ('ARC',layer,g,point(c),round(float(r),8),round(a%360,7)%360,round(b%360,7)%360)
    def text(g,value,p):return ('TEXT','BSA_DUCT_TEXT',g,value,point(p))
    for index,row in enumerate(rows):
        g=row['guid'];lo,hi=row['bounds_m'];x,y=indices
        corners=[(lo[x],lo[y]),(hi[x],lo[y]),(hi[x],hi[y]),(lo[x],hi[y])]
        if row['ifc_class']=='IfcDuctSegment':
            a,b=row['axis_start_m'],row['axis_end_m']
            expected[line('BSA_PIPE_AXIS',g,[a[x],a[y]],[b[x],b[y]])]+=1
            label=f"{row['name']} {row['internal_width_m']*1000:g}x{row['internal_height_m']*1000:g} mm INSIDE; L {row['length_m']:g} m"
            layer='BSA_DUCT_OUTLINE'
        elif row['ifc_class']=='IfcDuctFitting':
            c=[row['arc_centre_m'][x],row['arc_centre_m'][y]]
            points=[[p[x],p[y]] for p in row['arc_points_m']];radius=row['centreline_radius_m']
            angles=[math.degrees(math.atan2(p[1]-c[1],p[0]-c[0]))%360 for p in points]
            start,middle,end=angles
            if not math.isclose((end-start)%360,90,abs_tol=1e-7):start,end=end,start
            if not math.isclose((end-start)%360,90,abs_tol=1e-7) or not math.isclose((middle-start)%360,45,abs_tol=1e-7) or any(not math.isclose(math.dist(p,c),radius,rel_tol=0,abs_tol=1e-8) for p in points):raise ProjectError('checked circular bend projection required')
            half=row['internal_width_m']/2+row['wall_thickness_m']
            for r,layer in ((radius,'BSA_PIPE_AXIS'),(radius-half,'BSA_DUCT_OUTLINE'),(radius+half,'BSA_DUCT_OUTLINE')):expected[arc(layer,g,c,r,start,end)]+=1
            for p in (points[0],points[2]):
                direction=[(p[i]-c[i])/radius for i in (0,1)]
                expected[line('BSA_DUCT_OUTLINE',g,[c[i]+(radius-half)*direction[i] for i in (0,1)],[c[i]+(radius+half)*direction[i] for i in (0,1)])]+=1
            label=f"{row['name']} {row['internal_width_m']*1000:g}x{row['internal_height_m']*1000:g} mm INSIDE; R {radius:g} m; ARC L {row['length_m']:.6f} m"
            layer=None
        elif row['ifc_class']=='IfcFan':label=row['name']+' ENVELOPE ONLY';layer='BSA_CONTEXT_OUTLINE'
        else:raise ProjectError('unsupported checked rectangular sheet class')
        if layer is not None:
            for a,b in zip(corners,corners[1:]+corners[:1]):expected[line(layer,g,a,b)]+=1
        expected[text(g,label,(.5,.5-index*height*1.8))]+=1
    for entity in doc.modelspace():
        flags=raw.get(entity.dxf.handle.upper(),[])
        if len(flags)!=1 or flags[0] not in ([],['0']) or entity.dxf.invisible or entity.dxf.paperspace:raise ProjectError('saved rectangular entities must be visible in model space')
        layer=doc.layers.get(entity.dxf.layer)
        if layer.is_off() or layer.is_frozen() or layer.dxf.plot!=1:raise ProjectError('saved rectangular layers must plot visibly')
        tags=[(t.code,t.value) for t in entity.get_xdata('BSA_IFC')] if entity.has_xdata('BSA_IFC') else []
        if len(tags)!=1 or tags[0][0]!=1000:raise ProjectError('exact saved rectangular IFC identity required')
        g=tags[0][1]
        if entity.dxftype()=='LINE':
            a,b=list(entity.dxf.start),list(entity.dxf.end);precise([a,b])
            if abs(a[2])>1e-8 or abs(b[2])>1e-8:raise ProjectError('planar saved rectangular LINE required')
            actual[line(entity.dxf.layer,g,a[:2],b[:2])]+=1
        elif entity.dxftype()=='ARC':
            d=entity.dxf;precise([list(d.center),[d.radius,d.start_angle,d.end_angle]])
            if abs(d.center.z)>1e-8 or d.radius<=0 or not d.extrusion.isclose((0,0,1),abs_tol=1e-8):raise ProjectError('planar saved rectangular ARC required')
            actual[arc(d.layer,g,list(d.center)[:2],d.radius,d.start_angle,d.end_angle)]+=1
        elif entity.dxftype()=='TEXT':
            d=entity.dxf;precise([list(d.insert),[d.height,d.rotation,d.width,d.oblique]])
            if abs(d.insert.z)>1e-8 or abs(d.height-height)>1e-8 or abs(d.rotation)>1e-8 or abs(d.width-1)>1e-8 or abs(d.oblique)>1e-8 or d.halign or d.valign or not d.extrusion.isclose((0,0,1),abs_tol=1e-8):raise ProjectError('source-relative rectangular text style required')
            actual[text(g,d.text,list(d.insert)[:2])]+=1
        else:raise ProjectError('unsupported saved rectangular entity')
    if actual!=expected:raise ProjectError('saved rectangular geometry, notes or IFC coverage differ from checked source')
    graphics=audit_graphics(doc,height)
    if digest(path)!=before:raise ProjectError('rectangular DXF changed during independent audit')
    return dict(dxf_sha256=before,entity_count=sum(actual.values()),saved_geometry_notes_identity_pass=True,visibility_flags_pass=True,text_graphics=graphics,
        design_accepted=False,scope='Actual saved entities versus already source-checked model facts, not writer flags; approximate text boxes, native print, source authentication and full installation acceptance separate')
