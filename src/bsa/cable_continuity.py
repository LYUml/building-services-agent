"""Source authoring and saved correspondence for one quarter with tangent straights."""
import math
import numpy as np
from .engine import ProjectError
from .quarter_cable import inspect as quarter, rigid


def author(model, builder, spec, envelope, extension, lead=0.):
    from . import quarter_cable
    if type(extension) not in (int, float) or not math.isfinite(extension) or extension <= 0:
        raise ProjectError('positive finite sourced tangent extension required')
    if type(lead) not in (int,float) or not math.isfinite(lead) or lead<0:
        raise ProjectError('nonnegative finite sourced lead extension required')
    _, frame, points = quarter_cable.source_geometry(spec, envelope)
    tangent = -frame[:3, 0]
    end = points[-1] + tangent * extension
    bend, arc = quarter_cable.author(model, builder, spec, envelope)
    profile = model.create_entity('IfcCircleProfileDef', ProfileType='AREA', Radius=float(envelope))
    straight = builder.extrude(profile, magnitude=float(extension), position=points[-1],
        position_z_axis=tangent, position_x_axis=frame[:3, 1])
    start=points[0]+frame[:3,2]*lead
    pieces=[]
    if lead:
        lead_solid=builder.extrude(profile,magnitude=float(lead),position=start,
            position_z_axis=-frame[:3,2],position_x_axis=frame[:3,1])
        bend=model.create_entity('IfcBooleanResult',Operator='UNION',FirstOperand=lead_solid,SecondOperand=bend)
        lead_curve=model.create_entity('IfcPolyline',Points=[model.create_entity('IfcCartesianPoint',Coordinates=p.tolist()) for p in (start,points[0])])
        pieces.append(model.create_entity('IfcCompositeCurveSegment',Transition='CONTSAMEGRADIENT',SameSense=True,ParentCurve=lead_curve))
    union = model.create_entity('IfcBooleanResult', Operator='UNION', FirstOperand=bend, SecondOperand=straight)
    line = model.create_entity('IfcPolyline', Points=[
        model.create_entity('IfcCartesianPoint', Coordinates=p.tolist()) for p in (points[-1], end)])
    curve = model.create_entity('IfcCompositeCurve', SelfIntersect=False, Segments=pieces+[
        model.create_entity('IfcCompositeCurveSegment', Transition='CONTSAMEGRADIENT', SameSense=True, ParentCurve=arc),
        model.create_entity('IfcCompositeCurveSegment', Transition='DISCONTINUOUS', SameSense=True, ParentCurve=line)])
    ports = quarter_cable.port_frames(spec, envelope)
    ports[0][:3,3]=start
    ports[-1][:3, 3] = end
    return union, curve, ports


def _straight(straight,line,object_frame,factor):
    import ifcopenshell.util.placement as placement
    if straight.is_a() != 'IfcExtrudedAreaSolid' or not straight.Position or not straight.Position.is_a('IfcAxis2Placement3D'):
        raise ProjectError('explicit straight extrusion required')
    profile = straight.SweptArea
    if profile.is_a() != 'IfcCircleProfileDef' or profile.ProfileType != 'AREA':
        raise ProjectError('solid circular straight profile required')
    if profile.Position and not np.allclose(placement.get_axis2placement(profile.Position), np.eye(3), atol=1e-10, rtol=0):
        raise ProjectError('unoffset straight profile required')
    radius = float(profile.Radius) * factor
    length = float(straight.Depth) * factor
    if not math.isfinite(radius + length) or radius <= 0 or length <= 0:
        raise ProjectError('positive finite straight radius/length required')
    frame = rigid(object_frame @ rigid(placement.get_axis2placement(straight.Position)))
    frame[:3, 3] *= factor
    direction = np.array(straight.ExtrudedDirection.DirectionRatios, dtype=float)
    if direction.shape != (3,) or not np.isfinite(direction).all() or not np.allclose(direction, [0, 0, 1], atol=1e-10, rtol=0):
        raise ProjectError('positive local-Z straight extrusion required')
    start = frame[:3, 3]
    tangent = frame[:3, 2]
    end = start + tangent * length
    if not line.is_a('IfcPolyline') or len(line.Points) != 2:
        raise ProjectError('two-point independent straight Axis required')
    coords = np.array([p.Coordinates for p in line.Points], dtype=float)
    if coords.shape != (2, 3) or not np.isfinite(coords).all():
        raise ProjectError('finite 3D straight Axis required')
    coords = np.array([(object_frame @ np.append(p, 1))[:3] * factor for p in coords])
    if not np.allclose(coords, [start, end], atol=1e-9, rtol=0):
        raise ProjectError('straight Body differs from independent Axis')
    extent = radius * np.sqrt(np.maximum(0., 1 - tangent**2))
    bounds = np.array([np.minimum(start, end) - extent, np.maximum(start, end) + extent])
    volume = math.pi * radius**2 * length
    return dict(length=length,radius=radius,points=np.array([start,end]),end_normals=np.array([-tangent,tangent]),
                expected=dict(volume=volume,centroid=(start+end)/2,bounds=bounds))


