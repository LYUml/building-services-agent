"""Analytic interpolation error for one decreasing line segment drawn on log-log axes."""
import math
from .engine import ProjectError


def segment_bound(x0,y0,x1,y1):
    values=(x0,y0,x1,y1)
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values) or x1<=x0 or y1>=y0:raise ProjectError('positive strictly increasing flow/decreasing pressure segment required')
    r=x1/x0;s=y1/y0
    if not math.isfinite(r) or r<=1 or not 0<s<1:raise ProjectError('unrepresentable normalised curve segment')
    k=math.log(s)/math.log(r);m=(s-1)/(r-1)
    relative_x=k*(1-m)/(m*(1-k))
    absolute_x=math.exp(math.log(m/k)/(k-1))
    if not 1<=relative_x<=r or not 1<=absolute_x<=r:raise ProjectError('interpolation stationary point outside segment')
    relative=max(0.,math.expm1(math.log1p(m*(relative_x-1))-k*math.log(relative_x)))
    absolute=max(0.,y0*((1+m*(absolute_x-1))-absolute_x**k))
    return dict(maximum_relative_pressure_excess=relative,maximum_absolute_pressure_excess_pa=absolute,
        relative_maximum_flow=x0*relative_x,absolute_maximum_flow=x0*absolute_x,log_log_exponent=k,
        relation='physical-coordinate chord is above convex log-log segment; bounds exclude endpoint rounding and manufacturer/graph uncertainty')


def curve_bound(points):
    if not isinstance(points,list) or len(points)<2:raise ProjectError('at least two native calibrated points required')
    rows=[dict(segment=i,**segment_bound(*a,*b)) for i,(a,b) in enumerate(zip(points,points[1:]))]
    return dict(segment_count=len(rows),maximum_relative_pressure_excess=max(r['maximum_relative_pressure_excess'] for r in rows),maximum_absolute_pressure_excess_pa=max(r['maximum_absolute_pressure_excess_pa'] for r in rows),segments=rows)
