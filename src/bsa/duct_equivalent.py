"""Rectangular equivalent-round straight friction, separate from local losses.

ASHRAE Fundamentals 2021 ch21 Eq25/Table3; fluids 1.3.1 (MIT)
provides the Colebrook engine. Inputs are SI and must be sourced by callers.
"""
import math


def calculate(*, flow_m3_s, width_m, height_m, density_kg_m3,
              viscosity_Pa_s, roughness_m):
    values = (flow_m3_s, width_m, height_m, density_kg_m3, viscosity_Pa_s)
    if any(isinstance(x, bool) or not math.isfinite(x) or x <= 0 for x in values):
        raise ValueError('Flow, dimensions and fluid properties must be finite positive numbers')
    if isinstance(roughness_m, bool) or not math.isfinite(roughness_m) or roughness_m < 0:
        raise ValueError('Roughness must be finite and nonnegative')
    from fluids import friction_factor
    de = 1.30 * (width_m * height_m)**0.625 / (width_m + height_m)**0.25
    actual = flow_m3_s / (width_m * height_m)
    equivalent = 4 * flow_m3_s / (math.pi * de**2)
    re = density_kg_m3 * equivalent * de / viscosity_Pa_s
    if re < 4000:
        raise ValueError('Equivalent-round turbulent correlation requires Re >= 4000')
    f = friction_factor(re, roughness_m / de, Method='Colebrook', Darcy=True)
    return dict(equivalent_diameter_m=de, actual_velocity_m_s=actual,
                equivalent_round_velocity_m_s=equivalent, reynolds=re,
                darcy_factor=f, friction_Pa_m=f*density_kg_m3*equivalent**2/(2*de),
                aspect_ratio=max(width_m,height_m)/min(width_m,height_m),
                scope='Straight friction only; fitting losses require actual duct velocity',
                design_accepted=False)
