"""Read a saved smooth circular minor bend; no loss or product acceptance."""
import math
import numpy as np
from ifcopenshell.util import placement, system, unit
from .product_alignment import aligned_placement


def calculate(obj, inlet_name='inlet', outlet_name='outlet'):
    if obj.file.schema != 'IFC4' or not math.isclose(unit.calculate_unit_scale(obj.file), 1., rel_tol=0, abs_tol=1e-12) or not math.isclose(unit.calculate_unit_scale(obj.file, 'PLANEANGLEUNIT'), 1., rel_tol=0, abs_tol=1e-12):
        raise ValueError('Explicit metre IFC4 bend required')
    projects = obj.file.by_type('IfcProject')
    if len(projects) != 1 or not projects[0].UnitsInContext or not any(u.UnitType == 'LENGTHUNIT' for u in projects[0].UnitsInContext.Units if hasattr(u, 'UnitType')):
        raise ValueError('Explicit length unit required')
    if not obj.is_a('IfcDuctFitting') or obj.PredefinedType != 'BEND':
        raise ValueError('Native duct BEND required')
    reps = obj.Representation.Representations if obj.Representation else []
    bodies = [r for r in reps if r.RepresentationIdentifier == 'Body']
    axes = [r for r in reps if r.RepresentationIdentifier == 'Axis']
    if len(bodies) != 1 or len(axes) != 1 or len(bodies[0].Items) != 1 or len(axes[0].Items) != 1:
        raise ValueError('One body and independent Axis required')
    solid = bodies[0].Items[0]
    if not solid.is_a('IfcRevolvedAreaSolid') or not solid.SweptArea.is_a('IfcCircleHollowProfileDef'):
        raise ValueError('Revolved hollow circular profile required')
    profile = solid.SweptArea
    if profile.ProfileType != 'AREA' or not profile.Position or profile.Position.RefDirection is not None:
        raise ValueError('Explicit unrotated radial profile offset required')
    xy = profile.Position.Location.Coordinates
    if len(xy) != 2 or xy[1] != 0.:
        raise ValueError('Radial profile offset required')
    radius, outer, gauge, angle = float(xy[0]), float(profile.Radius), float(profile.WallThickness), float(solid.Angle)
    if not all(math.isfinite(v) for v in (radius, outer, gauge, angle)) or not 0 < gauge < outer < radius or not 0 < angle <= math.pi/2:
        raise ValueError('Finite positive minor bend dimensions required')
    if not np.allclose(placement.get_axis2placement(solid.Position), np.eye(4), atol=1e-10, rtol=0) or tuple(solid.Axis.Location.Coordinates) != (0., 0., 0.) or solid.Axis.Axis is None or tuple(solid.Axis.Axis.DirectionRatios) != (0., 1., 0.):
        raise ValueError('Explicit local positive-Y revolution required')
    world = placement.get_local_placement(obj.ObjectPlacement)
    aligned_placement(world, np.eye(4), 0)
    curve = axes[0].Items[0]
    if not curve.is_a('IfcIndexedPolyCurve') or not curve.Points.is_a('IfcCartesianPointList3D') or curve.SelfIntersect is not False or len(curve.Segments or []) != 1 or not curve.Segments[0].is_a('IfcArcIndex') or tuple(curve.Segments[0].wrappedValue) != (1, 2, 3):
        raise ValueError('One independent three-point minor arc required')
    pts = np.asarray(curve.Points.CoordList, dtype=float)
    if pts.shape != (3, 3) or not np.isfinite(pts).all():
        raise ValueError('Three finite Axis points required')
    a, b, c = pts
    u, v = b-a, c-a
    w = np.cross(u, v)
    den = 2*float(w@w)
    if den <= 1e-24:
        raise ValueError('Axis arc is numerically degenerate')
    centre = a + ((u@u)*np.cross(v, w)+(v@v)*np.cross(w, u))/den
    axis_radius = float(np.linalg.norm(a-centre))
    x, y = (a-centre)/axis_radius, (c-centre)/axis_radius
    axis_angle = math.atan2(float(np.linalg.norm(np.cross(x, y))), float(x@y))
    expected = np.array([[radius*math.cos(t), 0., -radius*math.sin(t)] for t in (0., angle/2, angle)])
    if not np.allclose(pts, expected, atol=1e-9, rtol=0) or not np.allclose(centre, 0., atol=1e-8, rtol=0) or not math.isclose(axis_radius, radius, rel_tol=1e-8, abs_tol=0) or not math.isclose(axis_angle, angle, rel_tol=1e-8, abs_tol=0):
        raise ValueError('Independent Axis and native swept bend differ')
    ports = system.get_ports(obj)
    if len(ports) != 2 or {p.Name for p in ports} != {inlet_name, outlet_name} or inlet_name == outlet_name:
        raise ValueError('Two distinct owned bend ports required')
    definitions = [(inlet_name, pts[0], [0., 0., 1.], 'SINK'), (outlet_name, pts[-1], [-math.sin(angle), 0., -math.cos(angle)], 'SOURCE')]
    for name, point, normal, flow in definitions:
        port = next(p for p in ports if p.Name == name)
        f = placement.get_local_placement(port.ObjectPlacement)
        aligned_placement(f, np.eye(4), 0)
        if system.get_port_element(port) != obj or port.FlowDirection != flow or not np.allclose(f[:3, 3], world[:3, 3]+world[:3, :3]@point, atol=1e-8, rtol=0) or not np.allclose(f[:3, 2], world[:3, :3]@normal, atol=1e-8, rtol=0):
            raise ValueError('Owned directed bend cap differs')
    return dict(inner_m=2*(outer-gauge), outer_m=2*outer, radius_m=radius,
        angle_rad=axis_angle, angle_degrees=math.degrees(axis_angle),
        centreline_length_m=axis_radius*axis_angle,
        analytic_wall_volume_m3=math.pi*(outer**2-(outer-gauge)**2)*radius*angle,
        physical_applicability_verified=False, pressure_loss_Pa=None)
