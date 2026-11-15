"""Numerical SU2 history checks; these never grant engineering acceptance.

Boundary targets are signed kg/s: one positive inlet, negative outlets.
Caller binds the history and targets to its source model and solver settings.
"""
import math


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Finite numerical value required')
    return value


def assess(rows, targets, inlet, *, window=200, flow_tolerance=.001,
           mass_tolerance=.001, pressure_range_tolerance=.005):
    """Require each flow and global mass check throughout a consecutive window.

    Tolerances are explicit numerical design targets, not regulations.
    Pressure differences cover the complete supplied inlet-to-outlet domain.
    """
    if type(window) is not int or window < 2 or len(rows) < window:
        raise ValueError('Complete multi-iteration window required')
    for value in (flow_tolerance, mass_tolerance, pressure_range_tolerance):
        if not 0 < _number(value) < 1:
            raise ValueError('Relative numerical tolerance must be between zero and one')
    if inlet not in targets or len(targets) < 2:
        raise ValueError('One inlet and at least one outlet required')
    for name, value in targets.items():
        if not isinstance(name, str) or not name:
            raise ValueError('Named boundary required')
        value = _number(value)
        if value * (1 if name == inlet else -1) <= 0:
            raise ValueError('One positive inlet and negative outlet targets required')
    if not math.isclose(math.fsum(targets.values()), 0., rel_tol=0, abs_tol=1e-10*targets[inlet]):
        raise ValueError('Conservative source target mass flows required')
    data = rows[-window:]
    iterations = [_number(row['Inner_Iter']) for row in data]
    if any(int(i) != i for i in iterations) or any(b-a != 1 for a, b in zip(iterations, iterations[1:])):
        raise ValueError('Consecutive saved iteration numbers required')
    flow_errors = {name: [] for name in targets}
    balances = []
    differences = {name: [] for name in targets if name != inlet}
    for row in data:
        mass = {name: _number(row[f'Avg_Massflow({name})']) for name in targets}
        for name, target in targets.items():
            flow_errors[name].append(_number(abs(mass[name]-target)/abs(target)))
        # Normalize against prescribed inlet mass, never a possibly zero or
        # reversed instantaneous inlet. Individual signed flow checks remain.
        balances.append(abs(math.fsum(mass.values()))/targets[inlet])
        pi = _number(row[f'Avg_TotalPress({inlet})'])
        for name in differences:
            differences[name].append(_number(pi-_number(row[f'Avg_TotalPress({name})'])))
    pressures = {}
    for name, values in differences.items():
        mean = math.fsum(values)/window
        spread = max(values)-min(values)
        positive = min(values) > 0
        relative = spread/mean if mean > 0 else None
        pressures[name] = dict(mean_Pa=mean, range_Pa=spread,
                              relative_range=relative, positive=positive,
                              stable=positive and relative <= pressure_range_tolerance)
    flow_pass = all(max(values) <= flow_tolerance for values in flow_errors.values())
    mass_pass = max(balances) <= mass_tolerance
    pressure_pass = all(row['stable'] for row in pressures.values())
    return dict(window_iterations=[int(iterations[0]), int(iterations[-1])],
                maximum_relative_flow_errors={k: max(v) for k, v in flow_errors.items()},
                maximum_relative_mass_imbalance=max(balances), pressures=pressures,
                numerical_targets=dict(flow=flow_tolerance, mass=mass_tolerance,
                                       pressure_range=pressure_range_tolerance),
                flow_pass=flow_pass, mass_pass=mass_pass, pressure_stability_pass=pressure_pass,
                numerical_window_pass=flow_pass and mass_pass and pressure_pass,
                engineering_accepted=False,
                scope='Complete supplied domain; numerical window only. Requires separate model, turbulence, mesh and source applicability verification.')


def main():
    """Assess host-selected saved project history without running a solver."""
    import argparse
    import csv
    import hashlib
    import io
    import json
    from pathlib import Path
    from .workspace import project_root

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', required=True)
    parser.add_argument('--targets', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--window', type=int, default=200)
    args = parser.parse_args()
    root = project_root()
    if root is None:
        raise ValueError('Explicit host BSA_PROJECT_ROOT required')

    def project_path(value):
        path = (root / value).resolve()
        if not path.is_relative_to(root):
            raise ValueError('History, targets and output must remain in host project')
        return path

    history, target_file, output = map(project_path, (args.history, args.targets, args.output))
    if output.exists():
        raise ValueError('Preserve existing evidence: select a new output file')
    before = history.stat()
    data = history.read_bytes()
    after = history.stat()
    if (before.st_size != after.st_size or len(data) != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns):
        raise ValueError('History changed during observation; retry the same run')
    rows = []
    for raw in csv.DictReader(io.StringIO(data.decode('utf-8-sig')), skipinitialspace=True):
        if None in raw or any(value is None for value in raw.values()):
            raise ValueError('Incomplete history row; retry the same run')
        rows.append({key.strip().strip('"'): _number(float(value)) for key, value in raw.items()})
    target_data = target_file.read_bytes()
    basis = json.loads(target_data)
    result = assess(rows, basis['signed_mass_flow_targets_kg_s'], basis['inlet'], window=args.window)
    result['provenance'] = dict(history_sha256=hashlib.sha256(data).hexdigest(),
                                targets_sha256=hashlib.sha256(target_data).hexdigest(),
                                method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(window_iterations=result['window_iterations'],
                          numerical_window_pass=result['numerical_window_pass'],
                          engineering_accepted=False)))


if __name__ == '__main__':
    main()
