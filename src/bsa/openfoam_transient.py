"""Fixed-step physical-time diagnostics, separate from steady convergence gates.

Uses pinned NumPy quadrature; does not infer stationarity, ADPI or design acceptance.
Callers bind the native fields, pressure definition, units and selected run segment.
"""
from decimal import Decimal, InvalidOperation
import math

import numpy as np


def _seconds(value):
    if not isinstance(value, (str, Decimal)):
        raise ValueError('Explicit decimal-string physical seconds required')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Finite physical seconds required') from exc
    if not result.is_finite() or result < 0:
        raise ValueError('Finite nonnegative physical seconds required')
    return result


def _validate(samples):
    if not samples:
        raise ValueError('Physical-time observations required')
    previous = None
    for time, value in samples:
        if not isinstance(time, Decimal):
            raise ValueError('Decimal physical-time labels required')
        _seconds(time)
        if previous is not None and time <= previous:
            raise ValueError('Strictly increasing physical times required')
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('Finite observation required')
        previous = time


def read_samples(text, column, *, delta_t_s):
    """Read a complete single native segment; never trim rows or merge restarts."""
    if column not in ('sum(phi)', 'orientedSum(phi)', 'average(Pt)', 'average(Ptf)'):
        raise ValueError('Explicit supported native column required')
    dt = _seconds(delta_t_s)
    if dt == 0 or not text.endswith('\n'):
        raise ValueError('Positive time step and complete newline-terminated file required')
    headers = [line.lstrip('#').split() for line in text.splitlines()
               if line.startswith('#') and line.lstrip('#').split()[:1] == ['Time']]
    if headers != [['Time', column]]:
        raise ValueError('One matching native column header required')
    result = []
    for line in text.splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError('Exactly two complete native columns required')
        try:
            time, value = _seconds(parts[0]), float(parts[1])
        except ValueError as exc:
            raise ValueError('Finite numerical native row required') from exc
        if result and time - result[-1][0] != dt:
            raise ValueError('Exact consecutive physical time steps required')
        result.append((time, value))
    _validate(result)
    return result


def difference(left, right):
    """Subtract simultaneous signed quantities, without guessing their units."""
    _validate(left)
    _validate(right)
    if [t for t, _ in left] != [t for t, _ in right]:
        raise ValueError('Exactly matching physical times required')
    result = [(t, a-b) for (t, a), (_, b) in zip(left, right)]
    _validate(result)
    return result


def window_statistics(samples, start_s, end_s):
    """Trapezoidal time-weighted moments; endpoint samples must exist exactly.

    RMS uses quadrature of squared nodal deviations, not an exact continuous
    variance or an uncertainty/confidence estimate. No extrapolation is allowed.
    """
    _validate(samples)
    start, end = _seconds(start_s), _seconds(end_s)
    if start >= end:
        raise ValueError('Positive physical-time window required')
    window = [(t, v) for t, v in samples if start <= t <= end]
    if len(window) < 2 or window[0][0] != start or window[-1][0] != end:
        raise ValueError('Exact sampled window endpoints required')
    x = np.array([float(t-start) for t, _ in window])
    y = np.array([v for _, v in window])
    if not np.isfinite(x).all() or np.any(np.diff(x) <= 0):
        raise ValueError('Physical times must remain distinct in quadrature precision')
    duration = float(end-start)
    with np.errstate(over='raise', invalid='raise', divide='raise'):
        try:
            mean = float(np.trapezoid(y, x)/duration)
            rms = float(np.sqrt(np.trapezoid((y-mean)**2, x)/duration))
            span = float(np.ptp(y))
        except FloatingPointError as exc:
            raise ValueError('Finite quadrature results required') from exc
    if not all(math.isfinite(v) for v in (mean, rms, span)):
        raise ValueError('Finite quadrature results required')
    return {'start_s': str(start), 'end_s': str(end), 'samples': len(window),
            'time_weighted_mean': mean, 'time_weighted_rms': rms, 'range': span,
            'diagnostic_only': True, 'stationarity_accepted': False,
            'pressure_adopted': False}
