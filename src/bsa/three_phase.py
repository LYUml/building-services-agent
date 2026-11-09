"""Source-bound constant-PQ wye networks using pinned upstream pandapower.

Sequence lines, one voltage level and one external source only. Numerical
verification and explicit study targets are separate from design acceptance.
"""
import argparse
import cmath
import importlib.metadata
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError

MODEL='three-phase sequence-line constant-PQ wye'
ROOT=Path(__file__).resolve().parents[2]


def fields(row,keys):
    if not isinstance(row,dict) or set(row)!=set(keys.split()):
        raise ProjectError('required exact fields: '+keys)


def number(row,key,minimum=None,positive=False):
    v=row.get(key)
    if type(v) not in (int,float) or not math.isfinite(v) or (minimum is not None and (v<minimum or (positive and v==minimum))):
        raise ProjectError('invalid finite numeric input: '+key)
    return v


def prepare(project):
    project=Path(project).resolve();base=project.parent
    if not project.is_relative_to(ROOT):raise ProjectError('project must be in repository')
    p=json.loads(project.read_text(encoding='utf-8-sig'))
    fields(p,'version model name sources supply buses lines loads voltage_limits')
    if type(p['version']) is not int or p['version']!=1 or p['model']!=MODEL or not isinstance(p['name'],str) or not p['name'].strip():
        raise ProjectError('version 1 and explicit sequence-line wye model/name required')
    if not isinstance(p['sources'],dict) or not p['sources']:raise ProjectError('source records required')
    inputs={project}
    for key,source in p['sources'].items():
        fields(source,'path sha256 locator kind')
        if not isinstance(key,str) or not key or not isinstance(source['path'],str) or Path(source['path']).is_absolute():raise ProjectError('relative source path required')
        f=(base/source['path']).resolve()
        if not f.is_relative_to(base) or not f.is_file() or digest(f)!=source['sha256']:raise ProjectError('source path/hash mismatch')
        if not isinstance(source['locator'],str) or not source['locator'].strip() or source['kind'] not in ('course_given','measured','manufacturer','design_target','assumption'):
            raise ProjectError('explicit source kind/locator required')
        inputs.add(f)

    def source(row,key='source'):
        if not isinstance(row.get(key),str) or row[key] not in p['sources']:raise ProjectError('unknown source: '+key)

    def rows(key):
        values=p[key]
        if not isinstance(values,list) or not values:raise ProjectError('nonempty '+key+' required')
        seen=set()
        for row in values:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'].strip() or row['id'] in seen:
                raise ProjectError('unique nonempty IDs required for '+key)
            seen.add(row['id'])
        return values

    buses=rows('buses');ids={b['id'] for b in buses}
    for b in buses:fields(b,'id')
    s=p['supply'];fields(s,'bus line_line_v frequency_hz voltage_pu angle_degree s_sc_max_mva rx_max x0x_max r0x0_max source')
    source(s)
    if not isinstance(s['bus'],str) or s['bus'] not in ids:raise ProjectError('source bus missing')
    for key in ('line_line_v','frequency_hz','voltage_pu','s_sc_max_mva','rx_max','x0x_max','r0x0_max'):number(s,key,0,True)
    number(s,'angle_degree')
    adjacency={b:set() for b in ids}
    for line in rows('lines'):
        fields(line,'id from to length_m r1_ohm_per_km x1_ohm_per_km r0_ohm_per_km x0_ohm_per_km max_current_a source current_limit_source')
        source(line);source(line,'current_limit_source')
        if any(not isinstance(line[k],str) or line[k] not in ids for k in ('from','to')) or line['from']==line['to']:raise ProjectError('valid distinct line buses required')
        adjacency[line['from']].add(line['to']);adjacency[line['to']].add(line['from'])
        for key in ('length_m','r1_ohm_per_km','r0_ohm_per_km','max_current_a'):number(line,key,0,True)
        for key in ('x1_ohm_per_km','x0_ohm_per_km'):number(line,key,0)
    visited=set();todo=[s['bus']]
    while todo:
        b=todo.pop()
        if b not in visited:visited.add(b);todo.extend(adjacency[b]-visited)
    if visited!=ids:raise ProjectError('all buses must be connected to the source')
    total=0
    for load in rows('loads'):
        fields(load,'id bus p_kw q_kvar source');source(load)
        if not isinstance(load['bus'],str) or load['bus'] not in ids:raise ProjectError('load bus missing')
        for key in ('p_kw','q_kvar'):
            values=load[key]
            if not isinstance(values,list) or len(values)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ProjectError('three finite phase powers required')
        if min(load['p_kw'])<0:raise ProjectError('load generation unsupported; p_kw must be nonnegative')
        total+=sum(load['p_kw'])
    if total<=0:raise ProjectError('positive total active demand required')
    v=p['voltage_limits'];fields(v,'minimum_pu maximum_pu source');source(v)
    if number(v,'minimum_pu',0,True)>=number(v,'maximum_pu',0,True):raise ProjectError('ordered positive voltage targets required')
    return p,inputs


