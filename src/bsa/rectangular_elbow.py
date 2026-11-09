"""Source-parametric sharp-corner rectangular hollow 90-degree duct bend."""
import math
from .engine import ProjectError
from . import circular_geometry as circular
from .circular_elbow import AXES,saved_arc_length

WALL='rectangular 90-degree elbow wall'
SCOPE='axis-aligned envelopes and rectangular straight and elbow walls'


def specification(d):
    import numpy as np
    if d.get('ifc_class')!='IfcDuctFitting':raise ProjectError('rectangular elbow requires IfcDuctFitting')
    p=d.get('properties',{});values=[p.get(k) for k in ('InternalWidth_m','InternalHeight_m','WallThickness_m','CenterlineRadius_m')]
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values):raise ProjectError('positive sourced rectangular dimensions, thickness and radius required')
    width,height,t,radius=values;outer_width=width+2*t;outer_height=height+2*t
    if radius<=outer_width/2:raise ProjectError('rectangular bend radius must exceed radial outside half-width')
    axes=d.get('bend_axes');centre=d.get('arc_center_m')
    if not isinstance(axes,list) or len(axes)!=2 or any(not isinstance(a,str) or a not in AXES for a in axes):raise ProjectError('two explicit signed cardinal bend axes required')
    u,v=[np.array(AXES[a],dtype=float) for a in axes]
    if np.dot(u,v)!=0:raise ProjectError('perpendicular rectangular bend axes required')
    if not isinstance(centre,list) or len(centre)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in centre):raise ProjectError('finite source bend centre required')
    centre=np.array(centre);normal=np.cross(u,v);extent=radius+outer_width/2
    lo=centre+np.minimum(0,u*extent)+np.minimum(0,v*extent)-abs(normal)*outer_height/2
    hi=centre+np.maximum(0,u*extent)+np.maximum(0,v*extent)+abs(normal)*outer_height/2
    if not np.allclose(d['origin_m'],lo,atol=1e-8,rtol=0) or not np.allclose(d['size_m'],hi-lo,atol=1e-8,rtol=0):raise ProjectError('rectangular elbow envelope differs from source section/radius/frame')
    start=centre+radius*u;end=centre+radius*v;ports=d.get('ports',[])
    if len(ports)!=2 or {p['direction'] for p in ports} not in ({'SOURCE','SINK'},{'SOURCEANDSINK'}):raise ProjectError('two directed or bidirectional rectangular bend ports required')
    normals={};seen=set()
    for port in ports:
        point=np.array(d['origin_m'])+port['offset_m']
        if np.allclose(point,start,atol=1e-8,rtol=0):key='start';n=-v
        elif np.allclose(point,end,atol=1e-8,rtol=0):key='end';n=-u
        else:raise ProjectError('rectangular bend ports must occupy arc-end centres')
        if key in seen:raise ProjectError('distinct rectangular bend ends required')
        seen.add(key);normals[port['id']]=n.tolist()
    matrix=np.eye(4);matrix[:3,:3]=np.column_stack((u,v,normal));matrix[:3,3]=centre
    area=outer_width*outer_height-width*height
    radial_second=(outer_height*outer_width**3-height*width**3)/12
    offset=2/math.pi*(radius+radial_second/(area*radius))
    centroid=centre+offset*(u+v)
    return dict(width=width,height=height,thickness=t,outer_width=outer_width,outer_height=outer_height,radius=radius,
        matrix=matrix,normals=normals,start=start,end=end,length=radius*math.pi/2,volume=area*radius*math.pi/2,centroid=centroid,bounds=np.array([lo,hi]))


def author(model,context,obj,d):
    import ifcopenshell.api as api
    s=specification(d);obj.PredefinedType='BEND'
    profile_position=model.create_entity('IfcAxis2Placement2D',Location=model.create_entity('IfcCartesianPoint',Coordinates=(float(s['radius']),0.)))
    profile=model.create_entity('IfcRectangleHollowProfileDef',ProfileType='AREA',Position=profile_position,XDim=float(s['outer_width']),YDim=float(s['outer_height']),WallThickness=float(s['thickness']))
    origin=model.create_entity('IfcCartesianPoint',Coordinates=(0.,0.,0.))
    position=model.create_entity('IfcAxis2Placement3D',Location=origin,Axis=model.create_entity('IfcDirection',DirectionRatios=(0.,-1.,0.)),RefDirection=model.create_entity('IfcDirection',DirectionRatios=(1.,0.,0.)))
    axis=model.create_entity('IfcAxis1Placement',Location=origin,Axis=model.create_entity('IfcDirection',DirectionRatios=(0.,1.,0.)))
    solid=model.create_entity('IfcRevolvedAreaSolid',SweptArea=profile,Position=position,Axis=axis,Angle=math.pi/2)
    rep=model.create_entity('IfcShapeRepresentation',ContextOfItems=context,RepresentationIdentifier='Body',RepresentationType='SweptSolid',Items=[solid]);api.run('geometry.assign_representation',model,product=obj,representation=rep)
    r=s['radius'];points=model.create_entity('IfcCartesianPointList3D',CoordList=[(r,0.,0.),(r/math.sqrt(2),r/math.sqrt(2),0.),(0.,r,0.)])
    curve=model.create_entity('IfcIndexedPolyCurve',Points=points,Segments=[model.create_entity('IfcArcIndex',(1,2,3))],SelfIntersect=False)
    rep=model.create_entity('IfcShapeRepresentation',ContextOfItems=context,RepresentationIdentifier='Axis',RepresentationType='Curve3D',Items=[curve]);api.run('geometry.assign_representation',model,product=obj,representation=rep)
    api.run('geometry.edit_object_placement',model,product=obj,matrix=s['matrix'],is_si=True)


