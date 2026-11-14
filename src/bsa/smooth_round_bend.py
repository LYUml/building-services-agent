"""Conditional smooth-wall bend study using the pinned upstream loss engine."""
import math
import fluids
from fluids.fittings import bend_rounded
from fluids.friction import friction_factor
from .round_bend_quantities import calculate as native_bend


def calculate(obj, flow_m3_s, density_kg_m3, viscosity_Pa_s, *, construction_basis):
    if construction_basis != 'smooth_rigid_candidate':
        raise ValueError('Explicit smooth rigid candidate required; corrugated flex unsupported')
    if fluids.__version__ != '1.3.1':
        raise ValueError('Study requires pinned fluids 1.3.1')
    for v in (flow_m3_s, density_kg_m3, viscosity_Pa_s):
        if type(v) not in (int, float) or not math.isfinite(v) or v <= 0:
            raise ValueError('Finite positive SI flow, density and viscosity required')
    native = native_bend(obj)
    d, r = native['inner_m'], native['radius_m']
    v = flow_m3_s/(math.pi*d*d/4)
    re = density_kg_m3*v*d/viscosity_Pa_s
    if re < 4000:
        raise ValueError('This study is restricted to turbulent flow')
    fd = friction_factor(Re=re, eD=0., Method='Colebrook')
    k = bend_rounded(Di=d, angle=native['angle_degrees'], rc=r, fd=fd, method='Rennels')
    vp = density_kg_m3*v*v/2
    return dict(product_guid=obj.GlobalId, native_geometry=native,
        construction_basis=construction_basis, roughness_m=0.,
        flow_m3_s=flow_m3_s, density_kg_m3=density_kg_m3, viscosity_Pa_s=viscosity_Pa_s,
        velocity_m_s=v, Reynolds=re, Darcy_factor=fd, coefficient=k,
        reference_velocity_pressure_Pa=vp, conditional_bend_loss_Pa=k*vp,
        included_arc_friction_Pa=fd*native['centreline_length_m']/d*vp,
        arc_friction_must_not_be_added_again=True,
        source='fluids 1.3.1 bend_rounded Rennels; Rennels and Hudson 2012',
        source_url='https://fluids.readthedocs.io/fluids.fittings.html#fluids.fittings.bend_rounded',
        physical_applicability_verified=False, interaction_verified=False,
        installed_flex_loss_Pa=None, design_accepted=False)
