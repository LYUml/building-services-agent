"""Read supported centred four-ring transition dimensions,not a loss correlation."""
import math

import numpy as np

ANGLE_QUANTITIES = {'taper_width_angle_deg', 'taper_height_angle_deg', 'major_taper_angle_deg',
    'taper_angle_difference_deg'}
QUANTITIES = ANGLE_QUANTITIES | {'taper_length_m', 'inlet_straight_length_m', 'outlet_straight_length_m',
    'total_length_m', 'outlet_hydraulic_diameter_m', 'taper_length_over_outlet_hydraulic_diameter',
    'total_length_over_outlet_hydraulic_diameter'}

FAMILIES = {'centred_one_plane', 'centred_equal_angle_pyramidal'}


def family_check(family, geometry):
    """Necessary diagram geometry only; numerical equality is not fabrication tolerance."""
    if family not in FAMILIES:
        raise ValueError('Supported centred transition family required')
    if geometry is None:
        raise ValueError('Native transition geometry required for family check')
    q = geometry['quantities']
    angles = [q['taper_width_angle_deg'], q['taper_height_angle_deg']]
    if any(not math.isfinite(v) or not 0 <= v < 180 for v in angles):
        raise ValueError('Finite native wall angles required')
    same_direction = geometry['flow_change'] in ('contraction', 'expansion')
    # An unchanged plane must actually be unchanged. Do not turn a shallow
    # two-plane taper into a one-plane fitting by an angular tolerance.
    if family == 'centred_one_plane':
        matches = min(angles) == 0 and max(angles) > 0
    else:
        matches = min(angles) > 0 and abs(angles[0]-angles[1]) <= 1e-6
    return dict(family=family, pass_check=bool(matches and same_direction),
        numerical_equal_angle_bound_deg=1e-6 if family=='centred_equal_angle_pyramidal' else None,
        physical_applicability_verified=False)


def rings(brep):
    if not brep.is_a('IfcFacetedBrep'): raise ValueError('Supported faceted transition BRep required')
    points = np.unique(np.asarray([p.Coordinates for face in brep.Outer.CfsFaces for bound in face.Bounds
        for p in bound.Bound.Polygon], dtype=float), axis=0)
    if points.shape != (16, 3) or not np.isfinite(points).all(): raise ValueError('Sixteen finite transition ring corners required')
    stations = np.unique(points[:, 2]); sections = []
    if len(stations) != 4: raise ValueError('Four distinct axial transition stations required')
    for z in stations:
        ring = points[points[:, 2] == z]; lo, hi = ring[:, :2].min(axis=0), ring[:, :2].max(axis=0)
        if len(ring) != 4 or np.any(hi <= lo) or not np.allclose(lo, -hi, rtol=0, atol=1e-10):
            raise ValueError('Centred positive rectangular ring required')
        expected = np.asarray([(x,y,z) for x in (lo[0],hi[0]) for y in (lo[1],hi[1])])
        if any(np.min(np.linalg.norm(ring-p, axis=1)) > 1e-10 for p in expected): raise ValueError('Rectangular ring corners differ')
        sections.append(hi-lo)
    if not np.allclose(sections[0],sections[1],rtol=0,atol=1e-10) or not np.allclose(sections[2],sections[3],rtol=0,atol=1e-10):
        raise ValueError('Explicit straight end sections required')
    return stations, np.asarray(sections)


def calculate(obj, inlet_name, outlet_name):
    """Requires separate full native geometry/source inspection before design use."""
    if not obj.is_a('IfcDuctFitting') or obj.PredefinedType != 'TRANSITION' or {inlet_name,outlet_name} != {'start','end'}:
        raise ValueError('Supported directed rectangular transition required')
    representations = obj.Representation.Representations
    if len(representations) != 1 or len(representations[0].Items) != 1: raise ValueError('Single saved transition body required')
    body = representations[0].Items[0]
    if not body.is_a('IfcBooleanResult') or body.Operator != 'DIFFERENCE': raise ValueError('Outer-minus-inner transition wall required')
    outer_z, outer = rings(body.FirstOperand); inner_z, inner = rings(body.SecondOperand)
    if not np.allclose(outer_z[1:3],inner_z[1:3],rtol=0,atol=1e-10) or not np.all(outer > inner):
        raise ValueError('Native wall and taper station correspondence required')
    # Inner end caps deliberately extend for the Boolean bore; use outer end planes.
    start, taper, end = [float(x) for x in np.diff(outer_z)]
    inlet, outlet = (inner[0],inner[-1]) if inlet_name=='start' else (inner[-1],inner[0])
    inlet_straight, outlet_straight = (start,end) if inlet_name=='start' else (end,start)
    angles = [math.degrees(2*math.atan2(abs(float(b-a)),2*taper)) for a,b in zip(inlet,outlet)]
    dh = float(2*outlet[0]*outlet[1]/sum(outlet)); total = start+taper+end
    change = 'contraction' if np.all(outlet <= inlet) and np.any(outlet < inlet) else 'expansion' if np.all(outlet >= inlet) and np.any(outlet > inlet) else 'mixed_width_height_change'
    quantities = dict(taper_length_m=taper,inlet_straight_length_m=inlet_straight,outlet_straight_length_m=outlet_straight,
        total_length_m=total,taper_width_angle_deg=angles[0],taper_height_angle_deg=angles[1],major_taper_angle_deg=max(angles),
        taper_angle_difference_deg=abs(angles[0]-angles[1]),
        outlet_hydraulic_diameter_m=dh,taper_length_over_outlet_hydraulic_diameter=taper/dh,total_length_over_outlet_hydraulic_diameter=total/dh)
    if any(not math.isfinite(v) or v < 0 for v in quantities.values()): raise ValueError('Finite nonnegative transition quantities required')
    return dict(quantities=quantities,flow_change=change,inlet_section_m=inlet.tolist(),outlet_section_m=outlet.tolist(),
        outer_station_z_m=outer_z.tolist(),inner_station_z_m=inner_z.tolist(),
        scope='Supported saved centred transition dimensions only;Boolean cap extension excluded from physical length. Hydraulic diameter is a declared geometric quantity,not proof of a loss-method substitution. Source construction assumptions and full native/source/physical review remain separate.')
