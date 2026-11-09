"""Analytic correspondence for native circular 90-degree cable envelopes."""
import math
import numpy as np
from .engine import ProjectError
from .three_phase import fields


def rigid(frame):
    if frame.shape!=(4,4) or not np.isfinite(frame).all() or not np.allclose(frame[3],[0,0,0,1],atol=1e-10,rtol=0) or not np.allclose(frame[:3,:3].T@frame[:3,:3],np.eye(3),atol=1e-10,rtol=0) or not math.isclose(float(np.linalg.det(frame[:3,:3])),1,abs_tol=1e-10):raise ProjectError('rigid right-handed quarter-cable frame required')
    return frame


def source_geometry(spec,envelope):
    fields(spec,'radius_m centre_m rotation')
    radius=spec['radius_m']
    if type(radius) not in (int,float) or not math.isfinite(radius) or not 0<envelope<radius:raise ProjectError('quarter cable requires sourced bend radius larger than envelope radius')
    origin=np.array(spec['centre_m'],dtype=float);rotation=np.array(spec['rotation'],dtype=float)
    if origin.shape!=(3,) or rotation.shape!=(3,3):raise ProjectError('three-coordinate centre and 3x3 rotation required')
    frame=np.eye(4);frame[:3,:3]=rotation;frame[:3,3]=origin;rigid(frame)
    return float(radius),frame,points(frame,radius)


def points(frame,radius):
    local=[[radius,0.,0.],[radius/math.sqrt(2),0.,-radius/math.sqrt(2)],[0.,0.,-radius]]
    return np.array([(frame@np.append(p,1))[:3] for p in local])


def author(model,builder,spec,envelope):
    radius,frame,axis_points=source_geometry(spec,envelope)
    profile=model.create_entity('IfcCircleProfileDef',ProfileType='AREA',Radius=float(envelope),
        Position=builder.create_axis2_placement_2d((radius,0.)))
    axis=model.create_entity('IfcAxis1Placement',Location=model.create_entity('IfcCartesianPoint',Coordinates=(0.,0.,0.)),
        Axis=model.create_entity('IfcDirection',DirectionRatios=(0.,1.,0.)))
    solid=model.create_entity('IfcRevolvedAreaSolid',SweptArea=profile,Position=builder.create_axis2_placement_3d_from_matrix(frame),Axis=axis,Angle=math.pi/2)
    curve=model.create_entity('IfcIndexedPolyCurve',Points=model.create_entity('IfcCartesianPointList3D',CoordList=axis_points.tolist()),
        Segments=[model.create_entity('IfcArcIndex',(1,2,3))],SelfIntersect=False)
    return solid,curve


def port_frames(spec,envelope):
    _,frame,axis_points=source_geometry(spec,envelope)
    result=[]
    for point,normal in zip(axis_points[[0,-1]],(frame[:3,2],-frame[:3,0])):
        reference=np.array([1.,0.,0.]) if abs(normal[0])<.9 else np.array([0.,1.,0.])
        x=reference-normal*np.dot(reference,normal);x/=np.linalg.norm(x)
        matrix=np.eye(4);matrix[:3,:3]=np.column_stack((x,np.cross(normal,x),normal));matrix[:3,3]=point
        result.append(matrix)
    return result


def properties(frame,radius,envelope):
    """Exact quarter-torus bounds/centroid; no sampled endpoint-chord bounds."""
    p=frame[:3,0];q=-frame[:3,2];n=frame[:3,1];centre=frame[:3,3]
    low=[];high=[]
    for i in range(3):
        angles=[0.,math.pi/2]
        theta=math.atan2(q[i],p[i])
        angles.extend(t for t in (theta,theta+math.pi,theta-math.pi) if 0<t<math.pi/2)
        values=[p[i]*math.cos(t)+q[i]*math.sin(t) for t in angles]
        a,b=min(values),max(values)
        low.append(centre[i]+radius*a-envelope*math.sqrt(a*a+n[i]*n[i]))
        high.append(centre[i]+radius*b+envelope*math.sqrt(b*b+n[i]*n[i]))
    centroid=centre+(radius+envelope**2/(4*radius))*2/math.pi*(p+q)
    return dict(bounds=np.array([low,high]),centroid=centroid,volume=math.pi*envelope**2*radius*math.pi/2)


def inspect(solid,curve,object_frame,factor,angle_factor):
    import ifcopenshell.util.placement as placement
    if solid.is_a()!='IfcRevolvedAreaSolid' or not math.isclose(float(solid.Angle)*angle_factor,math.pi/2,rel_tol=0,abs_tol=1e-10):raise ProjectError('only exact 90-degree circular revolution supported')
    profile=solid.SweptArea
    if profile.is_a()!='IfcCircleProfileDef' or profile.ProfileType!='AREA' or not profile.Position:raise ProjectError('placed solid circular revolution profile required')
    profile_point=np.array(profile.Position.Location.Coordinates,dtype=float)
    envelope=float(profile.Radius)
    if profile_point.shape!=(2,) or not np.isfinite(profile_point).all() or abs(profile_point[1])>1e-10 or not math.isfinite(envelope) or not 0<envelope<profile_point[0]:raise ProjectError('positive offset circular profile and non-self-intersecting bend required')
    radius=float(profile_point[0]);axis=solid.Axis
    location=np.array(axis.Location.Coordinates,dtype=float)
    direction=np.array(axis.Axis.DirectionRatios,dtype=float) if axis.Axis else np.array([0.,0.,1.])
    if location.shape!=(3,) or not np.allclose(location,0,atol=1e-10,rtol=0) or direction.shape!=(3,) or not np.isfinite(direction).all() or np.linalg.norm(direction)<=0 or not np.allclose(direction/np.linalg.norm(direction),[0.,1.,0.],atol=1e-10,rtol=0):raise ProjectError('canonical in-plane positive-Y revolution axis required')
    if not solid.Position or not solid.Position.is_a('IfcAxis2Placement3D'):raise ProjectError('explicit revolution placement required')
    frame=rigid(placement.get_axis2placement(solid.Position))
    if not curve.is_a('IfcIndexedPolyCurve') or not curve.Points.is_a('IfcCartesianPointList3D') or len(curve.Segments or [])!=1 or not curve.Segments[0].is_a('IfcArcIndex') or tuple(curve.Segments[0].wrappedValue)!=(1,2,3) or curve.SelfIntersect is not False:raise ProjectError('explicit three-point circular ArcIndex required; chord fallback forbidden')
    actual=np.array(curve.Points.CoordList,dtype=float);expected=points(frame,radius)
    if actual.shape!=(3,3) or not np.isfinite(actual).all() or not (np.allclose(actual,expected,atol=1e-9,rtol=0) or np.allclose(actual,expected[::-1],atol=1e-9,rtol=0)):raise ProjectError('revolved Body differs from independent exact circular Axis')
    world=rigid(object_frame@frame);world[:3,3]*=factor
    observed_points=np.array([(object_frame@np.append(p,1))[:3]*factor for p in actual])
    normals=np.array([world[:3,2],-world[:3,0]])
    if np.allclose(actual,expected[::-1],atol=1e-9,rtol=0):normals=normals[::-1]
    return dict(points=observed_points,radius=envelope*factor,bend_radius=radius*factor,length=radius*factor*math.pi/2,
                end_normals=normals,expected=properties(world,radius*factor,envelope*factor))
