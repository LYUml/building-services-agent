"""Signed native flux-window checks, independent of solver and pressure checks."""
import math


def assess_flux_window(rows, targets, *, window=200, relative_tolerance=.001):
    """Fluxes and targets use one unit and outward-positive signs throughout.

    Caller must bind patch names, saved steps and units to actual native output.
    Passing boundary algebra never establishes pressure or physical accuracy.
    """
    def finite(value):
        return type(value) in (int, float) and math.isfinite(value)

    if type(window) is not int or window < 2 or len(rows) < window:
        raise ValueError('Complete multi-step window required')
    if not finite(relative_tolerance) or not 0 < relative_tolerance < 1:
        raise ValueError('Explicit relative tolerance between zero and one required')
    if len(targets) < 2 or any(not isinstance(k, str) or not k for k in targets):
        raise ValueError('Named inlet and outlet targets required')
    if any(not finite(v) or v == 0 for v in targets.values()):
        raise ValueError('Finite nonzero signed targets required')
    incoming = -math.fsum(v for v in targets.values() if v < 0)
    outgoing = math.fsum(v for v in targets.values() if v > 0)
    if not incoming or not outgoing or not math.isclose(incoming, outgoing, rel_tol=1e-12):
        raise ValueError('Conservative signed targets required')
    data = rows[-window:]
    steps = [r['step'] for r in data]
    if any(type(i) is not int for i in steps) or any(b-a != 1 for a, b in zip(steps, steps[1:])):
        raise ValueError('Consecutive integer native steps required')
    errors = {name: 0. for name in targets}
    imbalance = 0.
    for row in data:
        flux = row['fluxes']
        if set(flux) != set(targets) or any(not finite(v) for v in flux.values()):
            raise ValueError('Exact finite named native fluxes required')
        for name, target in targets.items():
            errors[name] = max(errors[name], abs(flux[name]-target)/abs(target))
        imbalance = max(imbalance, abs(math.fsum(flux.values()))/incoming)
    return {
        'window': [steps[0], steps[-1]], 'samples': window,
        'max_relative_flux_errors': errors,
        'max_relative_global_imbalance': imbalance,
        'relative_tolerance': relative_tolerance,
        'signed_flux_window_passed': max(*errors.values(), imbalance) <= relative_tolerance,
        'pressure_accepted': False, 'engineering_accepted': False,
    }
