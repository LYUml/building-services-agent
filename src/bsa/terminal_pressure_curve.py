"""Bounded squared-flow pressure comparison using existing fluids interpolation."""
import math
from fluids.numerics import interp


FIELDS = ('total_pressure_Pa', 'static_pressure_Pa')


def reviewed_rows(rows):
    if len(rows) < 3:
        raise ValueError('At least three source pressure rows required')
    for r in rows:
        if any(type(r[k]) not in (int, float) or not math.isfinite(r[k]) or r[k] <= 0
               for k in ('flow_L_s', *FIELDS)):
            raise ValueError('Finite positive source flow and pressures required')
        if r['static_pressure_Pa'] > r['total_pressure_Pa']:
            raise ValueError('Static pressure exceeds source total pressure')
    if any(a['flow_L_s'] >= b['flow_L_s'] for a, b in zip(rows, rows[1:])):
        raise ValueError('Strictly increasing source flows required')
    return rows


def calculate(rows, flow_L_s):
    rows = reviewed_rows(rows)
    if type(flow_L_s) not in (int, float) or not math.isfinite(flow_L_s) or flow_L_s <= 0:
        raise ValueError('Finite positive design flow required')
    if not rows[0]['flow_L_s'] <= flow_L_s <= rows[-1]['flow_L_s']:
        raise ValueError('No terminal pressure extrapolation')
    q = [r['flow_L_s'] for r in rows]
    result = dict(flow_L_s=flow_L_s, interpolation_basis='Piecewise linear in squared flow',
        installed_terminal_pressure_verified=False, ADPI_verified=False,
        fan_duty_Pa=None, design_accepted=False)
    for k in FIELDS:
        p = [r[k] for r in rows]
        result[k] = interp(flow_L_s**2, [x*x for x in q], p)
        result['linear_flow_comparison_'+k] = interp(flow_L_s, q, p)
    return result


def square_law_rounding_band(rows, *, flow_half_step_L_s, pressure_half_step_Pa):
    """Constant P/Q² compatibility only; caller-declared rounding is not accuracy."""
    rows = reviewed_rows(rows)
    for v in (flow_half_step_L_s, pressure_half_step_Pa):
        if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
            raise ValueError('Explicit nonnegative rounding steps required')
    if any(r['flow_L_s'] <= flow_half_step_L_s or
           min(r[k] for k in FIELDS) <= pressure_half_step_Pa for r in rows):
        raise ValueError('Rounding bounds cross zero')
    result = {}
    for k in FIELDS:
        low = max((r[k]-pressure_half_step_Pa)/(r['flow_L_s']+flow_half_step_L_s)**2 for r in rows)
        high = min((r[k]+pressure_half_step_Pa)/(r['flow_L_s']-flow_half_step_L_s)**2 for r in rows)
        result[k] = dict(compatible=low <= high, coefficient_low=low,
            coefficient_high=high, unit='Pa/(L/s)^2')
    return dict(fields=result, assumed_flow_half_step_L_s=flow_half_step_L_s,
        assumed_pressure_half_step_Pa=pressure_half_step_Pa,
        manufacturer_accuracy_verified=False, installed_uncertainty_verified=False)
