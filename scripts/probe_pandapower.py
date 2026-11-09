"""Pinned upstream three-phase trial, not an assignment or production adapter.

Run with the isolated pandapower Python. Synthetic values are declared here;
they are not manufacturer data, measured routes or Hong Kong requirements.
"""
import argparse
import cmath
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path


def trial(p_kw):
    import pandapower as pp
    if pp.__version__!='3.5.6':raise ValueError('requires pandapower 3.5.6')
    net=pp.create_empty_network(f_hz=50,sn_mva=1)
    a=pp.create_bus(net,vn_kv=0.4,name='source')
    b=pp.create_bus(net,vn_kv=0.4,name='load')
    pp.create_ext_grid(net,a,vm_pu=1,va_degree=0,s_sc_max_mva=100,
                       rx_max=0.1,x0x_max=1,r0x0_max=0.1)
    pp.create_line_from_parameters(net,a,b,length_km=0.05,
        r_ohm_per_km=0.2,x_ohm_per_km=0.08,c_nf_per_km=0,max_i_ka=0.1,
        r0_ohm_per_km=0.6,x0_ohm_per_km=0.24,c0_nf_per_km=0)
    pp.create_asymmetric_load(net,b,p_a_mw=p_kw[0]/1000,p_b_mw=p_kw[1]/1000,
        p_c_mw=p_kw[2]/1000,q_a_mvar=0,q_b_mvar=0,q_c_mvar=0,type='wye')
    pp.runpp_3ph(net,numba=False,max_iteration=30,tolerance_mva=1e-10)
    if not net.converged:raise ValueError('upstream did not converge')
    bus=net.res_bus_3ph;line=net.res_line_3ph.loc[0]
    base_v=400/math.sqrt(3)
    voltages=[[cmath.rect(float(bus.loc[i,f'vm_{ph}_pu'])*base_v,
                          math.radians(float(bus.loc[i,f'va_{ph}_degree'])))
               for ph in 'abc'] for i in (a,b)]
    currents=[complex(p*1000,0).conjugate()/v.conjugate() for p,v in zip(p_kw,voltages[1])]
    z1=complex(0.2,0.08)*0.05;z0=complex(0.6,0.24)*0.05
    zdiag=(z0+2*z1)/3;zmut=(z0-z1)/3
    residuals=[abs(voltages[0][i]-voltages[1][i]-sum(
        (zdiag if i==j else zmut)*currents[j] for j in range(3))) for i in range(3)]
    phase_current_a=[float(line[f'i_{ph}_to_ka'])*1000 for ph in 'abc']
    current_errors=[abs(i-abs(j)) for i,j in zip(phase_current_a,currents)]
    p_load_error_w=[abs(-float(line[f'p_{ph}_to_mw'])*1e6-p*1000) for ph,p in zip('abc',p_kw)]
    q_load_error_var=[abs(float(line[f'q_{ph}_to_mvar'])*1e6) for ph in 'abc']
    source_w=sum(float(net.res_ext_grid_3ph.loc[0,f'p_{ph}_mw'])*1e6 for ph in 'abc')
    source_var=sum(float(net.res_ext_grid_3ph.loc[0,f'q_{ph}_mvar'])*1e6 for ph in 'abc')
    losses_w=sum((float(line[f'p_{ph}_from_mw'])+float(line[f'p_{ph}_to_mw']))*1e6 for ph in 'abc')
    losses_var=sum((float(line[f'q_{ph}_from_mvar'])+float(line[f'q_{ph}_to_mvar']))*1e6 for ph in 'abc')
    independently_derived_loss=sum(currents[i].conjugate()*sum(
        (zdiag if i==j else zmut)*currents[j] for j in range(3)) for i in range(3))
    result=dict(p_kw=p_kw,phase_voltage_v=[abs(v) for v in voltages[1]],
        phase_current_a=phase_current_a,line_loading_percent=float(line['loading_percent']),
        line_equation_residual_v=residuals,current_reconciliation_error_a=current_errors,
        load_reconciliation_error_w=p_load_error_w,source_power_w=source_w,line_losses_w=losses_w,
        independent_line_losses_w=independently_derived_loss.real,
        load_reconciliation_error_var=q_load_error_var,
        source_reactive_power_var=source_var,line_reactive_absorption_var=losses_var,
        reactive_balance_error_var=abs(source_var-losses_var),
        reactive_loss_error_var=abs(losses_var-independently_derived_loss.imag),
        power_balance_error_w=abs(source_w-sum(p_kw)*1000-losses_w),
        resistive_loss_error_w=abs(losses_w-independently_derived_loss.real))
    if len(set(p_kw))==1:
        p=p_kw[0]*1000
        t=base_v**2-2*z1.real*p
        v=math.sqrt((t+math.sqrt(t*t-4*abs(z1)**2*p*p))/2)
        result['balanced_analytic_voltage_v']=v
        result['balanced_analytic_error_v']=max(abs(abs(w)-v) for w in voltages[1])
    checks=dict(line_equations=max(residuals)<1e-5,
        currents=max(current_errors)<1e-5,load_power=max(p_load_error_w)<1e-3,
        power_balance=result['power_balance_error_w']<1e-3,
        reactive_power=max(q_load_error_var)<1e-3 and result['reactive_balance_error_var']<1e-3 and result['reactive_loss_error_var']<1e-3,
        resistive_losses=result['resistive_loss_error_w']<1e-3,
        balanced_analytic=result.get('balanced_analytic_error_v',0)<1e-5)
    result.update(verification_checks=checks,verification_pass=all(checks.values()),
        synthetic_current_target_a=100,synthetic_current_target_pass=max(phase_current_a)<=100,
        design_accepted=False)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve()
    root=Path(__file__).resolve().parents[1]
    if not out.is_relative_to(root/'runs'):p.error('output must be under repository runs')
    if out.exists():p.error('refusing to overwrite output')
    cases={name:trial(values) for name,values in [('balanced',[5,5,5]),('unbalanced',[10,5,2]),('overload',[30,5,2])]}
    result=dict(scope='Synthetic two-bus wye constant-power, zero-shunt sequence-line upstream evaluation only',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        versions={n:importlib.metadata.version(n) for n in ('pandapower','numpy','scipy','pandas')},
        source_basis='All line, supply, load and 100 A target values are synthetic trial inputs; no product/code applicability',
        cases=cases,verification_pass=all(c['verification_pass'] for c in cases.values()),
        overload_retained=not cases['overload']['synthetic_current_target_pass'],design_accepted=False)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(verification_pass=result['verification_pass'],overload_retained=result['overload_retained'],design_accepted=False)))
    return 0 if result['verification_pass'] and result['overload_retained'] else 2


if __name__=='__main__':raise SystemExit(main())
