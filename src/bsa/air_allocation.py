"""Compose classified load balance and explicit nearest-centre service allocation."""
import math
from .air_load import calculate
from .service_areas import allocate


def prepare(boundary, terminals, load_inputs, turndown):
    if type(turndown) not in (int, float) or not math.isfinite(turndown) or not 0 < turndown <= 1:
        raise ValueError('Explicit turndown in (0,1] required')
    load = calculate(load_inputs)
    allocation = allocate(boundary, terminals, load_inputs['area']['value'])
    rows = []
    for cell in allocation['terminals']:
        fraction = cell['allocated_load_area_m2']/allocation['given_load_area_m2']
        flow = fraction*load['supply_flow_L_s']
        rows.append(dict(cell, maximum_flow_L_s=flow, minimum_flow_L_s=flow*turndown))
    area = math.fsum(r['allocated_load_area_m2'] for r in rows)
    flow = math.fsum(r['maximum_flow_L_s'] for r in rows)
    if not math.isclose(area, allocation['given_load_area_m2'], rel_tol=1e-10) or not math.isclose(flow, load['supply_flow_L_s'], rel_tol=1e-10):
        raise ValueError('Allocated area or flow does not conserve total')
    return dict(load=load, allocation=allocation, terminals=rows, turndown=turndown,
                checks=dict(allocated_area_m2=area, allocated_flow_L_s=flow,
                            area_conserved=True, flow_conserved=True),
                scope='Uniform allowance allocated by nearest-centre area; not spatial load simulation, duct routing, air coverage or ADPI acceptance',
                design_accepted=False)
