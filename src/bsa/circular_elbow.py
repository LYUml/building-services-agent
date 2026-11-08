"""Source-declared 90-degree constant-bore circular elbow wall solids."""
import math
from .engine import ProjectError
from . import circular_geometry as circular

WALL='circular 90-degree elbow wall'
SCOPE='axis-aligned envelopes, straight circular walls and explicit 90-degree elbows'
AXES={'+X':[1,0,0],'-X':[-1,0,0],'+Y':[0,1,0],'-Y':[0,-1,0],'+Z':[0,0,1],'-Z':[0,0,-1]}
LOSS_BASIS='excess over centreline Darcy friction'


def specification(d):
    import numpy as np
    if d.get('ifc_class') not in ('IfcPipeFitting','IfcDuctFitting'):raise ProjectError('elbow requires explicit pipe/duct fitting class')
    props=d.get('properties',{});inner=props.get('InternalDiameter_m');outer=props.get('OutsideDiameter_m');radius=props.get('CenterlineRadius_m')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (inner,outer,radius)) or not 0<inner<outer or radius<=outer/2:raise ProjectError('elbow needs 0 < bore < outside diameter and centreline radius > outside radius')
    axes=d.get('bend_axes');centre=d.get('arc_center_m')
    if not isinstance(axes,list) or len(axes)!=2 or any(not isinstance(a,str) or a not in AXES for a in axes):raise ProjectError('two explicit signed cardinal elbow axes required')
    u,v=[np.asarray(AXES[a],dtype=float) for a in axes]
    if np.dot(u,v)!=0:raise ProjectError('elbow axes must be perpendicular')
    if not isinstance(centre,list) or len(centre)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in centre):raise ProjectError('explicit finite arc centre required')
    centre=np.asarray(centre);normal=np.cross(u,v);ro=outer/2
    lo=centre+np.minimum(0,u*(radius+ro))+np.minimum(0,v*(radius+ro))-abs(normal)*ro
    hi=centre+np.maximum(0,u*(radius+ro))+np.maximum(0,v*(radius+ro))+abs(normal)*ro
    if not np.allclose(d['origin_m'],lo,atol=1e-8,rtol=0) or not np.allclose(d['size_m'],hi-lo,atol=1e-8,rtol=0):raise ProjectError('elbow envelope differs from source radius/centre/axes')
    start=centre+radius*u;end=centre+radius*v
    ports=d.get('ports',[])
    if len(ports)!=2 or {p['direction'] for p in ports} not in ({'SOURCE','SINK'},{'SOURCEANDSINK'}):raise ProjectError('two directed or two bidirectional elbow ends required')
    normals={};seen=set()
    for p in ports:
        point=np.asarray(d['origin_m'])+p['offset_m']
        if np.allclose(point,start,atol=1e-8,rtol=0):key='start';out=-v
        elif np.allclose(point,end,atol=1e-8,rtol=0):key='end';out=-u
        else:raise ProjectError('elbow ports must occupy actual arc-end face centres')
        if key in seen:raise ProjectError('elbow ports must occupy distinct ends')
        seen.add(key);normals[p['id']]=out.tolist()
    length=math.pi*radius/2
    points=[(radius*u).tolist(),(radius*(u+v)/math.sqrt(2)).tolist(),(radius*v).tolist()]
    return dict(inner_m=inner,outer_m=outer,radius_m=radius,centre_m=centre.tolist(),u=u.tolist(),v=v.tolist(),normal=normal.tolist(),start_m=start.tolist(),end_m=end.tolist(),normals=normals,arc_points_local_m=points,length_m=length,volume_m3=math.pi*(outer**2-inner**2)*length/4)


