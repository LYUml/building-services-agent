"""Conditional TN final-circuit proof using explicit device/energy source envelopes."""
import argparse
import csv
import html
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError,validate,calculate

MODEL='TN bolted-fault final-circuit source-envelope verification'
VOLTAGE='project supply voltage is phase-to-earth U0'
ROUTE='phase and CPC each follow project one-way route length'
GROUPS={
    'loop':{'external_r_ohm_hot','external_x_ohm_hot','phase_r_ohm_per_m_hot','cpc_r_ohm_per_m_hot','loop_x_ohm_per_m','minimum_voltage_factor'},
    'device':{'rated_current_a','nominal_voltage_min_v','nominal_voltage_max_v','standalone_breaking_capacity_a','trip_current_min_a','guaranteed_fault_max_a','guaranteed_total_clearing_time_s'},
    'limits':{'maximum_disconnection_time_s'},
    'max_fault':{'prospective_max_fault_a'},
    'cpc':{'section_mm2','adiabatic_k_a_sqrt_s_per_mm2','maximum_adiabatic_time_s'},
    'energy':{'maximum_let_through_a2s','fault_current_min_a','fault_current_max_a'},
}


def prepare(project,data):
    validate(project)
    fields={'model','voltage_basis','loop_route_basis','sources','circuits'}
    if not isinstance(data,dict) or set(data)!=fields or data['model']!=MODEL or data['voltage_basis']!=VOLTAGE or data['loop_route_basis']!=ROUTE:
        raise ProjectError('explicit TN/phase-earth voltage and common phase/CPC route basis required')
    sources=data['sources']
    if not isinstance(sources,dict) or not sources or any(not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip() for k,v in sources.items()):raise ProjectError('fault sources required')
    def sourced(row):
        if not isinstance(row,dict) or not isinstance(row.get('source'),str) or row['source'] not in sources:raise ProjectError('known source required for each fault input group')
    rows=data['circuits'];circuits={c['id']:c for c in project['circuits']}
    if not isinstance(rows,list) or len(rows)!=len(circuits):raise ProjectError('every electrical circuit needs a fault row, with explicit null for unknown groups')
    mapped={}
    zero_allowed={'external_r_ohm_hot','external_x_ohm_hot','loop_x_ohm_per_m'}
    for row in rows:
        sourced(row)
        if set(row)!={'id','source'}|set(GROUPS) or not isinstance(row['id'],str) or row['id'] not in circuits or row['id'] in mapped:raise ProjectError('exact unique fault circuit coverage required')
        for name,keys in GROUPS.items():
            group=row[name]
            if group is None:continue
            sourced(group)
            if set(group)!=keys|{'source'}:raise ProjectError('complete sourced '+name+' group or explicit null required')
            for key in keys:
                value=group[key]
                if type(value) not in (int,float) or not math.isfinite(value) or value<0 or key not in zero_allowed and value==0:
                    raise ProjectError('finite nonnegative impedances and positive device/energy/limit inputs required: '+key)
            if name=='loop' and group['minimum_voltage_factor']>1:raise ProjectError('minimum voltage factor must be <=1')
            if name=='device':
                if not math.isclose(group['rated_current_a'],circuits[row['id']]['breaker_a'],rel_tol=0,abs_tol=1e-9):raise ProjectError('device source rating differs from circuit breaker')
                if group['nominal_voltage_min_v']>group['nominal_voltage_max_v'] or group['trip_current_min_a']>group['guaranteed_fault_max_a']:raise ProjectError('ordered source device applicability ranges required')
            if name=='energy' and group['fault_current_min_a']>group['fault_current_max_a']:raise ProjectError('ordered energy applicability range required')
        mapped[row['id']]=row
    if set(mapped)!=set(circuits):raise ProjectError('fault circuit coverage differs from electrical project')
    return mapped


