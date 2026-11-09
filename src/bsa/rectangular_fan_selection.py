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
