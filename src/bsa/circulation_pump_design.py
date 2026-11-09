"""Bounded sourced pump catalogue screening against circulation duty and pipe rules."""
import argparse
import copy
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .epanet import validate,CIRCULATION_MODEL
from .circulation_duty import run as duty_run
from .epanet_pipe_regulations import run as rules_run
from .fluid_bindings import density_declarations,check_density_consistency
from .regulations import source_paths

OBJECTIVE='lowest declared preference among passing candidates'


def candidates(project,catalogue):
    validate(project)
    if project['model']!=CIRCULATION_MODEL or len(project['pumps'])!=1:raise ProjectError('single-pump circulation required')
    if not isinstance(catalogue,dict) or set(catalogue)!={'objective','source','candidates'} or catalogue['objective']!=OBJECTIVE or not isinstance(catalogue['source'],str) or not catalogue['source'].strip():raise ProjectError('explicit sourced catalogue preference objective required')
    rows=catalogue['candidates']
    if not isinstance(rows,list) or not 1<=len(rows)<=100:raise ProjectError('bounded catalogue of 1 to 100 candidates required')
    seen=set();result=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'id','source','preference','head_curve'}:raise ProjectError('exact pump candidate fields required')
        if not isinstance(row['id'],str) or not row['id'].strip() or row['id'] in seen:raise ProjectError('unique candidate identifiers required')
        seen.add(row['id'])
        if not isinstance(row['source'],str) or not row['source'].strip() or type(row['preference']) not in (int,float) or not math.isfinite(row['preference']):raise ProjectError('sourced candidate and finite preference required')
        p=copy.deepcopy(project);source='candidate:'+row['id']
        if source in p['sources']:raise ProjectError('candidate source key collision')
        p['sources'][source]=row['source'];p['pumps'][0].update(head_curve=copy.deepcopy(row['head_curve']),source=source)
        validate(p);result.append((row,p))
    return result


def run(project,catalogue,thermal_basis,rule_basis,pack,sources,out):
    paths=[Path(p).resolve() for p in (project,catalogue,thermal_basis,rule_basis,pack)];out=Path(out).resolve()
    inputs={str(p):digest(p) for p in paths};p,c,_,_,rules=[json.loads(f.read_text(encoding='utf-8-sig')) for f in paths]
    options=candidates(p,c)
    official=source_paths(rules,sources)
    if any(not f.is_file() for f in official):raise ProjectError('official rule sources required before candidate screening')
    inputs.update({str(f):digest(f) for f in official})
    if any(out==Path(f) or out in Path(f).parents for f in inputs):raise ProjectError('output must not contain inputs')
    declarations=[]
    for kind,path in [('circulation_duty',paths[2]),('epanet_pipe_regulations',paths[3])]:declarations.extend(density_declarations(dict(id=kind,kind=kind),path))
    check_density_consistency(declarations)
    out.mkdir(parents=True,exist_ok=False)
    def unchanged():
        if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in inputs.items()):raise ProjectError('pump screening inputs changed')
    def trial(network,folder):
        unchanged();folder.mkdir();file=folder/'project.json';file.write_text(json.dumps(network,indent=2),encoding='utf-8')
        thermal=duty_run(file,paths[2],folder/'thermal');regulatory=rules_run(file,paths[3],paths[4],sources,folder/'rules')
        unchanged()
        return dict(pass_checks=thermal['calculated_checks_pass'] and regulatory['status']=='pass',
                    thermal_checks_pass=thermal['calculated_checks_pass'],hydraulic_checks_pass=regulatory['hydraulic_checks_pass'],pipe_rules_status=regulatory['status'],
                    network_sha256=digest(file),thermal_report_sha256=digest(folder/'thermal/thermal-duty.json'),rule_report_sha256=digest(folder/'rules/water-pipe-checks.json'))
    baseline=trial(p,out/'baseline')
    records=[]
    for i,(row,network) in enumerate(options):
        record=dict(id=row['id'],preference=row['preference'],source=row['source'],directory=f'candidate-{i:03d}')
        record.update(trial(network,out/record['directory']));records.append(record)
    passing=[(record,network) for record,(_,network) in zip(records,options) if record['pass_checks']]
    passing.sort(key=lambda pair:(pair[0]['preference'],pair[0]['id']))
    selected=None
    if passing:
        record,network=passing[0];rerun=trial(network,out/'selected')
        selected=dict(id=record['id'],preference=record['preference'],rerun=rerun)
        if rerun['network_sha256']!=record['network_sha256']:raise ProjectError('selected network differs from candidate')
    unchanged()
    result=dict(inputs=inputs,objective=c['objective'],objective_source=c['source'],baseline=baseline,candidates=records,selected=selected,
                feasible_candidate_found=selected is not None,selected_rerun_pass=bool(selected and selected['rerun']['pass_checks']),design_accepted=False,regulatory_compliance='not_established',
                pending=['real pump data, speed, efficiency, motor and NPSH applicability','IFC equipment/curve correspondence and physical coordination','complete load/regulatory coverage and engineering acceptance'])
    result['artifacts']={f.relative_to(out).as_posix():digest(f) for f in out.rglob('*') if f.is_file()}
    (out/'pump-screening.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('project','catalogue','thermal-basis','rule-basis','pack','sources','out'):parser.add_argument('--'+name,required=True,type=Path)
    a=parser.parse_args();r=run(a.project,a.catalogue,a.thermal_basis,a.rule_basis,a.pack,a.sources,a.out)
    print(json.dumps({k:r[k] for k in ('feasible_candidate_found','selected','selected_rerun_pass','design_accepted')},indent=2))
    return 0 if r['selected_rerun_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
