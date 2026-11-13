"""Separate developed-flow study of native transition end straights, not taper loss."""
import math
from . import duct_equivalent


def calculate(request, air):
    geometry = request['transition_geometry']
    if geometry is None:
        raise ValueError('Native centred transition geometry required')
    rows = []
    for end in ('inlet', 'outlet'):
        length = geometry['quantities'][end+'_straight_length_m']
        if isinstance(length, bool) or not math.isfinite(length) or length < 0:
            raise ValueError('Finite nonnegative native straight length required')
        width, height = geometry[end+'_section_m']
        port = request[end]
        if not all(math.isclose(a,b,rel_tol=0,abs_tol=1e-10) for a,b in
                zip((width,height),(port['width_m'],port['height_m']))):
            raise ValueError('Native ring and directed port dimensions differ')
        result = duct_equivalent.calculate(flow_m3_s=port['flow_m3_s'],
            width_m=width,height_m=height,**air)
        if not math.isfinite(length*result['friction_Pa_m']):
            raise ValueError('Finite straight friction contribution required')
        rows.append(dict(end=end,port_guid=request[end+'_port_guid'],length_m=length,
            width_m=width,height_m=height,flow_m3_s=port['flow_m3_s'],
            calculation=result,developed_flow_study_friction_Pa=length*result['friction_Pa_m']))
    if not math.isclose(rows[0]['flow_m3_s'],rows[1]['flow_m3_s'],rel_tol=1e-10,abs_tol=1e-12):
        raise ValueError('Transition end flows must conserve mass for inherited common density')
    return dict(product_guid=request['product_guid'],geometry_sha256=request['geometry_sha256'],
        ends=rows,developed_flow_study_friction_Pa=math.fsum(r['developed_flow_study_friction_Pa'] for r in rows),
        added_to_pressure_paths=False,physical_applicability_verified=False,
        scope='Separate equivalent-round developed-flow study of constant-section end lengths only. '
        'Short adjacent fittings may prevent developed flow. Taper friction, local losses, source table '
        'station/friction inclusion and interactions remain unresolved; do not add to table results '
        'or infer complete fitting pressure or fan duty.')
