"""Bind saved electrical geometry to the existing whole-model clash engine."""
import argparse
import json
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .three_phase import ROOT
from .three_phase_ifc import inputs as geometry_inputs,inspect as inspect_geometry


def inputs(project,ifc,binding,policy):
    from . import clash,solid_clash,contact_clearance
    policy=Path(policy).resolve();clash.validate_policy(json.loads(policy.read_text(encoding='utf-8-sig')))
    return geometry_inputs(project,ifc,binding)|{policy,Path(__file__).resolve(),*(Path(m.__file__).resolve() for m in (clash,solid_clash,contact_clearance))}


def run(project,ifc,binding,policy,out):
    from .clash import run as check_clash
    out=Path(out).resolve();files=inputs(project,ifc,binding,policy)
    if not out.is_relative_to(ROOT) or out.exists() or any(out==p or out in p.parents for p in files):raise ProjectError('new separate repository coordination output required')
    before={str(p):digest(p) for p in files}
    geometry=inspect_geometry(project,ifc,binding)
    clash=check_clash(ifc,policy,out/'clash')
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in before.items()):raise ProjectError('source changed during electrical coordination')
    result=dict(status='pass' if clash['calculated_checks_pass'] else 'fail',inputs=before,input_unchanged=True,
                geometry_correspondence_pass=geometry['geometry_correspondence_pass'],clash_checks=clash['checks'],
                checked_elements=clash['valid_geometry_count'],intersection_pair_count=clash['intersection_pair_count'],
                clearance_violation_pair_count=clash['clearance_violation_pair_count'],design_accepted=False,
                scope='Same saved electrical cable geometry and whole-model represented-element solid intersection/declared clearance checks only; source obstacle completeness, physical joints, product fidelity and full engineering acceptance remain unverified')
    (out/'coordination.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    for key in ('ifc','binding','policy','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.ifc,a.binding,a.policy,a.out)
    print(json.dumps({k:r[k] for k in ('status','clash_checks','design_accepted')}))
    raise SystemExit(0 if r['status']=='pass' else 2)
