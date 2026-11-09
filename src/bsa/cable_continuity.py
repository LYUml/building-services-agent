"""Read-only correspondence for a quarter followed by one tangent extrusion.

Not registered as an electrical route reader until ports and workflow gates exist.
"""
import math
import numpy as np
from .engine import ProjectError
from .quarter_cable import inspect as quarter, rigid


def inspect(solid, curve, object_frame, factor, angle_factor):
    import ifcopenshell.util.placement as placement
    if solid.is_a() != 'IfcBooleanResult' or solid.Operator != 'UNION':
        raise ProjectError('one quarter/straight UNION required')
    if not curve.is_a('IfcCompositeCurve') or curve.SelfIntersect is not False or len(curve.Segments) != 2:
        raise ProjectError('two-piece independent composite Axis required')
    first, last = curve.Segments
    if first.SameSense is not True or last.SameSense is not True or first.Transition != 'CONTSAMEGRADIENT' or last.Transition != 'DISCONTINUOUS':
        raise ProjectError('forward tangent open composite Axis required')
    bend = quarter(solid.FirstOperand, first.ParentCurve, object_frame, factor, angle_factor)
    straight = solid.SecondOperand
    if straight.is_a() != 'IfcExtrudedAreaSolid' or not straight.Position:
        raise ProjectError('explicit straight extrusion required')
    profile = straight.SweptArea
    if profile.is_a() != 'IfcCircleProfileDef' or profile.ProfileType != 'AREA':
        raise ProjectError('solid circular straight profile required')
    if profile.Position and not np.allclose(placement.get_axis2placement(profile.Position), np.eye(3), atol=1e-10, rtol=0):
        raise ProjectError('unoffset straight profile required')
    radius = float(profile.Radius) * factor
    length = float(straight.Depth) * factor
    if not math.isfinite(radius + length) or radius <= 0 or length <= 0 or not math.isclose(radius, bend['radius'], abs_tol=1e-10, rel_tol=0):
        raise ProjectError('positive equal-radius tangent pieces required')
    frame = rigid(object_frame @ rigid(placement.get_axis2placement(straight.Position)))
    frame[:3, 3] *= factor
    direction = np.array(straight.ExtrudedDirection.DirectionRatios, dtype=float)
    if direction.shape != (3,) or not np.isfinite(direction).all() or not np.allclose(direction, [0, 0, 1], atol=1e-10, rtol=0):
        raise ProjectError('positive local-Z straight extrusion required')
    start = frame[:3, 3]
    tangent = frame[:3, 2]
    end = start + tangent * length
    line = last.ParentCurve
    if not line.is_a('IfcPolyline') or len(line.Points) != 2:
        raise ProjectError('two-point independent straight Axis required')
    coords = np.array([p.Coordinates for p in line.Points], dtype=float)
    if coords.shape != (2, 3) or not np.isfinite(coords).all():
        raise ProjectError('finite 3D straight Axis required')
    coords = np.array([(object_frame @ np.append(p, 1))[:3] * factor for p in coords])
    if not np.allclose(coords, [start, end], atol=1e-9, rtol=0):
        raise ProjectError('straight Body differs from independent Axis')
    if not np.allclose(start, bend['points'][-1], atol=1e-9, rtol=0) or not np.allclose(tangent, bend['end_normals'][-1], atol=1e-10, rtol=0):
        raise ProjectError('pieces must meet with equal forward tangents')
    extent = radius * np.sqrt(np.maximum(0., 1 - tangent**2))
    bounds = np.array([np.minimum(start, end) - extent, np.maximum(start, end) + extent])
    volume = math.pi * radius**2 * length
    b = bend['expected']
    expected = dict(volume=b['volume'] + volume,
                    centroid=(b['centroid'] * b['volume'] + (start + end) / 2 * volume) / (b['volume'] + volume),
                    bounds=np.array([np.minimum(b['bounds'][0], bounds[0]), np.maximum(b['bounds'][1], bounds[1])]))
    return dict(length=bend['length'] + length, radius=radius, bend_radius=bend['bend_radius'],
                points=np.array([bend['points'][0], end]), expected=expected,
                end_normals=np.array([bend['end_normals'][0], tangent]))
