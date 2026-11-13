"""Compact MCP access to existing source-native analysis; no replacement solver."""
import json
import hashlib
import re
from pathlib import Path
from . import source_network_analysis as network, source_fitting_data as fittings
from . import workspace
from . import source_network_delivery as delivery
from .artifact_access import LIMIT
from .cli import digest


def summary(out, record, data):
    path=Path(out)/record
    return dict(status='pending',design_accepted=False,pressure_budget_complete=False,
        critical_path=None,original_requirement_count=len(data['original_requirement_ids']),
        outlet_path_count=len(data['boundary_paths']),
        fitting_path_count=data.get('unique_fitting_paths',len(data.get('missing_fitting_path_losses',[]))),
        conditional_table_path_count=data.get('calculated_table_paths',0),
        transition_end_straight_study_count=len(data.get('transition_end_straight_study',[])),
        artifacts=[dict(path=str(path),sha256=digest(path),bytes=path.stat().st_size)],
        scope='Source/native execution and conditional calculations only. Missing losses, physical '
        'applicability, source assumptions, native drawings and complete design acceptance remain separate.')


def run_network(source,out):
    result=network.run(source,out)
    return summary(out,'analysis.json',result)


def run_fittings(analysis,basis,out):
    result=fittings.run(analysis,basis,out)
    return summary(out,'fitting-data.json',result)


def inspect(out,kind):
    if kind not in ('network','fittings'):
        raise ValueError('Fixed network or fittings inspection required')
    record='analysis.json' if kind=='network' else 'fitting-data.json'
    path=Path(out)/record;before=digest(path)
    receipt=(network if kind=='network' else fittings).verify(out)
    data=json.loads(path.read_text(encoding='utf-8'))
    result=summary(out,record,data)
    if digest(path)!=before or result['artifacts'][0]['sha256']!=before:
        raise ValueError('Analysis record changed during inspection')
    result['integrity_pass']=receipt['integrity_pass']
    return result


def recorded_fittings(out,record_sha256):
    """Read one bounded byte snapshot; this is not a new native/source replay."""
    root=(workspace.project_root() or workspace.ROOT/'runs').resolve()
    path=(Path(out)/'fitting-data.json').resolve()
    if not path.is_relative_to(root):
        raise ValueError('Record must belong to the host selected project')
    if not isinstance(record_sha256,str) or not re.fullmatch('[0-9a-f]{64}',record_sha256):
        raise ValueError('Exact inspected record SHA256 required')
    with path.open('rb') as stream:payload=stream.read(LIMIT+1)
    if len(payload)>LIMIT:raise ValueError('Fitting record exceeds bounded read limit')
    if hashlib.sha256(payload).hexdigest()!=record_sha256:
        raise ValueError('Fitting record differs from inspected identity')
    data=json.loads(payload)
    if not isinstance(data.get('data_requests'),list):raise ValueError('Recorded fitting requests required')
    return data


def list_requests(out,record_sha256,offset=0,limit=20,status=None):
    if isinstance(offset,bool) or not isinstance(offset,int) or offset<0 or isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=20:
        raise ValueError('Nonnegative integer offset and limit1..20 required')
    if status not in (None,'source_data_required','table_support_missing','physical_review_required','source_applicability_required','native_condition_failed'):
        raise ValueError('Supported recorded request status required')
    data=recorded_fittings(out,record_sha256)
    rows=[r for r in data['data_requests'] if status is None or r['status']==status]
    page=[dict(product_guid=r['product_guid'],inlet_port_guid=r['inlet_port_guid'],
        outlet_port_guid=r['outlet_port_guid'],predefined_type=r['predefined_type'],
        status=r['status'],affected_outlet_count=len(r['affected_outlet_port_guids'])) for r in rows[offset:offset+limit]]
    return dict(record_sha256=record_sha256,total=len(rows),offset=offset,requests=page,
        next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
        verification='Recorded bytes only; use inspect for current source/native replay',design_accepted=False)


def read_request(out,record_sha256,product_guid,inlet_port_guid,outlet_port_guid):
    data=recorded_fittings(out,record_sha256)
    rows=[r for r in data['data_requests'] if (r['product_guid'],r['inlet_port_guid'],r['outlet_port_guid'])==(product_guid,inlet_port_guid,outlet_port_guid)]
    if len(rows)!=1:raise ValueError('Exactly one recorded directed fitting path required')
    return dict(record_sha256=record_sha256,request=rows[0],
        transition_end_straight_study=[r for r in data.get('transition_end_straight_study',[]) if r['product_guid']==product_guid],
        verification='Recorded bytes only; use inspect for current source/native replay',design_accepted=False)


def delivery_summary(out,data):
    out=Path(out).resolve();root=(workspace.project_root() or workspace.ROOT/'runs').resolve()
    artifacts=[]
    for name in ('delivery.json','native/section.dwg','native/sheet.pdf'):
        path=out/name;sha=digest(path)
        if name!='delivery.json' and sha!=data['artifacts'][name]:
            raise ValueError('Delivery output differs from producer identity')
        artifacts.append(dict(path=str(path),project_path=path.relative_to(root).as_posix(),sha256=sha,bytes=path.stat().st_size))
    return dict(status='review_required',product_count=data['product_count'],
        original_requirement_count=len(data['original_requirement_ids']),
        native_reopen_pass=data['native_reopen_pass'],pdf_reference_pass=data['pdf_reference_pass'],
        scale_denominator=data['scale_denominator'],plot_visual_review=data['plot_visual_review'],
        pressure_budget_complete=False,design_accepted=False,artifacts=artifacts,
        scope='Composed geometry-study delivery only; render and inspect the actual page. Source assumptions, pressure, products, installation and complete engineering acceptance remain unresolved.')


def run_delivery(source,out,autocad,scale=None):
    if autocad is None:raise ValueError('Explicit host AutoCAD startup configuration required')
    return delivery_summary(out,delivery.run(source,out,autocad,scale))


def inspect_delivery(out):
    out=Path(out).resolve();before=digest(out/'delivery.json')
    checked=delivery.verify(out);data=json.loads((out/'delivery.json').read_text())
    result=delivery_summary(out,data)
    if digest(out/'delivery.json')!=before or result['artifacts'][0]['sha256']!=before:
        raise ValueError('Delivery record changed during inspection')
    result['integrity_pass']=checked['integrity_pass'];return result
