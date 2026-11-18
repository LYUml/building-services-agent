"""Run or verify pinned FDS temperature checks on Windows."""
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
UNIFORM_CASE = 'uniform_temperature'
UNIFORM_SHA256 = 'd49229d3ba17066b026c5a15d00bb10cd7567275ed0b6ce8755626a5b33f3fe1'
INPUTS = {CASE: INPUT_SHA256, UNIFORM_CASE: UNIFORM_SHA256}
VERSION = 'FDS-6.11.1-0-gff928db-release'
SUCCESS = f'STOP: FDS completed successfully (CHID: {CASE})'
CONSOLE_STEP = re.compile(r'^\s*Time Step:\s*(\d+), Simulation Time:\s*([\d.]+) s\s*$', re.M)
ENGINE = 'firemodels/FDS6/bin/fds.exe'
LAUNCHER = 'firemodels/FDS6/bin/mpi/mpiexec.exe'
RUNTIME_HASHES = {
    ENGINE: '1dd7468130e403f18b9a45ec5134662fe9738ea6a12b0f600c5f91c16428312f',
    LAUNCHER: '3af7741d27090c13a150ff575dc216c268b06a174d0770fc07d9e6756db0dc92',
}
MISSING_RELEASE = 'Host FDS release not supplied; temperature probe not executed'
UNPINNED_INPUT = 'Unexpected FDS input SHA-256'


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


def point_temperature_errors(path):
    with path.open(newline='', encoding='ascii') as stream:
        units, columns, *rows = csv.reader(stream)
    if units != ['s', 'C', 'C'] or columns != ['Time', 'center', 'off_center'] or len(rows) != 6:
        raise ValueError('Unexpected FDS point temperature table layout')
    maxima = dict.fromkeys(columns[1:], 0.0)
    for row, expected_time in zip(rows, (0, 0.2, 0.45, 0.65, 0.8, 1), strict=True):
        time, center, off_center = map(float, row)
        if time != expected_time or not all(map(math.isfinite, (center, off_center))):
            raise ValueError('Invalid FDS point temperature sample')
        for column, value in zip(columns[1:], (center, off_center), strict=True):
            maxima[column] = max(maxima[column], abs(value - 22.5))
    return maxima


def inspect_steps(path, console, *, final_time=200):
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
    if len(samples) < 2 or samples[0][0] != 1 or samples[-1][1] != final_time or samples != logged:
        raise ValueError('FDS time-step table and console progression do not reconcile')
    return dict(report_samples=len(samples), final_step=samples[-1][0], final_simulation_s=samples[-1][1])


def run(release, source, out):
    if os.name != 'nt':
        raise ValueError('This probe uses the pinned Windows release')
    release, source, out = (Path(path).resolve() for path in (release, source, out))
    if not workspace.allowed(source) or not workspace.intake_output(out):
        raise ValueError('Use a permitted FDS input and output workspace')
    source_hash = digest(source)
    case = next((name for name, sha in INPUTS.items() if sha == source_hash), None)
    if case is None:
        raise ValueError(UNPINNED_INPUT)
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
    case_file = work/f'{case}.fds'
    shutil.copyfile(source, case_file)
    if digest(case_file) != source_hash:
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
    report = inspect_outputs(out, case)
    (out/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def output_paths(out, case):
    if not isinstance(case, str) or case not in INPUTS:
        raise ProjectError('Unsupported saved FDS probe case')
    names = (LAUNCHER, ENGINE, 'case/console.log', f'case/{case}.out',
             f'case/{case}_git.txt', f'case/{case}_steps.csv',
             f"case/{case}_{'devc' if case == UNIFORM_CASE else 'line'}.csv", f'case/{case}.fds')
    paths = {name: (out/name).resolve() for name in names}
    if any(not path.is_relative_to(out) or not path.is_file() for path in paths.values()):
        raise ProjectError('Missing FDS evidence or artifact path escapes the run')
    return paths


def inspect_outputs(out, case=CASE):
    paths = output_paths(out, case)
    _, _, log, native, version, steps, table, source = paths
    uniform = case == UNIFORM_CASE
    before = {name: digest(path) for name, path in paths.items()}
    if before[source] != INPUTS[case] or any(before[name] != sha for name, sha in RUNTIME_HASHES.items()):
        raise ProjectError('FDS saved input or runtime differs from the pinned release')
    log, native, version, steps, table = (paths[name] for name in (log, native, version, steps, table))
    console = log.read_text(errors='replace')
    success = f'STOP: FDS completed successfully (CHID: {case})'
    if (success not in console.splitlines()
            or success not in native.read_text(errors='replace').splitlines()
            or version.read_text().strip() != VERSION):
        raise ProjectError('FDS did not report successful completion with the pinned engine')
    progression = inspect_steps(steps, console, final_time=1 if uniform else 200)
    errors = point_temperature_errors(table) if uniform else temperature_errors(table)
    if any(digest(path) != before[name] for name, path in paths.items()):
        raise ProjectError('FDS evidence changed during inspection')
    report = dict(engine=VERSION, native_completed=True, final_simulation_s=progression['final_simulation_s'],
                  time_step_progression=progression, release_sha256=RELEASE_SHA256, input_sha256=INPUTS[case],
                  max_abs_error_c=errors, numerical_acceptance='not_established',
                  artifacts_sha256={name: sha for name, sha in before.items() if name != source})
    if uniform:
        report.update(case=case, expected_temperature_c=22.5, point_temperature_check_pass=not any(errors.values()))
    return report


def saved_report(out):
    out = Path(out).resolve()
    report_path = (out/'report.json').resolve()
    if not workspace.allowed(out) or not report_path.is_relative_to(out):
        raise ProjectError('Use a saved FDS run in the permitted workspace')
    raw = report_path.read_bytes()
    saved = json.loads(raw)
    if not isinstance(saved, dict):
        raise ProjectError('Invalid saved FDS report')
    return out, report_path, raw, saved


def evidence_paths(out):
    out, report_path, _, saved = saved_report(out)
    return (report_path, *output_paths(out, saved.get('case', CASE)).values())


def verify(out):
    out, report_path, raw, saved = saved_report(out)
    reconstructed = inspect_outputs(out, saved.get('case', CASE))
    expected = reconstructed.copy()
    if 'case' not in saved and 'time_step_progression' not in saved:
        del expected['time_step_progression']
    if expected != saved or report_path.read_bytes() != raw:
        raise ProjectError('Saved FDS report differs from reconstructed evidence')
    return dict(integrity_pass=True, **reconstructed)


def review_status(report, check):
    if check is None:
        return 'pending', 'FDS probe evidence reconciles; project CFD acceptance remains pending'
    if report.get('case') != UNIFORM_CASE:
        return 'fail', 'Uniform-point acceptance requires the pinned uniform FDS case'
    status = 'pass' if report['point_temperature_check_pass'] else 'fail'
    return status, 'Uniform FDS point temperature check against 22.5 °C at exported precision'


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
