"""Thin reader for pinned native surfaceFieldValue output, not a CFD engine.

Scope: steady deltaT=1 cases, phi in m3/s, already verified Pt in Pa.
Caller binds fields, density, weighting and one explicitly selected run segment.
Never merge restart directories or silently trim misaligned observations here.
"""
from decimal import Decimal, InvalidOperation
import math


def read_samples(text, column):
    """Read one complete native two-column file; preserve signed quantities."""
    if column not in ('sum(phi)', 'average(Pt)'):
        raise ValueError('Verified native flux or total-pressure column required')
    if not text.endswith('\n'):
        raise ValueError('Native file must end with a complete newline-terminated row')
    headers = [line.lstrip('#').split() for line in text.splitlines()
               if line.startswith('#') and line.lstrip('#').split()[:1] == ['Time']]
    if headers != [['Time', column]]:
        raise ValueError('One exact native column header required')
    result = []
    for line in text.splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError('Incomplete or unexpected native row')
        try:
            time = Decimal(parts[0])
            value = float(parts[1])
        except (InvalidOperation, ValueError) as exc:
            raise ValueError('Numerical native row required') from exc
        if not time.is_finite() or time != time.to_integral_value() or not math.isfinite(value):
            raise ValueError('Finite integer steady step and finite value required')
        step = int(time)
        if result and step != result[-1][0] + 1:
            raise ValueError('Native rows must be consecutive without overlaps')
        result.append((step, value))
    if not result:
        raise ValueError('Native observations required')
    return result


def to_convergence_rows(flux, total_pressure, density_kg_m3):
    """Convert outward m3/s to inward-positive kg/s; Pt remains in Pa."""
    if (type(density_kg_m3) not in (int, float)
            or not math.isfinite(density_kg_m3) or density_kg_m3 <= 0):
        raise ValueError('Explicit positive finite source density required')
    if not flux or set(flux) != set(total_pressure):
        raise ValueError('Exactly matching named native patch histories required')
    if any(not isinstance(k, str) or not k for k in flux):
        raise ValueError('Nonempty patch names required')
    steps = [t for t, _ in next(iter(flux.values()))]
    if not steps or any(type(t) is not int for t in steps) or any(b-a != 1 for a, b in zip(steps, steps[1:])):
        raise ValueError('Consecutive integer native steps required')
    for series in (*flux.values(), *total_pressure.values()):
        if [t for t, _ in series] != steps:
            raise ValueError('Exact simultaneous native observation times required')
        if any(type(v) not in (int, float) or not math.isfinite(v) for _, v in series):
            raise ValueError('Finite native observations required')
    rows = []
    for i, step in enumerate(steps):
        row = {'Inner_Iter': step}
        for name in flux:
            mass = -density_kg_m3 * flux[name][i][1]
            if not math.isfinite(mass):
                raise ValueError('Converted mass flow must remain finite')
            row[f'Avg_Massflow({name})'] = mass
            row[f'Avg_TotalPress({name})'] = total_pressure[name][i][1]
        rows.append(row)
    return rows
