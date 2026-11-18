"""Replay the pinned NIST FDS temperature-interpolation case on Windows."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile
from .source_refs import file_hash as digest
from . import workspace
from .engine import ProjectError


RELEASE_SHA256 = '302ec837caaea8cb990cece085bee2284a0338d64fac0b77d46749a92ab12dfc'
INPUT_SHA256 = '7262f82edadd529d74150760f61ee7b9b1dd238f6a796d70640439707b9e089f'
CASE = 'devc_interpolation_temperature'
VERSION = 'FDS-6.11.1-0-gff928db-release'
SUCCESS = f'STOP: FDS completed successfully (CHID: {CASE})'
CONSOLE_STEP = re.compile(r'^\s*Time Step:\s*(\d+), Simulation Time:\s*([\d.]+) s\s*$', re.M)
ENGINE = 'firemodels/FDS6/bin/fds.exe'
LAUNCHER = 'firemodels/FDS6/bin/mpi/mpiexec.exe'
RUNTIME_HASHES = {
    ENGINE: '1dd7468130e403f18b9a45ec5134662fe9738ea6a12b0f600c5f91c16428312f',
    LAUNCHER: '3af7741d27090c13a150ff575dc216c268b06a174d0770fc07d9e6756db0dc92',
}


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


def inspect_steps(path, console):
    with path.open(newline='', encoding='ascii') as stream:
        reader = csv.reader(stream)
        if (next(reader, None) != ['', '', 's', 's', 's']
                or next(reader, None) != ['Time Step', 'Wall Time', 'Step Size', 'Simulation Time', 'CPU Time']):
            raise ValueError('Unexpected FDS time-step table layout')
        previous_index, previous_time = 0, 0.0
        samples = []
        for row in reader:
            if len(row) != 5:
                raise ValueError('Incomplete FDS time-step record')
            index = int(row[0])
            step, time, cpu = map(float, row[2:])
            if (index <= previous_index or time <= previous_time or step <= 0 or cpu < 0
                    or not all(map(math.isfinite, (step, time, cpu)))):
                raise ValueError('Invalid FDS time-step progression')
            samples.append((index, time))
            previous_index, previous_time = index, time
    logged = [(int(index), float(time)) for index, time in CONSOLE_STEP.findall(console)]
    if len(samples) < 2 or samples[0][0] != 1 or samples[-1][1] != 200 or samples != logged:
        raise ValueError('FDS time-step table and console progression do not reconcile')
    return dict(report_samples=len(samples), final_step=samples[-1][0], final_simulation_s=samples[-1][1])


def run(release, source, out):
    if os.name != 'nt':
        raise ValueError('This probe uses the pinned Windows release')
    release, source, out = (Path(path).resolve() for path in (release, source, out))
    if not workspace.allowed(source) or not workspace.intake_output(out):
        raise ValueError('Use a permitted FDS input and output workspace')
    if digest(source) != INPUT_SHA256:
        raise ValueError('Unexpected FDS input SHA-256')
    with release.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != RELEASE_SHA256:
            raise ValueError('Unexpected FDS release SHA-256')
        out.mkdir(parents=True)
        with ZipFile(stream) as archive:
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
    launcher, engine = out/LAUNCHER, out/ENGINE
    env = {**os.environ, 'PATH': os.pathsep.join((str(binaries), str(mpi), os.environ['PATH'])),
           'OMP_NUM_THREADS': '1'}
    log = work/'console.log'
    try:
        with log.open('xb') as stream:
            result = subprocess.run([str(launcher), '-localonly', '-n', '1', str(engine), case_file.name],
                                    cwd=work, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise ProjectError('FDS probe timed out; see the retained console log') from exc
    if result.returncode != 0:
        raise ProjectError('FDS launcher failed; see the retained console log')
    report = inspect_outputs(out)
    (out/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def inspect_outputs(out):
    log = 'case/console.log'
    native = f'case/{CASE}.out'
    version = f'case/{CASE}_git.txt'
    steps = f'case/{CASE}_steps.csv'
    line = f'case/{CASE}_line.csv'
    source = f'case/{CASE}.fds'
    artifacts = (LAUNCHER, ENGINE, log, native, version, steps, line)
    paths = {name: (out/name).resolve() for name in (*artifacts, source)}
    if any(not path.is_relative_to(out) or not path.is_file() for path in paths.values()):
        raise ProjectError('Missing FDS evidence or artifact path escapes the run')
    before = {name: digest(path) for name, path in paths.items()}
    if before[source] != INPUT_SHA256 or any(before[name] != sha for name, sha in RUNTIME_HASHES.items()):
        raise ProjectError('FDS saved input or runtime differs from the pinned release')
    log, native, version, steps, line = (paths[name] for name in (log, native, version, steps, line))
    console = log.read_text(errors='replace')
    if (SUCCESS not in console.splitlines()
            or SUCCESS not in native.read_text(errors='replace').splitlines()
            or version.read_text().strip() != VERSION):
        raise ProjectError('FDS did not report successful completion with the pinned engine')
    progression = inspect_steps(steps, console)
    errors = temperature_errors(line)
    if any(digest(path) != before[name] for name, path in paths.items()):
        raise ProjectError('FDS evidence changed during inspection')
    return dict(engine=VERSION, native_completed=True, final_simulation_s=progression['final_simulation_s'],
                time_step_progression=progression, release_sha256=RELEASE_SHA256, input_sha256=INPUT_SHA256,
                max_abs_error_c=errors, numerical_acceptance='not_established',
                artifacts_sha256={name: before[name] for name in artifacts})


def verify(out):
    out = Path(out).resolve()
    report_path = (out/'report.json').resolve()
    if not workspace.allowed(out) or not report_path.is_relative_to(out):
        raise ProjectError('Use a saved FDS run in the permitted workspace')
    raw = report_path.read_bytes()
    saved = json.loads(raw)
    reconstructed = inspect_outputs(out)
    expected = reconstructed.copy()
    if isinstance(saved, dict) and 'time_step_progression' not in saved:
        del expected['time_step_progression']
    if expected != saved or report_path.read_bytes() != raw:
        raise ProjectError('Saved FDS report differs from reconstructed evidence')
    return dict(integrity_pass=True, **reconstructed)


def add_arguments(parser):
    for name in ('release', 'source', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args()
    print(json.dumps(run(args.release, args.source, args.out), indent=2))


if __name__ == '__main__':
    main()