def solve(project,data):
    mapped=prepare(project,data);baseline=calculate(project);results=[]
    for circuit in project['circuits']:
        row=mapped[circuit['id']];loop,device,limits,maximum,cpc,energy=[row[k] for k in ('loop','device','limits','max_fault','cpc','energy')]
        values={};coverage={};gaps=['missing '+k+' source group' for k in GROUPS if row[k] is None]
        if loop:
            length=circuit['route_length_m']
            resistance=loop['external_r_ohm_hot']+length*(loop['phase_r_ohm_per_m_hot']+loop['cpc_r_ohm_per_m_hot'])
            reactance=loop['external_x_ohm_hot']+length*loop['loop_x_ohm_per_m']
            impedance=abs(complex(resistance,reactance))
            if not all(math.isfinite(v) for v in (resistance,reactance,impedance)) or impedance<=0:raise ProjectError('positive finite derived fault-loop impedance required')
            values.update(loop_r_ohm_hot=resistance,loop_x_ohm=reactance,loop_z_ohm=impedance,
                          minimum_earth_fault_a=loop['minimum_voltage_factor']*project['supply_voltage_v']/impedance)
            if not math.isfinite(values['minimum_earth_fault_a']):raise ProjectError('derived fault current overflowed')
        minimum=values.get('minimum_earth_fault_a');max_a=maximum['prospective_max_fault_a'] if maximum else None
        checks=dict(fault_envelope_consistent=minimum<=max_a if minimum is not None and max_a is not None else None,
                    standalone_breaking_capacity=None,automatic_disconnection_proven=None,cpc_adiabatic_energy=None)
        voltage_ok=device is not None and device['nominal_voltage_min_v']<=project['supply_voltage_v']<=device['nominal_voltage_max_v']
        coverage['device_voltage']=voltage_ok if device else None
        if device and not voltage_ok:gaps.append('project voltage outside supplied device applicability')
        if device and maximum and voltage_ok:checks['standalone_breaking_capacity']=max_a<=device['standalone_breaking_capacity_a']
        current_ok=device is not None and minimum is not None and max_a is not None and device['trip_current_min_a']<=minimum<=max_a<=device['guaranteed_fault_max_a']
        coverage['device_fault_interval']=current_ok if device and minimum is not None and max_a is not None else None
        if coverage['device_fault_interval'] is False:gaps.append('supplied total-clearing envelope does not cover the complete fault-current interval')
        if loop and device:values['maximum_loop_z_for_source_trip_ohm']=loop['minimum_voltage_factor']*project['supply_voltage_v']/device['trip_current_min_a']
        if device and limits and voltage_ok and current_ok:
            if device['guaranteed_total_clearing_time_s']<=limits['maximum_disconnection_time_s']:checks['automatic_disconnection_proven']=True
            else:gaps.append('source upper clearing-time bound does not prove the required disconnection time')
        energy_ok=energy is not None and minimum is not None and max_a is not None and energy['fault_current_min_a']<=minimum<=max_a<=energy['fault_current_max_a']
        coverage['energy_fault_interval']=energy_ok if energy and minimum is not None and max_a is not None else None
        if coverage['energy_fault_interval'] is False:gaps.append('supplied maximum let-through energy does not cover the complete fault interval')
        time_ok=device is not None and cpc is not None and device['guaranteed_total_clearing_time_s']<=cpc['maximum_adiabatic_time_s']
        coverage['adiabatic_time']=time_ok if device and cpc else None
        if coverage['adiabatic_time'] is False:gaps.append('clearing-time bound outside sourced adiabatic applicability')
        if cpc:
            product=cpc['adiabatic_k_a_sqrt_s_per_mm2']*cpc['section_mm2'];capacity=product*product
            if not math.isfinite(capacity):raise ProjectError('derived adiabatic capacity overflowed')
            values['cpc_energy_capacity_a2s']=capacity
            if energy:
                values['minimum_cpc_section_from_source_bound_mm2']=math.sqrt(energy['maximum_let_through_a2s'])/cpc['adiabatic_k_a_sqrt_s_per_mm2']
            if energy and voltage_ok and current_ok and energy_ok and time_ok:checks['cpc_adiabatic_energy']=energy['maximum_let_through_a2s']<=capacity
        if any(not math.isfinite(v) for v in values.values()):raise ProjectError('derived fault verification values overflowed')
        status='fail' if any(value is False for value in checks.values()) else 'pending' if any(value is None for value in checks.values()) else 'pass'
        results.append(dict(id=circuit['id'],status=status,source=row['source'],values=values,source_coverage=coverage,checks=checks,unverified=gaps))
    if any(not math.isfinite(v) for c in baseline['circuits'] for k,v in c.items() if type(v) in (int,float)):raise ProjectError('baseline electrical values overflowed')
    status='fail' if not baseline['calculated_checks_pass'] or any(r['status']=='fail' for r in results) else 'pending' if any(r['status']=='pending' for r in results) else 'pass'
    return dict(status=status,baseline_checks_pass=baseline['calculated_checks_pass'],circuits=results,
                fault_checks_pass=all(r['status']=='pass' for r in results),calculated_checks_pass=status=='pass',design_accepted=False,
                scope='Sourced TN hot phase/CPC loop, standalone device capacity and total-clearing/let-through envelopes; conditional verification only',
                pending=['actual source/code-edition/clause and device curve/energy applicability review','TT/IT/RCD, selectivity/cascading and overload coordination',
                         'phase/neutral thermal protection, touch-voltage/earthing and complete electrical acceptance'])


