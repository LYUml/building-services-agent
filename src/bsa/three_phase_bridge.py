"""Run the verified three-phase adapter in its explicit isolated interpreter."""
import json
import math
from pathlib import Path
import subprocess
from .cli import digest
from .engine import ProjectError
from .three_phase import prepare,ROOT

RUNNER=ROOT/'scripts/run_three_phase.py'
ADAPTER=ROOT/'src/bsa/three_phase.py'
VERSIONS={'pandapower':'3.5.6','numpy':'2.4.6','scipy':'1.18.1','pandas':'2.3.3'}


def inputs(project):
    _,files=prepare(project)
    return files|{RUNNER,ADAPTER,Path(__file__).resolve()}


def run(project,out,python):
    project,out,python=[Path(p).resolve() for p in (project,out,python)]
    p,source_files=prepare(project)
    before={str(f):digest(f) for f in inputs(project)|{python}}
    if any(out==Path(f) or out in Path(f).parents for f in before):raise ProjectError('output must not contain inputs')
    out.mkdir(parents=True,exist_ok=False)
    with (out/'process.log').open('wb') as log:
        proc=subprocess.run([str(python),str(RUNNER),str(project),'--out',str(out/'native')],
            stdout=log,stderr=subprocess.STDOUT,timeout=120)
    study_path=out/'native/study.json';network=out/'native/network.json'
    if not study_path.is_file() or not network.is_file():raise ProjectError('three-phase run produced no verified study; inspect process.log')
    study=json.loads(study_path.read_text(encoding='utf-8'))
    if study.get('versions')!=VERSIONS or study.get('adapter_sha256')!=before[str(ADAPTER)]:raise ProjectError('three-phase runtime/adapter identity differs from verified pins')
    if study.get('inputs')!={str(f):before[str(f)] for f in source_files} or study.get('source_records')!=p['sources'] or study.get('input_unchanged') is not True:
        raise ProjectError('three-phase source identity differs')
    if study.get('network_sha256')!=digest(network) or study.get('design_accepted') is not False:raise ProjectError('three-phase saved artifact/acceptance mismatch')
    checks=study.get('verification_checks')
    residual_names={'max_line_voltage_error_v','max_end_current_error_a','max_current_result_error_a',
        'max_node_kcl_error_a','max_load_power_error_va','max_line_loss_error_va','total_power_balance_error_va'}
    if not isinstance(checks,dict) or set(checks)!=residual_names|{'native_input_correspondence'} or any(type(v) is not bool for v in checks.values()):raise ProjectError('complete three-phase Boolean verification checks required')
    tolerances={key:(1e-3 if key.endswith('_va') else 1e-5) for key in residual_names}
    if study.get('numerical_tolerances')!=tolerances or set(study.get('residuals',{}))!=residual_names:raise ProjectError('three-phase residual/tolerance inventory differs')
    for key in residual_names:
        value=study['residuals'][key]
        if type(value) not in (int,float) or not math.isfinite(value) or value<0 or checks[key] is not (value<tolerances[key]):raise ProjectError('three-phase residual result contradicts checks')
    if not isinstance(study.get('native_input_issues'),list) or checks['native_input_correspondence'] is not (not study['native_input_issues']):raise ProjectError('three-phase native correspondence result contradicts checks')
    if study.get('verification_pass') is not all(checks.values()):raise ProjectError('three-phase verification result contradicts checks')
    if [r['id'] for r in study['nodes']]!=[r['id'] for r in p['buses']] or [r['id'] for r in study['lines']]!=[r['id'] for r in p['lines']]:raise ProjectError('three-phase result inventory differs')
    def vector(row,key):
        values=row[key]
        if not isinstance(values,list) or len(values)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values):raise ProjectError('finite nonnegative phase result vector required')
        return values
    base=p['supply']['line_line_v']/math.sqrt(3)
    for row in study['nodes']:
        target=all(p['voltage_limits']['minimum_pu']<=v/base<=p['voltage_limits']['maximum_pu'] for v in vector(row,'phase_voltage_v'))
        if row['voltage_target_pass'] is not target:raise ProjectError('three-phase voltage target contradicts values')
    for row,line in zip(study['lines'],p['lines']):
        if row['current_target_pass'] is not (max(vector(row,'phase_current_a'))<=line['max_current_a']):raise ProjectError('three-phase current target contradicts values')
    target_checks=[r['voltage_target_pass'] for r in study['nodes']]+[r['current_target_pass'] for r in study['lines']]
    if any(type(v) is not bool for v in target_checks) or study.get('study_targets_pass') is not all(target_checks):raise ProjectError('three-phase target result contradicts checks')
    status='pass' if study['verification_pass'] and study['study_targets_pass'] else 'fail'
    if study.get('status')!=status or proc.returncode!=(0 if status=='pass' else 2):raise ProjectError('three-phase exit/status correspondence failed')
    if any(not Path(f).is_file() or digest(Path(f))!=h for f,h in before.items()):raise ProjectError('three-phase inputs changed during execution')
    result=dict(status=status,inputs=before,runtime=VERSIONS,study_sha256=digest(study_path),network_sha256=digest(network),
        design_accepted=False,scope=study['scope'])
    with (out/'three-phase.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    return result
