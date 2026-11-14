"""Bounded manufacturer operating-pressure baseline; never a device loss."""
import math
import fluids
from fluids.numerics import interp

SOURCE_URL = 'https://www.krueger-hvac.com/file/7365/SDIOM.pdf'
SOURCE_SHA256 = 'ea1d801c7d69eee95d000c88994e9bd6e80d1670a386ddec89fd4f55b9e6bd69'
# Actually viewed PDF/printed17 Table6.A; CFM, velocity pressure, basic static.
# Rounded inch-water source columns are retained together; no other table merged.
TABLE = {
    12: [(425, .01, .01), (1000, .08, .04), (1600, .20, .10), (2060, .33, .17)],
    14: [(580, .01, .01), (1375, .07, .04), (2100, .16, .10), (2800, .29, .18)],
}


def calculate(nominal_inlet_in, design_flow_m3_s):
    if fluids.__version__ != '1.3.1':
        raise ValueError('Pinned fluids1.3.1 required')
    if type(nominal_inlet_in) is not int or nominal_inlet_in not in TABLE:
        raise ValueError('Only source-reviewed sizes12/14 supported')
    if type(design_flow_m3_s) not in (float, int) or not math.isfinite(design_flow_m3_s) or design_flow_m3_s <= 0:
        raise ValueError('Finite positive SI design flow required')
    q = design_flow_m3_s / .0004719474432
    rows = TABLE[nominal_inlet_in]
    result = dict(nominal_inlet_in=nominal_inlet_in, design_flow_m3_s=design_flow_m3_s,
        design_CFM=q, source_url=SOURCE_URL, source_sha256=SOURCE_SHA256,
        source_locator='PDF17/printed17 Table6.A basic unit,damper fully open',
        interpolation='Piecewise linear CFM approximation on rounded IP columns;no extrapolation',
        pressure_quantity='Manufacturer velocity-plus-static baseline;not two-plane total-pressure loss',
        outlet_velocity_pressure_Pa=None, device_total_pressure_loss_Pa=None,
        controlled_operating_pressure_Pa=None, design_accepted=False)
    if not rows[0][0] <= q <= rows[-1][0]:
        return dict(result, status='outside_published_flow_range')
    vp = interp(q, [r[0] for r in rows], [r[1] for r in rows])
    sp = interp(q, [r[0] for r in rows], [r[2] for r in rows])
    return dict(result, status='conditional_fully_open_baseline',
        source_velocity_pressure_Pa=vp*249.08891,
        source_static_difference_Pa=sp*249.08891,
        source_velocity_plus_static_Pa=(vp+sp)*249.08891)