def run(project_path,faults_path,out):
    project_path,faults_path,out=[Path(p).resolve() for p in (project_path,faults_path,out)]
    if any(out==p or out in p.parents for p in (project_path,faults_path)):raise ProjectError('output must not contain fault/electrical source inputs')
    before={str(p):digest(p) for p in (project_path,faults_path)}
    project=json.loads(project_path.read_text(encoding='utf-8-sig'));data=json.loads(faults_path.read_text(encoding='utf-8-sig'))
    result=solve(project,data);out.mkdir(parents=True,exist_ok=False)
    result.update(inputs=before,inputs_unchanged=all(digest(Path(p))==sha for p,sha in before.items()),fault_data=data,electrical_sources=project['sources'],
                  methods=['https://www.electrical-installation.org/enwiki/TN_system_-_Principle',
                           'https://www.electrical-installation.org/enwiki/Other_characteristics_of_a_circuit-breaker',
                           'https://www.electrical-installation.org/enwiki/Verification_of_the_withstand_capabilities_of_cables_under_short-circuit_conditions'])
    if not result['inputs_unchanged']:raise ProjectError('fault source input changed during calculation')
    with (out/'checks.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['id','status','minimum_earth_fault_a','loop_z_ohm','standalone_breaking_capacity','automatic_disconnection_proven','cpc_adiabatic_energy'])
        writer.writeheader();writer.writerows(dict(id=r['id'],status=r['status'],**{k:r['values'].get(k) for k in ('minimum_earth_fault_a','loop_z_ohm')},**{k:r['checks'][k] for k in ('standalone_breaking_capacity','automatic_disconnection_proven','cpc_adiabatic_energy')}) for r in result['circuits'])
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Conditional fault verification</title><h1>Conditional fault verification</h1><p>'+html.escape(result['scope'])+'</p><p>Uncovered source guarantees stay unverified. No B/C/D trip multiples, disconnection times or material constants are embedded.</p><pre>'+html.escape(json.dumps(result['circuits'],indent=2))+'</pre><h2>Pending</h2><ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in result['pending'])+'</ul>',encoding='utf-8')
    result['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
    (out/'faults.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    parser.add_argument('--faults',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();result=run(args.project,args.faults,args.out)
    print(json.dumps({k:result[k] for k in ('status','fault_checks_pass','calculated_checks_pass','design_accepted')}))
    return 0 if result['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
