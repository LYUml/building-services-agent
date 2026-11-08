"""Recalculate circular-tree hydraulics and bind per-segment HVAC rule checks."""
import argparse
import copy
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network import run as run_network
from .regulations import evaluate,source_paths


def run(project,basis,pack,sources,out):
    files=[Path(p).resolve() for p in (project,basis,pack)];out=Path(out).resolve()
    before={str(p):digest(p) for p in files}
    network,bases,rules=[json.loads(p.read_text(encoding='utf-8-sig')) for p in files]
    official=source_paths(rules,sources)
    if any(out==p or out in p.parents for p in set(files)|official):raise ProjectError('output must not contain inputs')
    cached={str(p):digest(p) if p.is_file() else None for p in official}
    segments={s['id']:s for s in network['segments']}
    if not isinstance(bases,dict) or set(bases)!=set(segments):raise ProjectError('exact per-segment regulatory basis coverage required')
    for b in bases.values():
        if not isinstance(b,dict):raise ProjectError('per-segment basis must be an object')
        conditions=b.get('water_pipe',{})
        if not isinstance(conditions,dict) or any(k in conditions for k in ('velocity','linear_friction')):
            raise ProjectError('computed pipe velocity/friction cannot be overridden')
    out.mkdir(parents=True,exist_ok=False)
    hydraulic=run_network(files[0],out/'network')
    report=out/'network/network.json'
    checks={};projects={}
    origin='Fresh network '+str(files[0])+' SHA256 '+before[str(files[0])]
    for row in hydraulic['segments']:
        id=row['id'];p=copy.deepcopy(bases[id]);conditions=p.setdefault('water_pipe',{})
        conditions['velocity']=dict(value=row['velocity_m_s'],unit='m/s',source=origin)
        conditions['linear_friction']=dict(value=row['friction_pa']/segments[id]['length_m'],unit='Pa/m',source=origin+'; distributed Darcy loss only, excluding fittings and elevation')
        checks[id]=evaluate(rules,p,sources);projects[id]=p
    if any(digest(Path(p))!=h for p,h in before.items()) or any((digest(Path(p)) if Path(p).is_file() else None)!=h for p,h in cached.items()):raise ProjectError('pipe rule inputs changed')
    before.update({p:h for p,h in cached.items() if h is not None})
    passed=all(c['supported_checks_pass'] for c in checks.values())
    result=dict(inputs=before,inputs_unchanged=True,network_report_sha256=digest(report),missing_sources=[p for p,h in cached.items() if h is None],segment_checks=checks,
                supported_checks_pass=passed,hydraulic_checks_pass=hydraulic['calculated_checks_pass'],
                status='fail' if not hydraulic['calculated_checks_pass'] else 'pass' if passed else 'pending',
                design_accepted=False,regulatory_compliance='not_established',
                scope='Fresh prescribed-flow circular-tree velocities and distributed friction; sourced code-diameter and flow/control classification; complete HVAC compliance not established')
    (out/'bound-pipe-projects.json').write_text(json.dumps(projects,indent=2),encoding='utf-8')
    (out/'water-pipe-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    for name in ('basis','pack','sources','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.basis,a.pack,a.sources,a.out)
    print(json.dumps({'status':r['status'],'supported_checks_pass':r['supported_checks_pass']}))
    return 0 if r['status']=='pass' else 2


if __name__=='__main__':raise SystemExit(main())
