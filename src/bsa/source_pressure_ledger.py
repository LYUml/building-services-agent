"""Reconstruct source-network pressure evidence per outlet without inventing duty."""
import argparse
import json
import math
from pathlib import Path
from . import source_fitting_data as fitting
from .cli import digest
from .workspace import allowed

KEY=('product_guid','inlet_port_guid','outlet_port_guid')
GAPS=['fitting physical applicability and source transcription','whole-fitting friction and pressure stations','adjacent fitting and joint interaction','terminal and equipment losses','boundary pressure requirements and physical source assumptions']


def key(row):return tuple(row[k] for k in KEY)


def number(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Finite signed pressure required')
    return value


def calculate(case,data):
    if case['original_requirement_ids']!=data['original_requirement_ids']:raise ValueError('Original requirements differ')
    requests={key(r):r for r in data['data_requests']};tables={key(r):r for r in data['table_results']}
    if len(requests)!=len(data['data_requests']) or len(tables)!=len(data['table_results']):raise ValueError('Duplicate directed fitting identity')
    straights={r['guid']:r for r in case['straight_sections']}
    supplied={p['outlet_port_guid']:p for p in data['boundary_paths']}
    if len(supplied)!=len(data['boundary_paths']):raise ValueError('Duplicate outlet summary')
    affected={k:set() for k in requests};paths=[];outlets=set()
    for path in case['boundary_paths']:
        outlet=path['outlet_port_guid']
        if outlet in outlets:raise ValueError('Duplicate original outlet')
        outlets.add(outlet);straight=[];conditional=[];missing=[];steps=[];seen=set();seen_straight=set();interfaces=0
        for step in path['steps']:
            if step['kind']=='shared_cap_interface':interfaces+=1;continue
            if step['kind']=='straight':
                r=straights[step['product_guid']];value=number(r['straight_friction_Pa'])
                if r['guid'] in seen_straight:raise ValueError('Repeated straight in one outlet path')
                seen_straight.add(r['guid'])
                if value!=step['straight_friction_Pa']:raise ValueError('Straight path contribution differs')
                straight.append(value);steps.append(dict(kind='straight',product_guid=r['guid'],signed_Pa=value));continue
            if step['kind']!='fitting':raise ValueError('Unsupported pressure step')
            k=key(step)
            if k not in requests or k in seen:raise ValueError('Missing or repeated directed fitting path')
            seen.add(k);affected[k].add(outlet);request=requests[k];table=tables.get(k)
            if table!=request['recorded_table_result']:raise ValueError('Request/table evidence differs')
            value=table.get('signed_tabulated_contribution_Pa') if table else None
            if value is None:missing.append(dict(zip(KEY,k)))
            else:conditional.append(number(value))
            steps.append(dict(kind='fitting',**dict(zip(KEY,k)),signed_Pa=value,status=request['status'],source_id=table.get('source_id') if table else None,citation_location=table.get('citation_location') if table else None))
        a=math.fsum(straight);b=math.fsum(conditional);old=supplied.get(outlet)
        if old is None or old['inlet_port_guid']!=path['inlet_port_guid'] or not math.isclose(a,number(path['known_straight_friction_Pa']),rel_tol=1e-12,abs_tol=1e-10):raise ValueError('Original outlet accounting differs')
        if not math.isclose(a,number(old['known_straight_friction_Pa']),rel_tol=1e-12,abs_tol=1e-10) or not math.isclose(b,number(old['supplied_table_contribution_Pa']),rel_tol=1e-12,abs_tol=1e-10) or old['unresolved_fitting_path_count']!=len(missing):raise ValueError('Recorded fitting outlet subtotal differs')
        partial=None if missing else a+b
        if old['tabulated_plus_separate_straight_Pa']!=partial or old['complete_total_pressure_drop_Pa'] is not None:raise ValueError('Unsupported complete pressure assertion')
        paths.append(dict(inlet_port_guid=path['inlet_port_guid'],outlet_port_guid=outlet,known_straight_friction_Pa=a,conditional_signed_table_subtotal_Pa=b,numerically_unresolved_fitting_paths=missing,conditional_arithmetic_only_Pa=partial,shared_interfaces_requiring_joint_review=interfaces,contributions=steps,unresolved_scope=GAPS,complete_total_pressure_drop_Pa=None))
    if outlets!=set(supplied) or any(not v for v in affected.values()) or set(tables)-set(requests):raise ValueError('Complete path/evidence coverage required')
    gaps=[];finite=0
    for k,request in requests.items():
        if set(request['affected_outlet_port_guids'])!=affected[k] or len(request['affected_outlet_port_guids'])!=len(affected[k]):raise ValueError('Affected outlet evidence differs')
        table=tables.get(k);value=table.get('signed_tabulated_contribution_Pa') if table else None
        if value is not None:finite+=1
        else:gaps.append(dict(**dict(zip(KEY,k)),predefined_type=request['predefined_type'],status=request['status'],affected_outlet_port_guids=sorted(affected[k]),affected_outlet_count=len(affected[k]),required_evidence=request['required_evidence']))
    gaps.sort(key=lambda r:(-r['affected_outlet_count'],r['product_guid'],r['inlet_port_guid'],r['outlet_port_guid']))
    return dict(outlet_paths=sorted(paths,key=lambda p:p['outlet_port_guid']),outlet_count=len(paths),unique_fitting_path_count=len(requests),conditional_numerical_path_count=finite,numerically_unresolved_fitting_path_count=len(gaps),missing_evidence_by_outlet_coverage=gaps,original_requirement_ids=case['original_requirement_ids'],excluded_transition_end_straight_study_count=len(data.get('transition_end_straight_study',[])),pressure_budget_complete=False,critical_path=None,fan_duty_Pa=None,design_accepted=False,scope='Evidence accounting only. Coverage order is research priority, not hydraulic criticality. Signed partial subtotals are not lower bounds or fan duties. Separate end-straight studies are excluded; parallel outlet paths are never summed.')


def evaluate(source):
    data=json.loads((source/'fitting-data.json').read_text());analysis=Path(data['source_analysis']).resolve()
    if not allowed(analysis):raise ValueError('Host-selected source analysis required')
    case=json.loads((analysis/'analysis.json').read_text())
    return calculate(case,data),{str(p):digest(p) for p in (source/'fitting-data.json',analysis/'analysis.json',Path(__file__).resolve(),Path(fitting.__file__).resolve())}


def run(source,out):
    source,out=Path(source).resolve(),Path(out).resolve()
    if not allowed(source) or not allowed(out) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out):raise ValueError('Fresh separate host-selected ledger output required')
    before=digest(source/'fitting-data.json');fitting.verify(source);data,pins=evaluate(source)
    if before!=digest(source/'fitting-data.json') or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Ledger inputs changed during reconstruction')
    out.mkdir(parents=True)
    (out/'pressure-ledger.json').write_text(json.dumps(data,indent=2));(out/'ledger.json').write_text(json.dumps(dict(source=str(source),inputs=pins,ledger_sha256=digest(out/'pressure-ledger.json')),indent=2));return data


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Host-selected ledger required')
    record=json.loads((out/'ledger.json').read_text());source=Path(record['source']).resolve()
    if not allowed(source):raise ValueError('Host-selected fitting source required')
    fitting.verify(source);data,pins=evaluate(source)
    if pins!=record['inputs'] or digest(out/'pressure-ledger.json')!=record['ledger_sha256'] or data!=json.loads((out/'pressure-ledger.json').read_text()):raise ValueError('Reconstructed pressure ledger differs')
    return data


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('source');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args()
    r=run(a.source,a.out) if a.command=='run' else verify(a.out)
    print(json.dumps({k:r[k] for k in ('outlet_count','conditional_numerical_path_count','numerically_unresolved_fitting_path_count','pressure_budget_complete','design_accepted')},indent=2));raise SystemExit(2)
