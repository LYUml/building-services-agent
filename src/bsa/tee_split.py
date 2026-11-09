"""Bounded fixed-total-flow split with sourced constant or tabulated face coefficients."""
import argparse
import importlib.metadata
import json
import math
import numpy as np
from pathlib import Path
from scipy.optimize import brentq
from .cli import digest
from .tee_pressure import run as pressure


def coefficient_table(control):
    """Validate optional continuous piecewise-linear data without extrapolation."""
    if 'coefficient_table' not in control:return None
    table=control['coefficient_table']
    if not isinstance(table,dict) or set(table)!={'source','rows'} or not isinstance(table['source'],str) or not table['source'].strip():
        raise ValueError('sourced coefficient table required')
    rows=table['rows']
    if not isinstance(rows,list) or len(rows)<2:raise ValueError('at least two coefficient rows required')
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'branch_fraction','k_run','k_branch'} or any(type(v) not in (int,float) or not math.isfinite(v) for v in row.values()):
            raise ValueError('finite fraction and coefficient rows required')
        if not 0<row['branch_fraction']<1:raise ValueError('interior table fractions required')
    fractions=[row['branch_fraction'] for row in rows]
    if any(b<=a for a,b in zip(fractions,fractions[1:])):raise ValueError('strictly increasing table fractions required')
    lo,hi=control['branch_fraction_bounds']
    if lo<fractions[0] or hi>fractions[-1]:raise ValueError('split bracket exceeds coefficient table; no extrapolation')
    return table


def run(model,tee_spec,assembly_spec,basis,control,out):
    paths=[Path(p).resolve() for p in (model,tee_spec,assembly_spec,basis,control)]
    model,tee_spec,assembly_spec,basis,control=paths;out=Path(out).resolve()
    before={str(p):digest(p) for p in paths}
    data=json.loads(basis.read_text(encoding='utf-8-sig'));c=json.loads(control.read_text(encoding='utf-8-sig'))
    if set(c)-{'coefficient_table'}!={'source','coefficient_scope','total_flow_m3_s','branch_fraction_bounds','pressure_tolerance_pa','ratio_tolerance'}:raise ValueError('exact split control required')
    if any(not isinstance(c[k],str) or not c[k].strip() for k in ('source','coefficient_scope')):raise ValueError('sourced coefficient interval applicability required')
    for k in ('total_flow_m3_s','pressure_tolerance_pa','ratio_tolerance'):
        if type(c[k]) not in (int,float) or not math.isfinite(c[k]) or c[k]<=0:raise ValueError('positive finite solver controls required')
    bounds=c['branch_fraction_bounds']
    if not isinstance(bounds,list) or len(bounds)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in bounds) or not 0<bounds[0]<bounds[1]<1:raise ValueError('strict interior branch fraction interval required')
    if c['ratio_tolerance']>=bounds[1]-bounds[0]:raise ValueError('ratio tolerance must be smaller than interval')
    table=coefficient_table(c)
    if importlib.metadata.version('scipy')!='1.18.1':raise ValueError('verified scipy 1.18.1 required')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out==p or out in p.parents for p in paths):raise ValueError('new repository output required')
    out.mkdir(parents=True);trials=[]
    def evaluate(fraction,supply=None):
        d=dict(data);q=c['total_flow_m3_s'];d['run_flow_m3_s']=q*(1-fraction);d['branch_flow_m3_s']=q*fraction
        if table is not None:
            fractions=[r['branch_fraction'] for r in table['rows']]
            if not fractions[0]<=fraction<=fractions[-1]:raise ValueError('coefficient extrapolation forbidden')
            for key in ('k_run','k_branch'):d[key]=float(np.interp(fraction,fractions,[r[key] for r in table['rows']]))
        if supply is not None:d['inlet_total_pressure_pa']=supply
        d['source']+='; split control: '+c['source'];d['coefficient_source']=(table['source'] if table else d['coefficient_source'])+'; interval applicability: '+c['coefficient_scope']
        index=len(trials);path=out/f'basis-{index}.json';path.write_text(json.dumps(d,indent=2))
        report=pressure(model,tee_spec,assembly_spec,path,out/f'trial-{index}')
        residual=report['paths']['run']['margin_pa']-report['paths']['branch']['margin_pa']
        trials.append(dict(fraction=fraction,k_run=d['k_run'],k_branch=d['k_branch'],residual_pa=residual,report=f'trial-{index}/tee-pressure.json'))
        return residual,report
    lo,hi=bounds;fl,left=evaluate(lo);fh,right=evaluate(hi)
    # Endpoint regimes prove each monotonic flow interval avoids the unsupported transition.
    if any(left['pipes'][k]['regime']!=right['pipes'][k]['regime'] for k in left['pipes']):raise ValueError('split interval crosses unsupported friction transition')
    bracketed=fl==0 or fh==0 or (fl<0<fh or fh<0<fl)
    result=dict(inputs=before,control=c,coefficient_mode='piecewise linear table' if table else 'constant',scipy_version='1.18.1',trials=trials,bracketed=bracketed,calculated_checks_pass=False,design_accepted=False,
        scope='Fixed total flow with adjustable source pressure and sourced face coefficients over declared interval; no pump curve, universal split or product/code acceptance')
    if bracketed:
        root=lo if fl==0 else hi if fh==0 else brentq(lambda x:evaluate(x)[0],lo,hi,xtol=c['ratio_tolerance'],rtol=1e-14,maxiter=100)
        residual,report=evaluate(root)
        required=max(data['inlet_total_pressure_pa']-row['margin_pa'] for row in report['paths'].values())
        _,final=evaluate(root,required)
        checks=dict(pressure_balance=abs(residual)<=c['pressure_tolerance_pa'],source_pressure_capacity=required<=data['inlet_total_pressure_pa'],velocity_targets=final['checks']['velocity_targets'],nonnegative_net_fitting_dissipation=final['checks']['nonnegative_net_fitting_dissipation'])
        result.update(branch_fraction=root,branch_flow_m3_s=c['total_flow_m3_s']*root,run_flow_m3_s=c['total_flow_m3_s']*(1-root),required_source_total_pressure_pa=required,available_source_total_pressure_pa=data['inlet_total_pressure_pa'],residual_pa=residual,checks=checks,calculated_checks_pass=all(checks.values()))
    if any(digest(p)!=before[str(p)] for p in paths):raise ValueError('input changed during split solve')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'tee-split.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','tee-spec','assembly-spec','basis','control','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=run(a.model,a.tee_spec,a.assembly_spec,a.basis,a.control,a.out);print(json.dumps(r,indent=2));raise SystemExit(0 if r['calculated_checks_pass'] else 2)
