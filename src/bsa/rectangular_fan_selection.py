"""Finite source-declared fan-curve screening on one verified native rectangular path."""
import copy
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .rectangular_binding import verified_study
from .rectangular_fan import validate_curve,run as trial
# Same explicit preference contract as circulation_pump_design; no EPANET dependency.
OBJECTIVE='lowest declared preference among passing candidates'


def candidates(catalogue):
    if not isinstance(catalogue,dict) or set(catalogue)!={'objective','source','candidates'} or catalogue['objective']!=OBJECTIVE or not isinstance(catalogue['source'],str) or not catalogue['source'].strip():raise ProjectError('explicit sourced finite fan preference catalogue required')
    rows=catalogue['candidates']
    if not isinstance(rows,list) or not 1<=len(rows)<=100:raise ProjectError('fan catalogue requires 1..100 candidates')
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'id','source','preference','curve'}:raise ProjectError('exact fan id/source/preference/curve fields required')
        if not isinstance(row['id'],str) or not row['id'].strip() or row['id'] in seen:raise ProjectError('unique nonempty fan candidate IDs required')
        seen.add(row['id'])
        if not isinstance(row['source'],str) or not row['source'].strip() or type(row['preference']) not in (int,float) or not math.isfinite(row['preference']):raise ProjectError('fan source and finite preference required')
        validate_curve(row['curve'])
    return copy.deepcopy(rows)