def build(p):
    import pandapower as pp
    net=pp.create_empty_network(f_hz=p['supply']['frequency_hz'],sn_mva=1)
    s=p['supply'];buses={b['id']:pp.create_bus(net,vn_kv=s['line_line_v']/1000,name=b['id']) for b in p['buses']}
    pp.create_ext_grid(net,buses[s['bus']],**{k:s[k] for k in ('s_sc_max_mva','rx_max','x0x_max','r0x0_max')},vm_pu=s['voltage_pu'],va_degree=s['angle_degree'])
    for line in p['lines']:
        pp.create_line_from_parameters(net,buses[line['from']],buses[line['to']],name=line['id'],
            length_km=line['length_m']/1000,r_ohm_per_km=line['r1_ohm_per_km'],x_ohm_per_km=line['x1_ohm_per_km'],
            r0_ohm_per_km=line['r0_ohm_per_km'],x0_ohm_per_km=line['x0_ohm_per_km'],
            c_nf_per_km=0,c0_nf_per_km=0,max_i_ka=line['max_current_a']/1000)
    for load in p['loads']:
        pp.create_asymmetric_load(net,buses[load['bus']],name=load['id'],type='wye',
            **{f'p_{ph}_mw':v/1000 for ph,v in zip('abc',load['p_kw'])},
            **{f'q_{ph}_mvar':v/1000 for ph,v in zip('abc',load['q_kvar'])})
    return net


def native_input_issues(p,net):
    """Check saved upstream model parameters against the declared input contract."""
    issues=[]
    def compare(observed,expected,label):
        try:
            same=observed==expected if isinstance(expected,(str,bool)) else math.isfinite(float(observed)) and math.isclose(float(observed),expected,rel_tol=1e-12,abs_tol=1e-12)
            if not same:issues.append(label)
        except (TypeError,ValueError):issues.append(label)
    s=p['supply'];bus_ids={b['id']:i for i,b in enumerate(p['buses'])}
    compare(net.f_hz,s['frequency_hz'],'frequency')
    for i,b in enumerate(p['buses']):
        for key,v in dict(name=b['id'],vn_kv=s['line_line_v']/1000,in_service=True).items():compare(net.bus.loc[i,key],v,'bus '+b['id']+' '+key)
    for key,v in dict(bus=bus_ids[s['bus']],vm_pu=s['voltage_pu'],va_degree=s['angle_degree'],in_service=True,
        **{k:s[k] for k in ('s_sc_max_mva','rx_max','x0x_max','r0x0_max')}).items():compare(net.ext_grid.loc[0,key],v,'supply '+key)
    for i,line in enumerate(p['lines']):
        expected=dict(name=line['id'],from_bus=bus_ids[line['from']],to_bus=bus_ids[line['to']],
            length_km=line['length_m']/1000,r_ohm_per_km=line['r1_ohm_per_km'],x_ohm_per_km=line['x1_ohm_per_km'],
            r0_ohm_per_km=line['r0_ohm_per_km'],x0_ohm_per_km=line['x0_ohm_per_km'],
            c_nf_per_km=0,c0_nf_per_km=0,max_i_ka=line['max_current_a']/1000,parallel=1,df=1,in_service=True)
        for key,v in expected.items():compare(net.line.loc[i,key],v,'line '+line['id']+' '+key)
    for i,load in enumerate(p['loads']):
        expected=dict(name=load['id'],bus=bus_ids[load['bus']],type='wye',scaling=1,in_service=True,
            **{f'p_{ph}_mw':v/1000 for ph,v in zip('abc',load['p_kw'])},
            **{f'q_{ph}_mvar':v/1000 for ph,v in zip('abc',load['q_kvar'])})
        for key,v in expected.items():compare(net.asymmetric_load.loc[i,key],v,'load '+load['id']+' '+key)
    for table in ('load','sgen','asymmetric_sgen','gen','trafo','trafo3w','shunt','switch','impedance','ward','xward','dcline','motor'):
        if len(net[table]):issues.append('unsupported elements in '+table)
    for table,n in [('bus',len(p['buses'])),('line',len(p['lines'])),('asymmetric_load',len(p['loads'])),('ext_grid',1)]:
        if list(net[table].index)!=list(range(n)):issues.append('native element inventory '+table)
    return issues