def tessellate(spec):
    import numpy as np
    radius=spec['radius_m'];ro=spec['outer_m']/2
    circle_step=min(circular.ANGULAR_DEFLECTION,2*math.acos(1-min(circular.LINEAR_DEFLECTION_M/ro,1)))
    arc_step=min(circular.ANGULAR_DEFLECTION,2*math.acos(1-min(circular.LINEAR_DEFLECTION_M/(radius+ro),1)))
    if min(circle_step,arc_step)<=0:raise ProjectError('elbow dimensions exceed floating-point tessellation precision')
    around=max(16,4*math.ceil((2*math.pi/circle_step)/4));along=max(4,math.ceil((math.pi/2)/arc_step))
    if around*(along+1)>500000:raise ProjectError('elbow exceeds explicit tessellation size budget')
    u,v,n=[np.asarray(spec[k]) for k in ('u','v','normal')];vertices=[];faces=[]
    def index(shell,i,j):return shell*(along+1)*around+i*around+j%around
    for r in (ro,spec['inner_m']/2):
        for i in range(along+1):
            theta=math.pi*i/(2*along);direction=math.cos(theta)*u+math.sin(theta)*v
            for j in range(around):
                phi=2*math.pi*j/around
                vertices.append(((radius+r*math.cos(phi))*direction+r*math.sin(phi)*n).tolist())
    for shell in (0,1):
        for i in range(along):
            for j in range(around):
                a,b,c,d=index(shell,i,j),index(shell,i+1,j),index(shell,i+1,j+1),index(shell,i,j+1)
                triangles=[(a,b,c),(a,c,d)]
                faces.extend(triangles if shell==0 else [tuple(reversed(t)) for t in triangles])
    for i in (0,along):
        for j in range(around):
            a,b,c,d=index(1,i,j),index(0,i,j),index(0,i,j+1),index(1,i,j+1)
            triangles=[(a,b,c),(a,c,d)]
            faces.extend(triangles if i==0 else [tuple(reversed(t)) for t in triangles])
    return vertices,faces,dict(arc_intervals=along,circumference_intervals=around,linear_deflection_bound_m=max(ro*(1-math.cos(math.pi/around)),(radius+ro)*(1-math.cos(math.pi/(4*along)))))


def author(model,context,obj,d):
    import ifcopenshell.api as api
    import numpy as np
    spec=specification(d);obj.PredefinedType='BEND'
    vertices,faces,quality=tessellate(spec)
    rep=api.run('geometry.add_mesh_representation',model,context=context,vertices=[vertices],faces=[faces])
    rep.Items[0].Closed=True
    api.run('geometry.assign_representation',model,product=obj,representation=rep)
    points=model.create_entity('IfcCartesianPointList3D',CoordList=spec['arc_points_local_m'])
    segment=model.create_entity('IfcArcIndex',(1,2,3))
    curve=model.create_entity('IfcIndexedPolyCurve',Points=points,Segments=[segment],SelfIntersect=False)
    axis=model.create_entity('IfcShapeRepresentation',ContextOfItems=context,RepresentationIdentifier='Axis',RepresentationType='Curve3D',Items=[curve])
    api.run('geometry.assign_representation',model,product=obj,representation=axis)
    matrix=np.eye(4);matrix[:3,3]=spec['centre_m'];api.run('geometry.edit_object_placement',model,product=obj,matrix=matrix,is_si=True)


