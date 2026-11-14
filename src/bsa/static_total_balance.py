"""Signed pressure identity at explicitly declared equal-flow reference stations."""
from .loss_reference import finite


def calculate(static_difference_Pa, flow_m3_s, density_kg_m3,
              inlet_area_m2, outlet_area_m2, *, station_basis):
    if not isinstance(station_basis, str) or not station_basis.strip():
        raise ValueError('Explicit reference-station basis required')
    ps = finite(static_difference_Pa)
    q, rho, ai, ao = [finite(v, True) for v in
        (flow_m3_s, density_kg_m3, inlet_area_m2, outlet_area_m2)]
    vi, vo = finite(q/ai, True), finite(q/ao, True)
    pvi, pvo = finite(rho*vi*vi/2, True), finite(rho*vo*vo/2, True)
    correction = finite(pvi-pvo)
    total = finite(ps+correction)
    return dict(static_difference_Pa=ps, inlet_velocity_pressure_Pa=pvi,
        outlet_velocity_pressure_Pa=pvo, velocity_pressure_difference_Pa=correction,
        conditional_total_difference_Pa=total, passive_loss_sign_consistent=total >= 0,
        flow_m3_s=q, density_kg_m3=rho, inlet_area_m2=ai, outlet_area_m2=ao,
        station_basis=station_basis, source_station_correspondence_verified=False,
        actual_controlled_device_loss_Pa=None, physical_applicability_verified=False,
        design_accepted=False)
