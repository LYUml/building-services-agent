"""Sourced constant-property thermal transport targets on a fresh circulation run."""
import argparse
import json
import math
from pathlib import Path
from . import epanet
from .cli import digest
from .engine import ProjectError


def validate(basis, project):
    if project['model'] != epanet.CIRCULATION_MODEL:
        raise ProjectError('thermal transport requires explicit circulation mode')
    if not isinstance(basis, dict) or set(basis) != {'sources', 'fluid_applicability', 'targets'}:
        raise ProjectError('exact thermal basis fields required')
    sources = basis['sources']
    if not isinstance(sources, dict) or not sources or any(not isinstance(v, str) or not v.strip() for v in sources.values()):
        raise ProjectError('thermal source descriptions required')
    if basis['fluid_applicability'] not in sources:
        raise ProjectError('source fluid properties and hydraulic-fluid applicability together')
    targets = basis['targets']
    if not isinstance(targets, list) or not targets:
        raise ProjectError('nonempty thermal targets required')
    reservoirs = {r['id'] for r in project['reservoirs']}
    allowed = {r['id'] for r in project['pipes'] if r['from'] not in reservoirs and r['to'] not in reservoirs}
    seen = set()
    units = {'thermal_power': 'kW_thermal', 'density': 'kg/m3', 'specific_heat': 'J/(kg K)', 'temperature_difference': 'K'}
    for row in targets:
        if not isinstance(row, dict) or set(row) != {'link', 'direction', *units}:
            raise ProjectError('exact thermal target fields required')
        if row['link'] not in allowed or row['link'] in seen or row['direction'] not in ('from_to', 'to_from'):
            raise ProjectError('unique non-reference pipe and explicit flow direction required')
        seen.add(row['link'])
        for key, unit in units.items():
            q = row[key]
            if not isinstance(q, dict) or set(q) != {'value', 'unit', 'source'}:
                raise ProjectError('sourced thermal quantity required')
            v = q['value']
            if q['unit'] != unit or q['source'] not in sources or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
                raise ProjectError('positive finite quantity with exact thermal units and source required')
        try:
            required = row['thermal_power']['value'] * 1000 / (row['density']['value'] * row['specific_heat']['value'] * row['temperature_difference']['value'])
        except (OverflowError, ZeroDivisionError):
            raise ProjectError('thermal transport calculation outside numeric range')
        if not math.isfinite(required) or required <= 0:
            raise ProjectError('thermal transport calculation outside numeric range')
    return basis


def evaluate(basis, hydraulic):
    flows = {r['id']: r['flow_m3_s'] for r in hydraulic.get('pipes', [])}
    rows = []
    for t in basis['targets']:
        power, rho, cp, dt = (t[k]['value'] for k in ('thermal_power', 'density', 'specific_heat', 'temperature_difference'))
        required = power * 1000 / (rho * cp * dt)
        flow = flows.get(t['link'])
        directed = None if flow is None else flow * (1 if t['direction'] == 'from_to' else -1)
        passed = directed is not None and math.isfinite(directed) and directed >= required
        rows.append(dict(link=t['link'], required_flow_m3_s=required, directed_flow_m3_s=directed,
                         target_pass=passed, thermal_power_kw=power))
    return dict(targets=rows, hydraulic_checks_pass=hydraulic['calculated_checks_pass'],
                calculated_checks_pass=hydraulic['calculated_checks_pass'] and all(r['target_pass'] for r in rows),
                design_accepted=False, regulatory_compliance='not_established',
                pending=['Source applicability of constant properties and design temperature difference',
                         'Actual heat exchanger capacity, temperatures, controls and thermal losses',
                         'Coverage of all loads, diversity and simultaneous branch duties',
                         'IFC correspondence, regional rules and complete engineering acceptance'])


def run(project, basis, out):
    project, basis, out = Path(project).resolve(), Path(basis).resolve(), Path(out).resolve()
    if any(out == p or out in p.parents for p in (project, basis)):
        raise ProjectError('output must not contain input files')
    hashes = {str(p): digest(p) for p in (project, basis)}
    p = epanet.validate(json.loads(project.read_text(encoding='utf-8-sig')))
    b = validate(json.loads(basis.read_text(encoding='utf-8-sig')), p)
    out.mkdir(parents=True, exist_ok=False)
    (out/'basis-copy.json').write_text(json.dumps(b, indent=2), encoding='utf-8')
    hydraulic = epanet.run(project, out/'hydraulic')
    result = evaluate(b, hydraulic)
    if any(digest(Path(name)) != value for name, value in hashes.items()):
        raise ProjectError('thermal or hydraulic input changed during execution')
    result.update(input_hashes=hashes, hydraulic_report_sha256=digest(out/'hydraulic/water.json'), basis=b)
    (out/'thermal-duty.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project'); parser.add_argument('basis'); parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = run(args.project, args.basis, args.out)
    print(json.dumps(result, indent=2))
    return 0 if result['calculated_checks_pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
