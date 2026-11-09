"""Bind a fresh single-line pump operating point to scoped WSD capacity checks."""
import argparse
import copy
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .pump import prepare, run as pump_run
from .regulations import evaluate, source_paths


def run(project, curve, basis, pack, sources, out):
    files = [Path(p).resolve() for p in (project, curve, basis, pack)]
    out = Path(out).resolve()
    hashes = {str(p): digest(p) for p in files}
    network, pump, contract, rules = [json.loads(p.read_text(encoding='utf-8-sig')) for p in files]
    terminal = prepare(network, pump)
    if not isinstance(contract, dict) or set(contract) != {'regulatory_basis', 'connection'}:
        raise ProjectError('regulatory_basis and explicit tank connection required')
    connection = contract['connection']
    keys = {'terminal_id', 'tank_id', 'capacity_mode', 'hydraulic_boundary_basis', 'source'}
    if not isinstance(connection, dict) or set(connection) != keys or any(not isinstance(v, str) or not v.strip() for v in connection.values()):
        raise ProjectError('exact sourced tank connection and boundary required')
    if connection['terminal_id'] != terminal or connection['capacity_mode'] != 'one operating pump; standby capacity excluded':
        raise ProjectError('single-terminal one-pump capacity contract required')
    facts = copy.deepcopy(contract['regulatory_basis'])
    if not isinstance(facts, dict) or not isinstance(facts.get('sump_pump'), dict):
        raise ProjectError('sump_pump regulatory basis required')
    conditions = facts['sump_pump']
    if any(k in conditions for k in ('available_pumping_capacity', 'capacity_duty_basis')):
        raise ProjectError('computed capacity/duty basis cannot be overridden')
    if conditions.get('tank_identity', {}).get('value') != connection['tank_id']:
        raise ProjectError('tank identity differs from hydraulic connection')
    target = conditions.get('tank_design_outflow', {})
    terminal_row = next(n for n in network['nodes'] if n['id'] == terminal)
    if type(target.get('value')) not in (int, float) or target['value'] <= 0 or target.get('unit') != 'm3/s' or target['value'] != terminal_row['demand_m3_s']:
        raise ProjectError('tank design outflow must equal sourced terminal design demand in m3/s')
    if len(rules.get('rules', [])) != 1 or rules['rules'][0].get('method') != 'wsd_sump_pump':
        raise ProjectError('single scoped WSD sump-pump rule required')
    official = source_paths(rules, sources)
    if any(out == p or out in p.parents for p in set(files) | official):raise ProjectError('output must not contain inputs')
    cached = {str(p): digest(p) if p.is_file() else None for p in official}
    out.mkdir(parents=True, exist_ok=False)
    hydraulic = pump_run(files[0], files[1], out/'pump')
    report_hash = digest(out/'pump/pump.json')
    result = None
    point = hydraulic.get('operating_point')
    if hydraulic.get('status') == 'converged' and point is not None:
        origin = 'Fresh bsa.pump lower-bracket operating flow; pump report SHA256 '+report_hash
        conditions['available_pumping_capacity'] = dict(value=point['flow_m3_s'], unit='m3/s', source=origin)
        conditions['capacity_duty_basis'] = dict(value=connection['hydraulic_boundary_basis'], source=origin+'; '+connection['source'])
        result = evaluate(rules, facts, sources)
        (out/'bound-facts.json').write_text(json.dumps(facts, indent=2), encoding='utf-8')
    if any(digest(Path(p)) != h for p, h in hashes.items()) or any((digest(Path(p)) if Path(p).is_file() else None) != h for p, h in cached.items()):
        raise ProjectError('plumbing pump inputs changed during calculation')
    hashes.update({p:h for p,h in cached.items() if h is not None})
    passed = bool(result and result['supported_checks_pass'])
    output = dict(inputs=hashes, inputs_unchanged=True, connection=connection,
                  missing_sources=[p for p,h in cached.items() if h is None],
                  pump_report_sha256=report_hash, capacity_origin='fresh_single_line_operating_point_lower_bracket' if result else 'unavailable',
                  regulatory_checks=result, supported_checks_pass=passed,
                  hydraulic_checks_pass=hydraulic['calculated_checks_pass'],
                  status='fail' if not hydraulic['calculated_checks_pass'] else 'pass' if passed else 'pending',
                  design_accepted=False, regulatory_compliance='not_established',
                  pending=['duplicate/standby configuration and controls are sourced assertions only',
                           'actual suction, tank level range, products and IFC correspondence',
                           'tank outflow derivation and complete plumbing acceptance'])
    output['artifacts'] = {p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'plumbing-pump-checks.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'curve', 'basis', 'pack', 'sources', 'out'):parser.add_argument('--'+name, required=True)
    a = parser.parse_args(); r = run(a.project, a.curve, a.basis, a.pack, a.sources, a.out)
    print(json.dumps({k:r[k] for k in ('status', 'hydraulic_checks_pass', 'supported_checks_pass', 'design_accepted')}))
    return 0 if r['status'] == 'pass' else 2


if __name__ == '__main__':raise SystemExit(main())
