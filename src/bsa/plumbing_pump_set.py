"""Evaluate sourced one-duty/one-standby pumps separately; never add capacities."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .plumbing_pump_binding import run as check
from .regulations import source_paths
from .pump import prepare


def inputs(project):
    project = Path(project).resolve()
    data = json.loads(project.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or set(data) != {'version','source','operating_mode','pumps'} or type(data['version']) is not int or data['version'] != 1:
        raise ProjectError('versioned sourced pump-set contract required')
    if not isinstance(data['source'], str) or not data['source'].strip() or data['operating_mode'] != 'one duty and one standby; each evaluated alone':
        raise ProjectError('explicit sourced one-duty/one-standby mode required')
    pumps = data['pumps']
    if not isinstance(pumps, list) or len(pumps) != 2:raise ProjectError('exactly two independently identified pumps required')
    seen = set(); roles = set(); rows = []; files = {project}
    for row in pumps:
        if not isinstance(row, dict) or set(row) != {'id','role','network','curve','source'} or any(not isinstance(v,str) or not v.strip() for v in row.values()):
            raise ProjectError('exact sourced pump identity, role, network and curve required')
        if row['id'] in seen or row['role'] not in ('duty','standby') or row['role'] in roles:
            raise ProjectError('distinct pump IDs and one of each role required')
        seen.add(row['id']); roles.add(row['role']); resolved = dict(row)
        for key in ('network','curve'):
            path = Path(row[key])
            if path.is_absolute():raise ProjectError('relative pump input required')
            path = (project.parent/path).resolve()
            if not path.is_relative_to(project.parent) or not path.is_file():raise ProjectError('pump input missing or escapes set directory')
            resolved[key] = path; files.add(path)
        rows.append(resolved)
    return data, rows, files


def run(project, basis, pack, sources, out):
    project, basis, pack, out = [Path(p).resolve() for p in (project,basis,pack,out)]
    data, rows, files = inputs(project)
    official = source_paths(json.loads(pack.read_text(encoding='utf-8-sig')), sources)
    files.update((basis,pack)); files.update(p for p in official if p.is_file())
    if any(out == p or out in p.parents for p in files | official):raise ProjectError('output must not contain source inputs')
    boundaries = []
    for row in rows:
        network = json.loads(row['network'].read_text(encoding='utf-8-sig'))
        curve = json.loads(row['curve'].read_text(encoding='utf-8-sig'))
        terminal = prepare(network, curve)
        node = next(n for n in network['nodes'] if n['id']==terminal)
        boundaries.append(dict(terminal_id=terminal, elevation_m=node['elevation_m'],
                               required_total_pressure_pa=node['required_total_pressure_pa'],
                               density_kg_m3=network['fluid']['density_kg_m3'],
                               dynamic_viscosity_pa_s=network['fluid']['dynamic_viscosity_pa_s']))
    if boundaries[0] != boundaries[1]:raise ProjectError('pump scenarios must share fluid and receiving-terminal boundary')
    before = {str(p):digest(p) for p in files}
    missing = [str(p) for p in official if not p.is_file()]
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for row in rows:
        role = row['role']; folder = out/role
        try:
            result = check(row['network'],row['curve'],basis,pack,sources,folder)
            record = dict(id=row['id'],role=role,source=row['source'],status=result['status'],
                          hydraulic_checks_pass=result['hydraulic_checks_pass'],
                          supported_checks_pass=result['supported_checks_pass'],report_sha256=digest(folder/'plumbing-pump-checks.json'))
        except (ProjectError, ValueError, OSError) as exc:
            record = dict(id=row['id'],role=role,source=row['source'],status='fail',error=str(exc),
                          hydraulic_checks_pass=False,supported_checks_pass=False)
        results.append(record)
        if any(not Path(p).is_file() or digest(Path(p)) != h for p,h in before.items()):raise ProjectError('pump-set inputs changed')
    if any(Path(p).exists() for p in missing):raise ProjectError('official source availability changed')
    status = 'fail' if any(r['status']=='fail' for r in results) else 'pass' if all(r['status']=='pass' for r in results) else 'pending'
    result = dict(inputs=before,inputs_unchanged=True,missing_sources=missing,source=data['source'],
                  operating_mode=data['operating_mode'],receiving_boundary=boundaries[0],pump_checks=results,status=status,
                  individual_capacity_checks_pass=all(r['hydraulic_checks_pass'] for r in results),
                  design_accepted=False,regulatory_compliance='not_established',
                  scope='Two separate fixed-terminal one-pump operating scenarios; not parallel operation or installed redundancy proof',
                  pending=['physical pump identities, switching/interlocks/isolation and common-cause failures',
                           'route/tank level/suction applicability, IFC and product evidence',
                           'full WSD and engineering acceptance'])
    result['artifacts'] = {p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'pump-set-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('project','basis','pack','sources','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=run(a.project,a.basis,a.pack,a.sources,a.out)
    print(json.dumps({k:r[k] for k in ('status','pump_checks','design_accepted')},indent=2))
    return 0 if r['status']=='pass' else 2


if __name__=='__main__':raise SystemExit(main())