def verify(obj,d,shape):
    import numpy as np
    import ifcopenshell.util.element as element
    import ifcopenshell.util.placement as placement
    from .cad_ifc import mesh_properties
    s=specification(d);bodies=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body']
    if len(bodies)!=1 or len(bodies[0].Items)!=1 or bodies[0].RepresentationType!='SweptSolid' or obj.PredefinedType!='BEND':raise ProjectError('one revolved rectangular BEND body required')
    solid=bodies[0].Items[0]
    if not solid.is_a('IfcRevolvedAreaSolid') or not solid.SweptArea.is_a('IfcRectangleHollowProfileDef'):raise ProjectError('explicit revolved hollow rectangular profile required')
    p=solid.SweptArea
    pairs=((p.XDim,s['outer_width']),(p.YDim,s['outer_height']),(p.WallThickness,s['thickness']),(solid.Angle,math.pi/2))
    if any(not math.isclose(a,b,abs_tol=1e-10,rel_tol=0) for a,b in pairs) or any(v not in (None,0.) for v in (p.InnerFilletRadius,p.OuterFilletRadius)):raise ProjectError('saved rectangular bend profile/angle differs')
    if not p.Position or not np.allclose(placement.get_axis2placement(p.Position),[[1,0,0,s['radius']],[0,1,0,0],[0,0,1,0],[0,0,0,1]],atol=1e-10,rtol=0):raise ProjectError('rectangular bend profile offset differs')
    expected=np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1]])
    if not np.allclose(placement.get_axis2placement(solid.Position),expected,atol=1e-10,rtol=0) or tuple(solid.Axis.Location.Coordinates)!=(0.,0.,0.) or tuple(solid.Axis.Axis.DirectionRatios)!=(0.,1.,0.):raise ProjectError('saved rectangular bend local revolution frame differs')
    if not np.allclose(placement.get_local_placement(obj.ObjectPlacement),s['matrix'],atol=1e-8,rtol=0):raise ProjectError('saved rectangular bend world placement differs')
    length,ends,radius=saved_arc_length(obj)
    if not math.isclose(length,s['length'],rel_tol=0,abs_tol=1e-9) or not math.isclose(radius,s['radius'],rel_tol=0,abs_tol=1e-9) or not np.allclose(ends,[s['start'],s['end']],atol=1e-8,rtol=0):raise ProjectError('rectangular bend Axis differs from source')
    props=element.get_psets(obj).get('BSA_DesignInputs',{})
    for key,value in (('InternalWidth_m',s['width']),('InternalHeight_m',s['height']),('WallThickness_m',s['thickness']),('CenterlineRadius_m',s['radius'])):
        if type(props.get(key)) not in (int,float) or not math.isclose(props[key],value,abs_tol=1e-10,rel_tol=0):raise ProjectError('rectangular bend metadata differs')
    v=np.array(shape.geometry.verts).reshape(-1,3);f=np.array(shape.geometry.faces).reshape(-1,3)
    volume,error,euler=circular.verify_closed_wall(v,f,s['volume']);mass=mesh_properties(v,f)
    if not np.allclose(mass['bounds'],s['bounds'],atol=circular.BOUNDS_TOLERANCE_M,rtol=0) or not np.allclose(mass['centroid'],s['centroid'],atol=circular.BOUNDS_TOLERANCE_M,rtol=0):raise ProjectError('native rectangular bend bounds/centroid differ from analytic geometry')
    return dict(body_shape=WALL,body_representation='IfcRevolvedAreaSolid hollow rectangle',saved_internal_width_m=s['width'],saved_internal_height_m=s['height'],saved_wall_thickness_m=s['thickness'],centreline_radius_m=radius,centreline_arc_length_m=length,
        analytic_wall_volume_m3=s['volume'],mesh_wall_volume_m3=volume,relative_volume_error=error,closed_mesh=True,one_connected_wall=True,euler_characteristic=euler,exact_arc_reference=True,analytic_centroid_m=s['centroid'].tolist(),native_centroid_m=mass['centroid'].tolist())
