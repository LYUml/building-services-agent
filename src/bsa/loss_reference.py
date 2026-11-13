"""Signed pressure-invariant coefficient rebasing and scoped transition review."""
import argparse
import json
import math
from pathlib import Path
from . import contraction_candidate as candidate
from .cli import digest
from .workspace import allowed


def finite(value,positive=False):
    if type(value) not in (int,float) or not math.isfinite(value) or (positive and value<=0):raise ValueError('Finite coefficient and positive velocity pressure required')
    return value


def same(a,b):
    return math.isclose(finite(a),finite(b),rel_tol=1e-12,abs_tol=0.)


def rebase(coefficient,source_velocity_pressure_Pa,target_velocity_pressure_Pa):
    k=finite(coefficient);source=finite(source_velocity_pressure_Pa,True);target=finite(target_velocity_pressure_Pa,True)
    pressure=finite(k*source);converted=finite(pressure/target)
    if (k!=0 and pressure==0) or (pressure!=0 and converted==0):raise ValueError('Nonzero pressure/coefficient underflow')
    if not same(converted*target,pressure):raise ValueError('Pressure invariant not retained')
    return converted


def compare(request,probe):
    if request['product_guid']!=probe['product_guid'] or probe['status']!='bounded_numerical_crosscheck_only':raise ValueError('Exact bounded transition candidate required')
    table=request['recorded_table_result']
    if table is None or table['signed_tabulated_contribution_Pa'] is None:raise ValueError('Existing conditional contribution required')
    ports={request['inlet_port_guid']:request['inlet'],request['outlet_port_guid']:request['outlet']}
    if table['reference_port_guid'] not in ports:raise ValueError('Owned reference port required')
    inlet,outlet=request['inlet'],request['outlet']
    if not same(inlet['flow_m3_s'],outlet['flow_m3_s']):raise ValueError('Same-flow transition required')
    implied=[]
    for row in (inlet,outlet):
        q=finite(row['flow_m3_s'],True);area=finite(finite(row['width_m'],True)*finite(row['height_m'],True),True);velocity=finite(q/area,True)
        if not same(velocity,row['actual_velocity_m_s']):raise ValueError('Port velocity/area differs')
        implied.append(finite(finite(row['actual_velocity_pressure_Pa'],True)/finite(velocity*velocity,True),True))
    if not same(*implied):raise ValueError('Common fluid density convention required')
    old_vp=ports[table['reference_port_guid']]['actual_velocity_pressure_Pa'];target=outlet['actual_velocity_pressure_Pa']
    if not same(old_vp,finite(table['reference_velocity_pressure_Pa'],True)):raise ValueError('Recorded reference velocity pressure differs')
    old_k=rebase(table['coefficient'],old_vp,target);old_pa=old_k*target;new_k=finite(probe['candidate_coefficient']);new_pa=finite(new_k*target)
    if (new_k!=0 and new_pa==0) or not same(old_pa,table['signed_tabulated_contribution_Pa']) or not same(new_pa,probe['candidate_signed_Pa']):raise ValueError('Stored contribution/reference differs')
    return dict(product_guid=request['product_guid'],common_reference_port_guid=request['outlet_port_guid'],common_reference_velocity_pressure_Pa=target,existing_coefficient_on_common_reference=old_k,candidate_coefficient_on_common_reference=new_k,existing_conditional_signed_Pa=old_pa,candidate_signed_Pa=new_pa,difference_Pa=finite(new_pa-old_pa),reference_conversion_removes_numeric_difference=same(old_pa,new_pa),physical_method_selected=False,design_accepted=False)


def evaluate(source):
    record=json.loads((source/'probe.json').read_text());fitting=Path(record['source']).resolve()
    if not allowed(fitting):raise ValueError('Host-selected fitting source required')
    files=[source/'probe.json',source/'candidate.json',fitting/'fitting-data.json',Path(__file__).resolve(),Path(candidate.__file__).resolve()];pins={str(p):digest(p) for p in files}
    result=candidate.verify(source);data=json.loads((fitting/'fitting-data.json').read_text());requests={r['product_guid']:r for r in data['data_requests'] if r['transition_geometry']}
    rows=[compare(requests[r['product_guid']],r) for r in result['rows'] if r['candidate_coefficient'] is not None]
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Reference audit inputs changed')
    return dict(comparisons=rows,source_transition_count=len(result['rows']),formal_loss_values_added=0,design_accepted=False,scope='Reference/continuity arithmetic audit only. Numerical equality tolerance is not physical acceptance. Original correlation, construction, station/friction and interaction applicability remain unresolved; no method is selected.'),pins


def run(source,out):
    source,out=Path(source).resolve(),Path(out).resolve()
    if not allowed(source) or not allowed(out) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out):raise ValueError('Fresh separate host-selected reference audit required')
    result,pins=evaluate(source);out.mkdir(parents=True);(out/'comparison.json').write_text(json.dumps(result,indent=2));(out/'audit.json').write_text(json.dumps(dict(source=str(source),inputs=pins,artifact_sha256=digest(out/'comparison.json')),indent=2));return result


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Host-selected audit required')
    record=json.loads((out/'audit.json').read_text());source=Path(record['source']).resolve()
    if not allowed(source):raise ValueError('Host-selected candidate source required')
    result,pins=evaluate(source)
    if record['inputs']!=pins or digest(out/'comparison.json')!=record['artifact_sha256'] or result!=json.loads((out/'comparison.json').read_text()):raise ValueError('Reconstructed reference audit differs')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('source');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args();r=run(a.source,a.out) if a.command=='run' else verify(a.out)
    print(json.dumps(dict(comparisons=len(r['comparisons']),remaining_numeric_differences=sum(not x['reference_conversion_removes_numeric_difference'] for x in r['comparisons']),formal_loss_values_added=0,design_accepted=False),indent=2));raise SystemExit(2)
