"""Source-bounded tee bore catalogue screening with retained native trials."""
import argparse
import json
import math
import re
from pathlib import Path
from .cli import digest
from .tee_assembly import run as assemble
from .tee_split import run as split

OBJECTIVE='lowest declared preference among passing candidates'


def prepare(path):
    path=Path(path).resolve();data=json.loads(path.read_text(encoding='utf-8-sig'));files={path};prepared=[];ids=set();common=None
    if set(data)!={'source','objective','candidates'} or not isinstance(data['source'],str) or not data['source'].strip() or data['objective']!=OBJECTIVE or not isinstance(data['candidates'],list) or not data['candidates']:raise ValueError('sourced nonempty catalogue and explicit preference objective required')
    for row in data['candidates']:
        if set(row)!={'id','source','preference','tee_spec','assembly_spec','basis','control'} or not isinstance(row['id'],str) or not re.fullmatch('[A-Za-z0-9_-]+',row['id']) or row['id'] in ids:raise ValueError('unique path-safe candidate IDs and exact source fields required')
        if not isinstance(row['source'],str) or not row['source'].strip() or type(row['preference']) not in (int,float) or not math.isfinite(row['preference']) or row['preference']<0:raise ValueError('candidate source and nonnegative preference required')
        ids.add(row['id']);paths=[]
        for key in ('tee_spec','assembly_spec','basis','control'):
            value=row[key]
            if not isinstance(value,str) or Path(value).is_absolute():raise ValueError('relative candidate source files required')
            p=(path.parent/value).resolve()
            if not p.is_relative_to(path.parent) or not p.is_file():raise ValueError('candidate source escapes catalogue or missing')
            files.add(p);paths.append(p)
        spec,assembly,basis,control=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
        # Compare duty and geometry invariants; only bore/OD and associated loss data may change.
        invariant=dict(spec={k:v for k,v in spec.items() if k not in ('source','outer_radius_m','inner_radius_m')},lengths=assembly['pipe_lengths_m'],basis={k:v for k,v in basis.items() if k not in ('source','fluid_source','coefficient_source','k_run','k_branch')},total_flow=control['total_flow_m3_s'],pressure_tolerance=control['pressure_tolerance_pa'],ratio_tolerance=control['ratio_tolerance'])
        if common is None:common=invariant
        elif common!=invariant:raise ValueError('candidate changes common duty, placement, topology or solver acceptance')
        prepared.append((row,paths))
    return data,prepared,files


def selected_paths(producer,catalogue):
    """Verify retained selection/source bytes and resolve the selected native model."""
    producer=Path(producer).resolve();catalogue=Path(catalogue).resolve()
    data,candidates,files=prepare(catalogue)
    report=json.loads((producer/'tee-selection.json').read_text(encoding='utf-8-sig'))
    if report.get('catalogue')!=data or report.get('inputs')!={str(p):digest(p) for p in files}:raise ValueError('selection source correspondence failed')
    if not report.get('calculated_checks_pass') or not report.get('selected_rerun_pass'):raise ValueError('no verified selected candidate')
    artifacts=report.get('artifacts',{})
    required={'selected/assembly/assembly.ifc','selected/assembly/assembly-checks.json','selected/split/tee-split.json'}
    actual={p.relative_to(producer).as_posix() for p in producer.rglob('*') if p.is_file()}-{'tee-selection.json'}
    if set(artifacts)!=actual or not required<=set(artifacts):raise ValueError('selection artifact coverage failed')
    for name,sha in artifacts.items():
        path=(producer/name).resolve()
        if not path.is_relative_to(producer) or not path.is_file() or digest(path)!=sha:raise ValueError('selection artifact changed')
    trials=report.get('trials',[])
    if [t['id'] for t in trials]!=[r['id'] for r,_ in candidates]:raise ValueError('candidate trial coverage failed')
    for trial,(row,_) in zip(trials,candidates):
        if trial['preference']!=row['preference'] or trial['source']!=row['source']:raise ValueError('candidate ranking correspondence failed')
    passing=[t for t in trials if t['passed']]
    if not passing or min(passing,key=lambda t:(t['preference'],t['id']))['id']!=report['selected']:raise ValueError('selected preference mismatch')
    row,paths=next((r,p) for r,p in candidates if r['id']==report['selected'])
    model=producer/'selected/assembly/assembly.ifc'
    split_report=json.loads((producer/'selected/split/tee-split.json').read_text())
    expected={str(p):digest(p) for p in [model,*paths]}
    if split_report.get('inputs')!=expected or not split_report.get('calculated_checks_pass'):raise ValueError('selected split source/pass mismatch')
    from .tee_assembly import verify
    spec,assembly=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths[:2]]
    if not verify(model,spec,assembly['pipe_lengths_m'])['assembly_checks_pass']:raise ValueError('selected native geometry mismatch')
    return model,paths[0],paths[1]


def run(catalogue,out):
    catalogue,out=Path(catalogue).resolve(),Path(out).resolve();data,candidates,files=prepare(catalogue)
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out==p or out in p.parents for p in files):raise ValueError('new repository output required')
    before={str(p):digest(p) for p in files};out.mkdir(parents=True);trials=[]
    def execute(row,paths,folder):
        if any(digest(p)!=before[str(p)] for p in files):raise ValueError('catalogue input changed')
        spec,assembly,basis,control=paths
        geometry=assemble(spec,assembly,folder/'assembly')
        if not geometry['assembly_checks_pass']:return False,{'geometry_failed':True}
        report=split(folder/'assembly/assembly.ifc',spec,assembly,basis,control,folder/'split')
        return report['calculated_checks_pass'],dict(bracketed=report['bracketed'],checks=report.get('checks',{}),branch_fraction=report.get('branch_fraction'),required_source_total_pressure_pa=report.get('required_source_total_pressure_pa'))
    for row,paths in candidates:
        try:
            passed,details=execute(row,paths,out/'candidates'/row['id'])
        except (ValueError,RuntimeError) as exc:
            passed,details=False,{'error':f'{type(exc).__name__}: {exc}'}
        trials.append(dict(id=row['id'],source=row['source'],preference=row['preference'],passed=passed,details=details))
    feasible=[t for t in trials if t['passed']];selected=min(feasible,key=lambda t:(t['preference'],t['id'])) if feasible else None
    rerun=False
    if selected:
        row,paths=next((r,p) for r,p in candidates if r['id']==selected['id'])
        rerun,details=execute(row,paths,out/'selected')
        if details!=selected['details']:raise ValueError('selected rerun differs from retained screening trial')
    if any(digest(p)!=before[str(p)] for p in files):raise ValueError('catalogue input changed')
    result=dict(inputs=before,catalogue=data,trials=trials,selected=selected['id'] if selected else None,selected_rerun_pass=rerun,calculated_checks_pass=bool(selected and rerun),design_accepted=False,scope='Source-bounded bore/OD candidate preference; no cost optimum, real fitting applicability, arbitrary routing or code acceptance')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()};(out/'tee-selection.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('catalogue');p.add_argument('--out',required=True);a=p.parse_args();r=run(a.catalogue,a.out);print(json.dumps({k:r[k] for k in ('selected','selected_rerun_pass','calculated_checks_pass','design_accepted')},indent=2));raise SystemExit(0 if r['calculated_checks_pass'] else 2)
