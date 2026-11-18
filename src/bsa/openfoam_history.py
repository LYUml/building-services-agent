"""Thin reader for pinned native surfaceFieldValue output, not a CFD engine.

Scope: steady deltaT=1 cases, phi in m3/s, already verified Pt in Pa.
Caller binds fields, density, weighting and one explicitly selected run segment.
Never merge restart directories or silently trim misaligned observations here.
"""
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path


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


class ProjectEvidence:
    """Read and reconcile one project-local set of saved CFD files."""

    def __init__(self, output_name):
        from .workspace import project_root

        self.root = project_root()
        if self.root is None:
            raise ValueError('Explicit host BSA_PROJECT_ROOT required')
        self.inputs = {}
        self.output_name = output_name
        self.output = self.path(output_name)
        if self.output.exists():
            raise ValueError('Preserve existing evidence: select a new output')

    def path(self, name):
        from .workspace import protected

        if not isinstance(name, str) or not name.strip() or Path(name).is_absolute():
            raise ValueError('Project-relative path required')
        resolved = (self.root / name).resolve()
        if resolved == self.root or not resolved.is_relative_to(self.root):
            raise ValueError('Files must remain inside the host project')
        if protected(resolved):
            raise ValueError('Completed historical project is read-only; select another workspace')
        return resolved

    def read(self, name):
        file = self.path(name)
        before = file.stat()
        data = file.read_bytes()
        after = file.stat()
        if (before.st_size != after.st_size or len(data) != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns):
            raise ValueError('Native input changed; retry the same run')
        fingerprint = hashlib.sha256(data).hexdigest()
        if self.inputs.setdefault(name, (file, fingerprint)) != (file, fingerprint):
            raise ValueError(f'OpenFOAM review input changed: {name}')
        return data, fingerprint

    def save(self, result):
        from .source_refs import file_hash

        for name, (file, fingerprint) in self.inputs.items():
            if self.path(name) != file or not file.is_file() or file_hash(file) != fingerprint:
                raise ValueError(f'OpenFOAM review input changed: {name}')
        if self.path(self.output_name) != self.output:
            raise ValueError('OpenFOAM review output path changed')
        with self.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write('\n')


def review_project(manifest_name, output_name, *, window=200):
    """Review one explicit segment inside the host BSA_PROJECT_ROOT."""
    from . import cfd_convergence

    evidence = ProjectEvidence(output_name)
    read = evidence.read
    data, digest = read(manifest_name)
    manifest = json.loads(data)
    if (manifest['schema'] != 'bsa.openfoam-history.v1'
            or manifest['units'] != {'phi': 'm3/s', 'Pt': 'Pa'}
            or manifest['time_basis'] != 'steady_deltaT_1'):
        raise ValueError('Explicit supported schema, units and steady time basis required')
    expected = manifest.get('expected_window')
    if expected is not None and (
            not isinstance(expected, list) or len(expected) != 2
            or any(type(t) is not int for t in expected)
            or expected[1] - expected[0] + 1 != window):
        raise ValueError('Expected window must match the requested integer-step count')
    targets = manifest['outward_volume_targets_m3_s']
    if set(manifest['patches']) != set(targets):
        raise ValueError('Native patch set must equal source target set')
    if not manifest['basis_files']:
        raise ValueError('Source and observer basis files required')
    basis_hashes = {name: read(file)[1] for name, file in manifest['basis_files'].items()}
    flux, pressure, hashes = {}, {}, {}
    for name, files in manifest['patches'].items():
        for key, column, destination in [('flux', 'sum(phi)', flux),
                                          ('total_pressure', 'average(Pt)', pressure)]:
            data, file_hash = read(files[key])
            destination[name] = read_samples(data.decode('utf-8-sig'), column)
            hashes[f'{name}/{key}'] = file_hash
    rho = manifest['density_kg_m3']
    rows = to_convergence_rows(flux, pressure, rho)
    result = cfd_convergence.assess(
        rows, {name: -rho*q for name, q in targets.items()}, manifest['inlet'], window=window)
    if expected is not None and expected != result['window_iterations']:
        raise ValueError('Native observations do not match the explicitly required window')
    result['complete_200_step_window'] = window >= 200
    result['declared_native_units'] = manifest['units']
    result['scope'] = ('Selected native segment only; caller binds units, density, weighting and '
                       'source applicability. Numerical stability is not engineering acceptance.')
    result['provenance'] = {
        'manifest_sha256': digest, 'native_input_sha256': hashes,
        'basis_file_sha256': basis_hashes,
        'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'assessor_sha256': hashlib.sha256(Path(cfd_convergence.__file__).read_bytes()).hexdigest(),
    }
    evidence.save(result)
    return result


def add_arguments(parser):
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--window', type=int, default=200)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args()
    result = review_project(args.manifest, args.output, window=args.window)
    print(json.dumps({k: result[k] for k in (
        'window_iterations', 'complete_200_step_window', 'numerical_window_pass', 'engineering_accepted')}))


if __name__ == '__main__':
    main()
