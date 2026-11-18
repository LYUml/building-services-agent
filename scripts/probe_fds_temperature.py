"""Replay the pinned NIST FDS temperature-interpolation case on Windows."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile


RELEASE_SHA256 = '302ec837caaea8cb990cece085bee2284a0338d64fac0b77d46749a92ab12dfc'
INPUT_SHA256 = '7262f82edadd529d74150760f61ee7b9b1dd238f6a796d70640439707b9e089f'
CASE = 'devc_interpolation_temperature'
VERSION = 'FDS-6.11.1-0-gff928db-release'
SUCCESS = f'STOP: FDS completed successfully (CHID: {CASE})'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def temperature_errors(path):
    with path.open(newline='', encoding='ascii') as stream:
        units, columns, *rows = csv.reader(stream)
    if units != ['m', 'C', 'C', 'C'] or columns != ['Z', 'TMP-1', 'TMP-2', 'TMP-3'] or len(rows) != 100:
        raise ValueError('Unexpected FDS temperature line table layout')
    maxima = dict.fromkeys(columns[1:], 0.0)
    for index, row in enumerate(rows):
        z, *values = map(float, row)
        if len(values) != 3 or not all(map(math.isfinite, (z, *values))) or abs(z - index / 99) > 1e-7:
            raise ValueError('Invalid FDS line coordinate or temperature record')
        for column, value in zip(columns[1:], values, strict=True):
            maxima[column] = max(maxima[column], abs(value - (20 + 5*z)))
    return maxima


def run(release, source, out):
    if os.name != 'nt':
        raise ValueError('This probe uses the pinned Windows release')
    release, source, out = (path.resolve() for path in (release, source, out))
    if digest(release) != RELEASE_SHA256 or digest(source) != INPUT_SHA256:
        raise ValueError('Unexpected release or input SHA-256')
    out.mkdir(parents=True)
    with ZipFile(release) as archive:
        for entry in archive.namelist():
            if entry.startswith('firemodels/FDS6/bin/'):
                archive.extract(entry, out)
    work = out/'case'
    work.mkdir()
    case_file = work/f'{CASE}.fds'
    shutil.copyfile(source, case_file)
    if digest(case_file) != INPUT_SHA256:
        raise ValueError('Case changed while copying')
    binaries = out/'firemodels/FDS6/bin'
    mpi = binaries/'mpi'
    launcher, engine = mpi/'mpiexec.exe', binaries/'fds.exe'
    env = {**os.environ, 'PATH': os.pathsep.join((str(binaries), str(mpi), os.environ['PATH'])),
           'OMP_NUM_THREADS': '1'}
    log = work/'console.log'
    with log.open('xb') as stream:
        result = subprocess.run([str(launcher), '-localonly', '-n', '1', str(engine), case_file.name],
                                cwd=work, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    native = work/f'{CASE}.out'
    version = work/f'{CASE}_git.txt'
    if (result.returncode != 0 or SUCCESS not in log.read_text(errors='replace').splitlines()
            or SUCCESS not in native.read_text(errors='replace').splitlines()
            or version.read_text().strip() != VERSION):
        raise RuntimeError('FDS did not report successful completion with the pinned engine')
    steps = work/f'{CASE}_steps.csv'
    with steps.open(newline='', encoding='ascii') as stream:
        units, labels, *rows = csv.reader(stream)
    if labels[3] != 'Simulation Time' or units[3] != 's' or float(rows[-1][3]) != 200:
        raise ValueError('FDS output does not establish the expected final simulation time')
    line = work/f'{CASE}_line.csv'
    errors = temperature_errors(line)
    report = dict(engine=VERSION, native_completed=True, final_simulation_s=200,
                  release_sha256=RELEASE_SHA256, input_sha256=INPUT_SHA256,
                  max_abs_error_c=errors, numerical_acceptance='not_established',
                  artifacts_sha256={path.relative_to(out).as_posix(): digest(path)
                                    for path in (launcher, engine, log, native, version, steps, line)})
    (out/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('release', 'source', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.release, args.source, args.out), indent=2))