def run(project,model,binding,ifc,analysis,catalogue,out):
    paths=[Path(p).resolve() for p in (project,model,binding,ifc,analysis,catalogue)]
    out=Path(out).resolve()
    if out.exists() or any(out==p or out in p.parents for p in paths):raise ProjectError('new separate fan selection output required')
    before={str(p):digest(p) for p in paths}
    options=candidates(json.loads(paths[-1].read_text(encoding='utf-8-sig')))
    verified_study(*paths[:5])
    out.mkdir(parents=True)
    def unchanged():
        if any(not Path(p).is_file() or digest(Path(p))!=h for p,h in before.items()):raise ProjectError('fan selection source changed')
    def evaluate(row,folder):
        unchanged();folder.mkdir()
        curve=folder/'curve.json';curve.write_text(json.dumps(row['curve'],indent=2),encoding='utf-8')
        try:
            r=trial(paths[0],curve,folder/'operating')
        except ProjectError as exc:
            unchanged()
            return dict(status='unsupported',calculated_checks_pass=False,reason=str(exc),curve_sha256=digest(curve))
        unchanged()
        return dict(status=r['status'],calculated_checks_pass=r['calculated_checks_pass'],checks=r.get('checks'),operating_point=r.get('operating_point'),curve_sha256=digest(curve),report_sha256=digest(folder/'operating/fan.json'))
    records=[]
    for i,row in enumerate(options):
        record={k:row[k] for k in ('id','source','preference')};record['directory']=f'candidate-{i:03d}'
        record.update(evaluate(row,out/record['directory']));records.append(record)
    passing=sorted((r for r in records if r['calculated_checks_pass']),key=lambda r:(r['preference'],r['id']))
    result=dict(inputs=before,inputs_unchanged=True,native_path_correspondence_pass=True,objective=OBJECTIVE,tie_break='lexical candidate ID',candidates=records,selected=None,feasible_candidate_found=bool(passing),selected_rerun_pass=False,calculated_checks_pass=False,design_accepted=False,
        scope='Finite sourced fan-curve screening on verified native duct path; no fan hardware authoring, electrical/HK acceptance or authenticity guarantee',
        pending=['Real vendor curve/installation and stable-region applicability','Native fan equipment/ports and electrical motor evidence','Full acoustics/control/Hong Kong/installation acceptance'])
    if passing:
        chosen=passing[0];row=next(r for r in options if r['id']==chosen['id'])
        rerun=evaluate(row,out/'selected')
        if not rerun['calculated_checks_pass'] or rerun['operating_point']!=chosen['operating_point']:raise ProjectError('selected fan rerun differs from ranked candidate')
        result.update(selected=dict(id=chosen['id'],source=chosen['source'],preference=chosen['preference'],rerun=rerun),selected_rerun_pass=True,calculated_checks_pass=True)
    verified_study(*paths[:5]);unchanged()
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'fan-selection.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def selected_input(producer,project,model,binding,ifc,analysis,catalogue):
    """Reconstruct candidate ranking and native scenario before selected-curve handoff."""
    from .rectangular_fan import solve
    producer=Path(producer).resolve()
    paths=[Path(p).resolve() for p in (project,model,binding,ifc,analysis,catalogue)]
    report=producer/'fan-selection.json'
    before=digest(report);result=json.loads(report.read_text(encoding='utf-8-sig'))
    expected_inputs={str(p):digest(p) for p in paths}
    if result.get('inputs')!=expected_inputs:raise ProjectError('selected fan source identity differs')
    if not all(result.get(k) is True for k in ('feasible_candidate_found','selected_rerun_pass','calculated_checks_pass','native_path_correspondence_pass')) or not isinstance(result.get('selected'),dict):raise ProjectError('no passing selected fan available')
    artifacts=result.get('artifacts',{})
    required={'selected/curve.json','selected/operating/fan.json','selected/operating/operating-network.json','selected/operating/analysis/network.json'}
    if not isinstance(artifacts,dict) or not required<=set(artifacts):raise ProjectError('selected fan artifact coverage missing')
    for name,sha in artifacts.items():
        path=(producer/name).resolve()
        if not path.is_relative_to(producer) or not path.is_file() or digest(path)!=sha:raise ProjectError('selected fan artifact changed')
    verified_study(*paths[:5])
    options=candidates(json.loads(paths[-1].read_text(encoding='utf-8-sig')))
    project_data=json.loads(paths[0].read_text(encoding='utf-8-sig'))
    records=result.get('candidates')
    if not isinstance(records,list) or len(records)!=len(options):raise ProjectError('selected fan candidate coverage differs')
    passing=[];solutions={}
    for i,(row,record) in enumerate(zip(options,records)):
        directory=f'candidate-{i:03d}'
        if any(record.get(k)!=row[k] for k in ('id','source','preference')) or record.get('directory')!=directory:raise ProjectError('selected fan candidate source/ranking differs')
        curve=producer/directory/'curve.json'
        if f'{directory}/curve.json' not in artifacts or json.loads(curve.read_text(encoding='utf-8-sig'))!=row['curve']:raise ProjectError('candidate curve differs from original source')
        try:
            fresh,data=solve(project_data,row['curve'])
            expected={k:fresh.get(k) for k in ('status','calculated_checks_pass','checks','operating_point')}
        except ProjectError as exc:
            expected=dict(status='unsupported',calculated_checks_pass=False,reason=str(exc));data=None
        if any(record.get(k)!=v for k,v in expected.items()):raise ProjectError('candidate status differs from fresh fan solve')
        if record.get('calculated_checks_pass'):
            passing.append(row);solutions[row['id']]=(fresh,data)
    if not passing:raise ProjectError('no feasible fan reconstructed')
    chosen=min(passing,key=lambda r:(r['preference'],r['id']))
    selection=result['selected']
    if result.get('objective')!=OBJECTIVE or result.get('tie_break')!='lexical candidate ID' or any(selection.get(k)!=chosen[k] for k in ('id','source','preference')):raise ProjectError('selected fan is not reconstructed preferred candidate')
    fresh,data=solutions[chosen['id']]
    curve=producer/'selected/curve.json'
    if json.loads(curve.read_text(encoding='utf-8-sig'))!=chosen['curve'] or json.loads((producer/'selected/operating/operating-network.json').read_text(encoding='utf-8-sig'))!=data:raise ProjectError('selected curve/operating scenario differs from sourced reconstruction')
    saved=json.loads((producer/'selected/operating/fan.json').read_text(encoding='utf-8-sig'))
    for key in ('status','checks','operating_point','calculated_checks_pass'):
        if saved.get(key)!=fresh.get(key):raise ProjectError('selected operating result differs from fresh solve')
    if selection.get('rerun',{}).get('operating_point')!=fresh['operating_point'] or selection.get('rerun',{}).get('calculated_checks_pass') is not True:raise ProjectError('selected rerun summary differs')
    if digest(report)!=before or any(not p.is_file() or digest(p)!=expected_inputs[str(p)] for p in paths):raise ProjectError('selected fan sources changed during handoff')
    for name,sha in artifacts.items():
        if digest(producer/name)!=sha:raise ProjectError('selected fan artifacts changed during handoff')
    return curve