def verify(obj,d,shape):
    import numpy as np
    import ifcopenshell.util.element as element
    import ifcopenshell.util.placement as placement
    spec=specification(d)
    bodies=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body']
    axes=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Axis']
    if len(bodies)!=1 or bodies[0].RepresentationType!='Tessellation' or len(bodies[0].Items)!=1 or obj.PredefinedType!='BEND':raise ProjectError('saved elbow must be one explicit tessellated BEND wall')
    if len(axes)!=1 or axes[0].RepresentationType!='Curve3D' or len(axes[0].Items)!=1:raise ProjectError('saved elbow needs exact circular arc Axis reference')
    curve=axes[0].Items[0]
    if not curve.is_a('IfcIndexedPolyCurve') or not curve.Points.is_a('IfcCartesianPointList3D') or len(curve.Segments or [])!=1 or not curve.Segments[0].is_a('IfcArcIndex') or tuple(curve.Segments[0].wrappedValue)!=(1,2,3) or curve.SelfIntersect is not False:raise ProjectError('saved elbow lost exact circular arc reference')
    if not np.allclose(curve.Points.CoordList,spec['arc_points_local_m'],atol=1e-10,rtol=0):raise ProjectError('saved elbow arc points differ from source')
    expected_vertices,expected_faces,quality=tessellate(spec);body=bodies[0].Items[0]
    if not body.is_a('IfcPolygonalFaceSet') or body.Closed is not True or body.PnIndex is not None or not body.Coordinates.is_a('IfcCartesianPointList3D'):raise ProjectError('saved elbow lost explicit closed indexed wall mesh')
    coordinates=np.asarray(body.Coordinates.CoordList);indices=[list(f.CoordIndex) for f in body.Faces]
    if coordinates.shape!=np.asarray(expected_vertices).shape or not np.allclose(coordinates,expected_vertices,atol=1e-10,rtol=0) or indices!=(np.asarray(expected_faces)+1).tolist():raise ProjectError('saved elbow tessellation differs from source parameters/deflection')
    matrix=placement.get_local_placement(obj.ObjectPlacement);expected=np.eye(4);expected[:3,3]=spec['centre_m']
    if not np.allclose(matrix,expected,atol=1e-9,rtol=0):raise ProjectError('saved elbow world placement differs')
    props=element.get_psets(obj).get('BSA_DesignInputs',{})
    for key,target in (('InternalDiameter_m',spec['inner_m']),('OutsideDiameter_m',spec['outer_m']),('CenterlineRadius_m',spec['radius_m'])):
        actual=props.get(key)
        if type(actual) not in (int,float) or not math.isclose(actual,target,abs_tol=1e-10,rel_tol=1e-10):raise ProjectError('saved elbow metadata differs from analytic geometry')
    vertices=np.asarray(shape.geometry.verts).reshape(-1,3);faces=np.asarray(shape.geometry.faces).reshape(-1,3)
    volume,error,euler=circular.verify_closed_wall(vertices,faces,spec['volume_m3'])
    local=vertices-np.asarray(spec['centre_m']);a=local@np.asarray(spec['u']);b=local@np.asarray(spec['v']);z=local@np.asarray(spec['normal'])
    radial=np.sqrt((np.sqrt(a*a+b*b)-spec['radius_m'])**2+z*z);tol=circular.BOUNDS_TOLERANCE_M
    if np.min(a)<-tol or np.min(b)<-tol or np.min(radial)<spec['inner_m']/2-tol or np.max(radial)>spec['outer_m']/2+tol:raise ProjectError('native elbow mesh exceeds quarter-arc or annular-wall bounds')
    if not np.any(abs(radial-spec['inner_m']/2)<1e-7) or not np.any(abs(radial-spec['outer_m']/2)<1e-7):raise ProjectError('native elbow lacks inner/outer surfaces')
    return dict(body_representation='source-parametric tessellated annular wall; exact circular Axis reference',tessellation=quality,body_shape=WALL,analytic_wall_volume_m3=spec['volume_m3'],mesh_wall_volume_m3=volume,relative_volume_error=error,volume_relative_tolerance=circular.VOLUME_RELATIVE_TOLERANCE,centreline_arc_length_m=spec['length_m'],centreline_radius_m=spec['radius_m'],saved_inner_diameter_m=spec['inner_m'],saved_outside_diameter_m=spec['outer_m'],closed_mesh=True,euler_characteristic=euler,explicit_circular_arc=True,through_bore_pass=True)


def saved_arc_length(obj):
    """Independently derive a quarter-circle length from actual saved axis points."""
    import numpy as np
    import ifcopenshell.util.placement as placement
    axes=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Axis'] if obj.Representation else []
    if len(axes)!=1 or len(axes[0].Items)!=1:raise ProjectError('one saved fitting Axis required for route length')
    curve=axes[0].Items[0]
    if not curve.is_a('IfcIndexedPolyCurve') or not curve.Points.is_a('IfcCartesianPointList3D') or len(curve.Segments or [])!=1 or not curve.Segments[0].is_a('IfcArcIndex') or tuple(curve.Segments[0].wrappedValue)!=(1,2,3):raise ProjectError('one exact saved circular arc required')
    points=np.asarray(curve.Points.CoordList,dtype=float)
    if points.shape!=(3,3) or not np.isfinite(points).all():raise ProjectError('three finite fitting arc points required')
    a,b,c=points;u=b-a;v=c-a;w=np.cross(u,v);den=2*float(np.dot(w,w))
    if den<=1e-24:raise ProjectError('degenerate saved fitting arc')
    centre=a+(np.dot(u,u)*np.cross(v,w)+np.dot(v,v)*np.cross(w,u))/den
    radius=float(np.linalg.norm(a-centre));start=(a-centre)/radius;end=(c-centre)/radius;mid=(b-centre)/radius
    if not math.isclose(float(np.dot(start,end)),0,abs_tol=1e-8) or not np.allclose(mid,(start+end)/math.sqrt(2),atol=1e-8,rtol=0):raise ProjectError('saved route fitting must be the intended minor 90-degree arc')
    matrix=placement.get_local_placement(obj.ObjectPlacement)
    world=[(matrix@np.append(p,1))[:3].tolist() for p in (a,c)]
    return math.pi*radius/2,world,radius
