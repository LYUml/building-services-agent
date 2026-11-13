"""Bounded data-only probe of pinned python-hvac contraction tables; not adoption."""
import ast
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from .cli import digest
from .workspace import allowed

COMMIT='94247560a667905bfbf67e45a58965a58254fce8'
SOURCE_SHA='4c0f14a911784d76aa7c7212cd930608219547b8cc63535627b4c33b930c57a9'
LICENSE_SHA='1ad7f5d784476db176152001eeafcef6b8476feac1b79739cf5249c5b04eb950'


def arrays(source,license_path):
    if digest(Path(source))!=SOURCE_SHA or digest(Path(license_path))!=LICENSE_SHA:raise ValueError('Exact pinned upstream source and MIT notice required')
    tree=ast.parse(Path(source).read_text(encoding='utf-8'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ConvergingTransitionA9B')
    result={}
    for n in cls.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('_theta','_A_on_A1','_k_A','_L_on_D','_zeta'):
            if not isinstance(n.value,ast.Call) or ast.unparse(n.value.func)!='np.array' or len(n.value.args)!=1 or n.value.keywords:raise ValueError('Literal upstream arrays required')
            result[n.targets[0].id]=np.asarray(ast.literal_eval(n.value.args[0]),dtype=float)
    if len(result)!=5:raise ValueError('Complete upstream data axes required')
    return result


def interpolate(data,angle,length_ratio,area_ratio):
    if importlib.metadata.version('scipy')!='1.18.1':raise ValueError('Pinned SciPy1.18.1 required')
    x,y,a,k,z=[np.asarray(data[n],dtype=float) for n in ('_theta','_L_on_D','_A_on_A1','_k_A','_zeta')]
    if any(v.ndim!=1 or len(v)<2 or not np.isfinite(v).all() or not np.all(np.diff(v)>0) for v in (x,y,a)) or z.shape!=(len(y),len(x)) or k.shape!=a.shape or not np.isfinite(z).all() or not np.isfinite(k).all():raise ValueError('Finite regular upstream grid required')
    for value,axis in ((angle,x),(length_ratio,y),(area_ratio,a)):
        if type(value) not in (int,float) or not math.isfinite(value) or not axis[0]<=value<=axis[-1]:raise ValueError('Candidate query outside explicit source axes')
    base=float(RegularGridInterpolator((y,x),z,bounds_error=True)([[length_ratio,angle]])[0])
    return base*float(np.interp(area_ratio,a,k))


def screen(request,data):
    geometry=request['transition_geometry'];q=geometry['quantities'];w=q['taper_width_angle_deg'];h=q['taper_height_angle_deg']
    row=dict(product_guid=request['product_guid'],candidate_coefficient=None,existing_conditional_coefficient=(request['recorded_table_result'] or {}).get('coefficient'),physical_applicability_verified=False,design_accepted=False)
    if geometry['flow_change']!='contraction':row['status']='flow_family_unmatched';return row
    if min(w,h)<=0 or abs(w-h)>1e-6:row['status']='no_single_equal_wall_angle';return row
    inlet=geometry['inlet_section_m'];outlet=geometry['outlet_section_m'];ratio=math.prod(outlet)/math.prod(inlet)
    row.update(angle_deg=w,taper_length_over_outlet_hydraulic_diameter=q['taper_length_over_outlet_hydraulic_diameter'],outlet_to_inlet_area_ratio=ratio)
    try:row['candidate_coefficient']=interpolate(data,float(w),float(q['taper_length_over_outlet_hydraulic_diameter']),float(ratio))
    except ValueError:row['status']='outside_candidate_axes';return row
    row['status']='bounded_numerical_crosscheck_only'
    row['coefficient_reference']='small downstream duct velocity pressure; do not compare directly with inlet-reference coefficients'
    table=request['recorded_table_result']
    if table and table.get('signed_tabulated_contribution_Pa') is not None:
        row['existing_conditional_signed_Pa']=table['signed_tabulated_contribution_Pa']
    row['candidate_signed_Pa']=row['candidate_coefficient']*request['outlet']['actual_velocity_pressure_Pa']
    return row


def evaluate(source,upstream,license_path):
    import scipy.interpolate._rgi as rgi
    from . import source_fitting_data as fitting
    paths=[source/'fitting-data.json',upstream,license_path,Path(__file__).resolve(),Path(fitting.__file__).resolve(),Path(rgi.__file__).resolve()]
    pins={str(p):digest(p) for p in paths};fitting.verify(source)
    data=json.loads((source/'fitting-data.json').read_text());grid=arrays(upstream,license_path)
    rows=[screen(r,grid) for r in data['data_requests'] if r['transition_geometry'] is not None]
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Candidate sources/methods changed')
    return dict(rows=rows,upstream_commit=COMMIT,upstream_package_executed=False,data_only_interpolation_probe=True,formal_loss_values_added=0,design_accepted=False,scope='Bounded numerical crosscheck of data extracted without executing upstream code. Single equal wall angle is a screening choice, not verified original correlation applicability. Small-duct reference retained; no candidate pressure enters production paths.'),pins


def run(source,upstream,license_path,out):
    source,upstream,license_path,out=[Path(p).resolve() for p in (source,upstream,license_path,out)]
    if not all(allowed(p) for p in (source,upstream,license_path,out)) or out.exists() or any(out.is_relative_to(p) or p.is_relative_to(out) for p in (source,upstream,license_path)):raise ValueError('Fresh separate host-selected candidate study required')
    result,pins=evaluate(source,upstream,license_path);out.mkdir(parents=True)
    (out/'candidate.json').write_text(json.dumps(result,indent=2));(out/'probe.json').write_text(json.dumps(dict(source=str(source),upstream=str(upstream),license=str(license_path),inputs=pins,artifact_sha256=digest(out/'candidate.json')),indent=2));return result


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Host-selected candidate study required')
    record=json.loads((out/'probe.json').read_text());paths=[Path(record[k]).resolve() for k in ('source','upstream','license')]
    if not all(allowed(p) for p in paths):raise ValueError('Host-selected sources required')
    result,pins=evaluate(*paths)
    if pins!=record['inputs'] or digest(out/'candidate.json')!=record['artifact_sha256'] or result!=json.loads((out/'candidate.json').read_text()):raise ValueError('Reconstructed candidate probe differs')
    return result


if __name__=='__main__':
    from collections import Counter
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('source');a.add_argument('upstream');a.add_argument('license');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args()
    r=run(a.source,a.upstream,a.license,a.out) if a.command=='run' else verify(a.out)
    print(json.dumps(dict(statuses=dict(Counter(x['status'] for x in r['rows'])),formal_loss_values_added=0,upstream_package_executed=False,design_accepted=False),indent=2));raise SystemExit(2)
