"""Admit only verified target failures as pump-search baselines, never as passes."""
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .epanet import CIRCULATION_MODEL, evaluate, validate
from .ifc_circulation_checks import verify_producer

TARGETS = {'pressure_targets', 'delivery_targets', 'velocity_limits'}
NUMERICAL = {'engine_clean', 'serialized_input_match', 'finite_results', 'reservoir_heads',
             'mass_balance', 'head_pressure_identity', 'demand_law', 'pipe_energy',
             'pump_curves', 'zero_reference_exchange', 'positive_circulation'}


def verify_failed_baseline(producer, template, binding):
    producer = Path(producer).resolve()
    geometry = verify_producer(producer, template, binding)
    def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
    report = read(producer/'water-binding.json')
    water = read(producer/'analysis/water.json')
    network = validate(read(producer/'network-input.json'))
    raw_path = producer/'analysis/raw.json'
    if 'analysis/raw.json' not in report['artifacts'] or network['model'] != CIRCULATION_MODEL:
        raise ProjectError('failed baseline requires recorded raw circulation evidence')
    if any(report.get(k) is not True for k in ('inputs_unchanged', 'saved_ifc_match', 'ifc_copy_unchanged')):
        raise ProjectError('failed baseline geometry/source checks are incomplete')
    if report.get('calculated_checks_pass') is not False or water.get('calculated_checks_pass') is not False or water.get('engine_error'):
        raise ProjectError('failed baseline must have a completed failing hydraulic assessment')
    if water.get('input_sha256') != digest(producer/'network-input.json') or water.get('input_unchanged') is not True:
        raise ProjectError('failed baseline hydraulic input differs')
    actual = evaluate(network, read(raw_path))
    checks = actual['checks']
    if checks != water.get('checks') or set(checks) != TARGETS | NUMERICAL or any(type(v) is not bool for v in checks.values()):
        raise ProjectError('failed baseline checks differ from raw result assessment')
    if any(not checks[k] for k in NUMERICAL):
        raise ProjectError('failed baseline numerical/curve checks must pass before iteration')
    failed = sorted(k for k in TARGETS if not checks[k])
    if not failed:raise ProjectError('failed baseline has no supported target failure')
    return dict(geometry=geometry, raw_sha256=digest(raw_path), failed_targets=failed,
                baseline_accepted=False, scope='Verified target failure admitted for pump search only; original task remains failed')
