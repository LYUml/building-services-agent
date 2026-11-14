"""Scoped analytic circular reducer dimensions; physical applicability is separate."""
import math
import numpy as np
from ifcopenshell.util import placement, system
from ifcopenshell.util.unit import calculate_unit_scale


def calculate(obj, flow_m3_s, density_kg_m3):
    model = obj.file
    projects = model.by_type('IfcProject')
    if model.schema != 'IFC4' or len(projects) != 1 or not projects[0].UnitsInContext:
        raise ValueError('Explicit project units required')
    units = [u for u in projects[0].UnitsInContext.Units if getattr(u, 'UnitType', None) == 'LENGTHUNIT']
    if len(units) != 1 or calculate_unit_scale(model) != 1:
        raise ValueError('Metre model required')
    if not obj.is_a('IfcDuctFitting') or obj.PredefinedType != 'TRANSITION':
        raise ValueError('Duct transition required')
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in (flow_m3_s, density_kg_m3)):
        raise ValueError('Positive finite flow and density required')
    reps = obj.Representation.Representations if obj.Representation else []
    if len(reps) != 1 or len(reps[0].Items) != 1:
        raise ValueError('Single native reducer body required')
    solid = reps[0].Items[0]
    if not solid.is_a('IfcRevolvedAreaSolid') or not math.isfinite(solid.Angle) or abs(solid.Angle - 2 * math.pi) > 1e-12:
        raise ValueError('Full analytic revolution required')
    if not np.allclose(placement.get_axis2placement(solid.Position), np.eye(4), atol=1e-12, rtol=0):
        raise ValueError('Identity native solid position required')
    if tuple(solid.Axis.Location.Coordinates) != (0., 0., 0.) or tuple(solid.Axis.Axis.DirectionRatios) != (0., 1., 0.):
        raise ValueError('Supported profile-axis datum required')
    profile = solid.SweptArea
    if profile.is_a() != 'IfcArbitraryClosedProfileDef' or not profile.OuterCurve.is_a('IfcPolyline'):
        raise ValueError('Explicit closed annular section required')
    pts = np.array([p.Coordinates for p in profile.OuterCurve.Points])
    if pts.shape != (9, 2) or not np.isfinite(pts).all():
        raise ValueError('Nine finite section points required')
    r1, r2 = pts[7, 0], pts[4, 0]
    c1, taper, c2 = pts[1, 1], pts[2, 1] - pts[1, 1], pts[3, 1] - pts[2, 1]
    gauge = pts[0, 0] - r1
    if not r1 > r2 > 0 or min(c1, taper, c2, gauge) <= 0:
        raise ValueError('Positive centred contraction with collars required')
    length = c1 + taper + c2
    expected = [(r1+gauge, 0), (r1+gauge, c1), (r2+gauge, c1+taper), (r2+gauge, length),
                (r2, length), (r2, c1+taper), (r1, c1), (r1, 0), (r1+gauge, 0)]
    if not np.allclose(pts, expected, atol=1e-12, rtol=0):
        raise ValueError('Supported constant radial wall profile required')
    frame = placement.get_local_placement(obj.ObjectPlacement)
    ports = system.get_ports(obj)
    if len(ports) != 2 or {p.FlowDirection for p in ports} != {'SINK', 'SOURCE'}:
        raise ValueError('Two directed owned ports required')
    for p in ports:
        f = placement.get_local_placement(p.ObjectPlacement)
        inlet = p.FlowDirection == 'SINK'
        if not np.allclose(f[:3, 3], frame[:3, 3] + frame[:3, 1] * (0 if inlet else length), atol=1e-9, rtol=0) or not np.allclose(f[:3, 2], frame[:3, 1] * (-1 if inlet else 1), atol=1e-9, rtol=0):
            raise ValueError('Native face centre and port normal required')
    area = math.pi * r1**2
    return dict(inlet_diameter_m=2*r1, outlet_diameter_m=2*r2, taper_m=taper,
                inlet_collar_m=c1, outlet_collar_m=c2, radial_gauge_m=gauge,
                inlet_to_outlet_area_ratio=(r1/r2)**2,
                included_angle_deg=math.degrees(2*math.atan((r1-r2)/taper)),
                inlet_velocity_pressure_Pa=density_kg_m3*(flow_m3_s/area)**2/2,
                reference='Large inlet Ao/Vo for source4-1 contraction',
                physical_applicability_verified=False)
