"""Bounded catalogue throw interpolation using pinned fluids, not ADPI prediction."""
import math
from fluids.numerics import interp


def positive(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('Finite positive numeric value required')
    return value


def evaluate(rows, *, maximum_flow_L_s, turndown, characteristic_length_m):
    q = positive(maximum_flow_L_s)
    length = positive(characteristic_length_m)
    if positive(turndown) > 1:
        raise ValueError('Turndown must be <=1')
    if len(rows) < 2:
        raise ValueError('At least two catalogue rows required')
    flows = [positive(r['flow_L_s']) for r in rows]
    throws = [positive(r['T025_m']) for r in rows]
    if any(b <= a for a,b in zip(flows,flows[1:])):
        raise ValueError('Catalogue flows must be strictly increasing')
    cases = {}
    for name, flow in [('maximum',q), ('minimum',q*turndown)]:
        if not flows[0] <= flow <= flows[-1]:
            cases[name] = dict(flow_L_s=flow,status='outside_catalogue',T025_m=None,ratio=None)
            continue
        throw = interp(flow, flows, throws)
        bracket = next((i for i in range(len(flows)-1) if flows[i] <= flow <= flows[i+1]))
        cases[name] = dict(flow_L_s=flow,status='within_catalogue',T025_m=throw,
                           ratio=throw/length,bracketing_rows=[bracket,bracket+1])
    return dict(cases=cases,method='Piecewise linear interpolation; explicit design approximation',
                ADPI_verified=False,design_accepted=False,
                pending=['Catalogue condition and characteristic-length applicability',
                         'ADPI classification, thermal load and criterion applicability'])
