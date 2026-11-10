"""Evaluate a hash-pinned upstream wheel without installing or adopting its tables."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WHEEL_SHA256 = '87a469dc3dd954c44da9f6b0e76ce5fffd5da8782de0490578ef8b88b402b82b'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(wheel, out):
    wheel, out = Path(wheel).resolve(), Path(out).resolve()
    if not wheel.is_relative_to(ROOT) or not out.is_relative_to(ROOT) or out.exists() or wheel.is_relative_to(out):
        raise ValueError('Repository-local pinned wheel and new separate output required')
    if digest(wheel) != WHEEL_SHA256:
        raise ValueError('Only reviewed hvac-pressure0.1.1 wheel is permitted')
    with zipfile.ZipFile(wheel) as archive:
        pins = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()
            if name.endswith('.py') or name.endswith('/LICENSE')}
    sys.path.insert(0, str(wheel))
    import hvac_pressure as hp
    from hvac_pressure.data.ashrae_tables import get_fitting
    if not str(hp.__file__).startswith(str(wheel)):
        raise ValueError('Probe imported a different upstream package')
    def transition(area, angle):
        return hp.fitting_loss('SR4-1', flow_m3s=.2, width_m=.5, height_m=.4,
            Ao_over_A1=area, theta_deg=angle)
    edge = transition(2, 180); outside = transition(2, 181)
    edge_area = transition(.1, 30); outside_area = transition(.05, 30)
    tee = get_fitting('SR5-1'); taper = get_fitting('SR4-1')
    observations = dict(
        out_of_range_angle_returns_boundary_coefficient=edge['C'] == outside['C'],
        out_of_range_angle_has_no_warning=not outside['warnings'],
        out_of_range_area_returns_boundary_coefficient=edge_area['C'] == outside_area['C'],
        out_of_range_area_has_no_warning=not outside_area['warnings'],
        tee_metadata_requires_radius_ratio='r/Wb = 1.0' in tee['notes'],
        transition_metadata_requires_two_parallel_sides='Two Sides Parallel' in taper['description'],
        upstream_returns_both_tee_paths=all(k in hp.fitting_loss('SR5-1', flow_m3s=.2,
            width_m=.5, height_m=.4, As_over_Ac=1., Ab_over_Ac=1., Qb_over_Qc=.5)
            for k in ('C', 'C2', 'delta_p_pa', 'delta_p2_pa')))
    if digest(wheel) != WHEEL_SHA256: raise ValueError('Upstream wheel changed during probe')
    result = dict(upstream='https://github.com/JeremySimonneau/hvac-fitting-loss', version='0.1.1',
        wheel_sha256=WHEEL_SHA256, package_file_hashes=pins, probe_sha256=digest(Path(__file__)),
        observations=observations, probe_completed=True, production_adapter=False, design_accepted=False,
        decision='Not adopted for current sharp rectangular tees and two-dimension-changing tapers. Domain guards, independent source/edition/reference-pressure validation and table redistribution review remain required. Probe does not validate coefficient accuracy.')
    out.mkdir(parents=True)
    (out/'probe.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel'); parser.add_argument('--out', required=True)
    args = parser.parse_args(); result = run(args.wheel, args.out)
    print(json.dumps(result['observations'], indent=2))