def audit(p,net):
    """Independent branch voltage, node KCL and complex power reconciliation."""
    if not net.converged:raise ProjectError('upstream did not converge')
    native_issues=native_input_issues(p,net)
    expected=[('res_bus_3ph',p['buses']),('res_line_3ph',p['lines']),('res_asymmetric_load_3ph',p['loads'])]
    for key,rows in expected:
        if list(net[key].index)!=list(range(len(rows))):raise ProjectError('missing/extra native result rows: '+key)
    if list(net.res_ext_grid_3ph.index)!=[0]:raise ProjectError('exactly one external grid result required')
    def value(row,key):
        v=float(row[key])
        if not math.isfinite(v):raise ProjectError('nonfinite upstream result: '+key)
        return v
    def power(row,ph,suffix=''):
        return complex(value(row,f'p_{ph}{suffix}_mw'),value(row,f'q_{ph}{suffix}_mvar'))*1e6
    base=p['supply']['line_line_v']/math.sqrt(3)
    volts={b['id']:[cmath.rect(value(net.res_bus_3ph.loc[i],f'vm_{ph}_pu')*base,
        math.radians(value(net.res_bus_3ph.loc[i],f'va_{ph}_degree'))) for ph in 'abc'] for i,b in enumerate(p['buses'])}
    if any(abs(v)<1e-6 for values in volts.values() for v in values):raise ProjectError('zero/near-zero voltage cannot be audited')
    kcl={b['id']:[0j]*3 for b in p['buses']};load_total=0j;load_errors=[]
    for i,load in enumerate(p['loads']):
        observed=net.res_asymmetric_load_3ph.loc[i]
        for n,ph in enumerate('abc'):
            demand=complex(load['p_kw'][n],load['q_kvar'][n])*1000
            kcl[load['bus']][n]+=(demand/volts[load['bus']][n]).conjugate()
            load_total+=demand;load_errors.append(abs(power(observed,ph)-demand))
    lines=[];loss_total=0j;loss_errors=[]
    for index,line in enumerate(p['lines']):
        row=net.res_line_3ph.loc[index];a,b=line['from'],line['to']
        sf=[power(row,ph,'_from') for ph in 'abc'];st=[power(row,ph,'_to') for ph in 'abc']
        currents=[(s/v).conjugate() for s,v in zip(sf,volts[a])]
        incoming=[(s/v).conjugate() for s,v in zip(st,volts[b])]
        for n in range(3):kcl[a][n]+=currents[n];kcl[b][n]+=incoming[n]
        z1=complex(line['r1_ohm_per_km'],line['x1_ohm_per_km'])*line['length_m']/1000
        z0=complex(line['r0_ohm_per_km'],line['x0_ohm_per_km'])*line['length_m']/1000
        drop=[sum(((z0+2*z1)/3 if i==j else (z0-z1)/3)*currents[j] for j in range(3)) for i in range(3)]
        residual=[abs(volts[a][n]-volts[b][n]-drop[n]) for n in range(3)]
        end_residual=[abs(x+y) for x,y in zip(currents,incoming)]
        current_errors=[abs(value(row,f'i_{ph}_{end}_ka')*1000-abs(v)) for end,values in [('from',currents),('to',incoming)] for ph,v in zip('abc',values)]
        loss=sum(sf)+sum(st);independent_loss=sum(i.conjugate()*v for i,v in zip(currents,drop))
        loss_total+=loss;loss_errors.append(abs(loss-independent_loss))
        amps=[abs(v) for v in currents]
        lines.append(dict(id=line['id'],phase_current_a=amps,line_voltage_residual_v=residual,
            end_current_residual_a=end_residual,current_result_error_a=current_errors,
            complex_loss_error_va=abs(loss-independent_loss),active_loss_w=loss.real,
            reactive_absorption_var=loss.imag,current_target_pass=max(amps)<=line['max_current_a']))
    grid=net.res_ext_grid_3ph.loc[0];supply=p['supply']['bus'];source_total=0j
    for n,ph in enumerate('abc'):
        injected=power(grid,ph);source_total+=injected
        kcl[supply][n]-=(injected/volts[supply][n]).conjugate()
    nodes=[dict(id=id,phase_voltage_v=[abs(v) for v in vs],phase_angle_degree=[math.degrees(cmath.phase(v)) for v in vs],
        current_balance_error_a=[abs(i) for i in kcl[id]],voltage_target_pass=all(
            p['voltage_limits']['minimum_pu']<=abs(v)/base<=p['voltage_limits']['maximum_pu'] for v in vs)) for id,vs in volts.items()]
    residuals=dict(max_line_voltage_error_v=max(max(r['line_voltage_residual_v']) for r in lines),
        max_end_current_error_a=max(max(r['end_current_residual_a']) for r in lines),
        max_current_result_error_a=max(max(r['current_result_error_a']) for r in lines),
        max_node_kcl_error_a=max(max(r['current_balance_error_a']) for r in nodes),
        max_load_power_error_va=max(load_errors),max_line_loss_error_va=max(loss_errors),
        total_power_balance_error_va=abs(source_total-load_total-loss_total))
    tolerances={key:(1e-3 if key.endswith('_va') else 1e-5) for key in residuals}
    checks={key:residuals[key]<tolerances[key] for key in residuals}
    checks['native_input_correspondence']=not native_issues
    verification_pass=all(checks.values())
    targets_pass=all(r['current_target_pass'] for r in lines) and all(r['voltage_target_pass'] for r in nodes)
    return dict(nodes=nodes,lines=lines,residuals=residuals,numerical_tolerances=tolerances,native_input_issues=native_issues,
        total_source_power=dict(electrical_kw=source_total.real/1000,reactive_kvar=source_total.imag/1000),
        total_load_power=dict(electrical_kw=load_total.real/1000,reactive_kvar=load_total.imag/1000),
        total_line_absorption=dict(electrical_kw=loss_total.real/1000,reactive_kvar=loss_total.imag/1000),
        verification_checks=checks,verification_pass=verification_pass,study_targets_pass=targets_pass,
        status='pass' if verification_pass and targets_pass else 'fail',design_accepted=False,
        scope='Single-voltage sequence-line constant-PQ wye power flow; numerical checks and declared targets only; no physical neutral, protection, cable selection, CAD/BIM or regulatory acceptance')


