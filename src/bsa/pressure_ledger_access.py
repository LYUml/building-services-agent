"""Bounded AI access to existing source-linked pressure evidence ledgers."""
import hashlib
import json
import re
from pathlib import Path
from . import source_pressure_ledger as ledger,workspace
from .artifact_access import LIMIT
from .cli import digest


def selected(out):
    out=Path(out).resolve();root=(workspace.project_root() or workspace.ROOT/'runs').resolve()
    if out==root or not out.is_relative_to(root):raise ValueError('Ledger must belong to selected project')
    return out,root


def summary(out,data):
    out,root=selected(out);path=out/'pressure-ledger.json';sha=digest(path)
    if json.loads((out/'ledger.json').read_text())['ledger_sha256']!=sha:raise ValueError('Ledger artifact differs from producer')
    return dict(status='review_required',outlet_count=data['outlet_count'],unique_fitting_path_count=data['unique_fitting_path_count'],conditional_numerical_path_count=data['conditional_numerical_path_count'],numerically_unresolved_fitting_path_count=data['numerically_unresolved_fitting_path_count'],original_requirement_count=len(data['original_requirement_ids']),record_sha256=sha,outlets=[dict(outlet_port_guid=p['outlet_port_guid'],numerically_unresolved_fitting_path_count=len(p['numerically_unresolved_fitting_paths'])) for p in data['outlet_paths']],artifact=dict(path=str(path),project_path=path.relative_to(root).as_posix(),sha256=sha,bytes=path.stat().st_size),pressure_budget_complete=False,critical_path=None,fan_duty_Pa=None,design_accepted=False,scope=data['scope'])


def run(source,out):
    selected(source);selected(out)
    return summary(out,ledger.run(source,out))


def inspect(out):
    out,_=selected(out);before=digest(out/'pressure-ledger.json');manifest=digest(out/'ledger.json')
    data=ledger.verify(out);result=summary(out,data)
    if digest(out/'pressure-ledger.json')!=before or digest(out/'ledger.json')!=manifest or result['record_sha256']!=before:raise ValueError('Ledger changed during inspection')
    result['integrity_pass']=True;return result


def recorded(out,record_sha256):
    out,_=selected(out)
    if not isinstance(record_sha256,str) or not re.fullmatch('[0-9a-f]{64}',record_sha256):raise ValueError('Exact inspected ledger SHA256 required')
    with (out/'pressure-ledger.json').open('rb') as stream:payload=stream.read(LIMIT+1)
    if len(payload)>LIMIT:raise ValueError('Ledger exceeds bounded read limit')
    if hashlib.sha256(payload).hexdigest()!=record_sha256:raise ValueError('Ledger differs from inspected identity')
    return json.loads(payload)


def list_gaps(out,record_sha256,offset=0,limit=20):
    if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=20:raise ValueError('Nonnegative offset and limit1..20 required')
    rows=recorded(out,record_sha256)['missing_evidence_by_outlet_coverage'];page=rows[offset:offset+limit]
    return dict(record_sha256=record_sha256,total=len(rows),offset=offset,gaps=page,next_offset=offset+len(page) if offset+len(page)<len(rows) else None,verification='Saved inspected bytes only; coverage order is research priority, not critical-path ranking',design_accepted=False)


def read_outlet(out,record_sha256,outlet_port_guid):
    rows=[p for p in recorded(out,record_sha256)['outlet_paths'] if p['outlet_port_guid']==outlet_port_guid]
    if len(rows)!=1:raise ValueError('Exactly one recorded outlet identity required')
    return dict(record_sha256=record_sha256,outlet=rows[0],verification='Saved inspected bytes only; use inspection for fresh source/native replay',pressure_budget_complete=False,fan_duty_Pa=None,design_accepted=False)