def inspect(solid,curve,object_frame,factor,angle_factor):
    if solid.is_a()!='IfcBooleanResult' or solid.Operator!='UNION':raise ProjectError('one quarter/straight UNION required')
    pending=[solid];leaves=[];visited=0
    while pending:
        item=pending.pop();visited+=1
        if visited>5:raise ProjectError('only one quarter with one or two tangent straights supported')
        if item.is_a()=='IfcBooleanResult':
            if item.Operator!='UNION':raise ProjectError('only UNION cable pieces supported')
            pending.extend([item.SecondOperand,item.FirstOperand])
        else:leaves.append(item)
    kinds=[item.is_a() for item in leaves]
    if kinds not in (['IfcRevolvedAreaSolid','IfcExtrudedAreaSolid'],['IfcExtrudedAreaSolid','IfcRevolvedAreaSolid','IfcExtrudedAreaSolid']):
        raise ProjectError('quarter-tail or lead-quarter-tail pieces required')
    if not curve.is_a('IfcCompositeCurve') or curve.SelfIntersect is not False or len(curve.Segments or [])!=len(leaves):raise ProjectError('matching independent composite Axis pieces required')
    segments=curve.Segments
    if any(segment.SameSense is not True or segment.Transition!=('DISCONTINUOUS' if i==len(leaves)-1 else 'CONTSAMEGRADIENT') for i,segment in enumerate(segments)):
        raise ProjectError('forward tangent open composite Axis required')
    pieces=[quarter(item,segment.ParentCurve,object_frame,factor,angle_factor) if item.is_a()=='IfcRevolvedAreaSolid' else _straight(item,segment.ParentCurve,object_frame,factor) for item,segment in zip(leaves,segments)]
    bend=next(piece for piece in pieces if 'bend_radius' in piece)
    if any(not math.isclose(piece['radius'],bend['radius'],abs_tol=1e-10,rel_tol=0) for piece in pieces):raise ProjectError('positive equal-radius tangent pieces required')
    for a,b in zip(pieces,pieces[1:]):
        if not np.allclose(a['points'][-1],b['points'][0],atol=1e-9,rtol=0) or not np.allclose(a['end_normals'][-1],-b['end_normals'][0],atol=1e-10,rtol=0):raise ProjectError('pieces must meet with equal forward tangents')
    volume=sum(piece['expected']['volume'] for piece in pieces)
    expected=dict(volume=volume,centroid=sum((piece['expected']['centroid']*piece['expected']['volume'] for piece in pieces),np.zeros(3))/volume,
        bounds=np.array([np.min([piece['expected']['bounds'][0] for piece in pieces],axis=0),np.max([piece['expected']['bounds'][1] for piece in pieces],axis=0)]))
    return dict(length=sum(piece['length'] for piece in pieces),radius=bend['radius'],bend_radius=bend['bend_radius'],
        points=np.array([pieces[0]['points'][0],pieces[-1]['points'][-1]]),expected=expected,
        end_normals=np.array([pieces[0]['end_normals'][0],pieces[-1]['end_normals'][-1]]),
        route_geometry='straight plus quarter plus straight' if len(pieces)==3 else 'quarter plus tangent straight')