def run(project,out):
    project,out=Path(project).resolve(),Path(out).resolve()
    p,inputs=prepare(project)
    if not out.is_relative_to(ROOT) or any(out==f or out in f.parents for f in inputs):raise ProjectError('output must be separate repository directory')
    if out.exists():raise ProjectError('refusing to overwrite run')
    before={str(f):digest(f) for f in inputs}
    import pandapower as pp
    if pp.__version__!='3.5.6':raise ProjectError('requires isolated pandapower 3.5.6')
    out.mkdir(parents=True)
    try:
        net=build(p);pp.to_json(net,str(out/'network.json'))
        net=pp.from_json(str(out/'network.json'))
        pp.runpp_3ph(net,numba=False,max_iteration=30,tolerance_mva=1e-10)
        result=audit(p,net)
        if any(digest(f)!=before[str(f)] for f in inputs):raise ProjectError('source changed during study')
        result.update(inputs=before,source_records=p['sources'],input_unchanged=True,
            versions={n:importlib.metadata.version(n) for n in ('pandapower','numpy','scipy','pandas')},
            network_sha256=digest(out/'network.json'),adapter_sha256=digest(Path(__file__)))
        with (out/'study.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
        return result
    except Exception as exc:
        with (out/'failure.json').open('x',encoding='utf-8') as f:json.dump(dict(error=type(exc).__name__,message=str(exc),design_accepted=False),f,indent=2)
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:result=run(a.project,a.out)
    except Exception as exc:p.exit(2,type(exc).__name__+': '+str(exc)+'\n')
    print(json.dumps({k:result[k] for k in ('status','verification_pass','study_targets_pass','design_accepted')}))
    return 0 if result['status']=='pass' else 2


if __name__=='__main__':raise SystemExit(main())
