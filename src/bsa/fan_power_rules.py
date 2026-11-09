"""Scoped BEC 2024 CAV/VAV base fan-power comparison; no deduction or operating-point model."""
import copy
import math
from .cli import digest
from .engine import ProjectError


def check(pack,rule,project,root):
    from .regulations import evaluate
    if rule.get('limits')!={'CAV':1.6,'VAV':2.1,'exempt_below_w':2500.,'base_clean_treatment_max_pa':250.}:raise ProjectError('verified BEC 2024 base fan-power limits required')
    facts=project.get('facts',{});reasons=[]
    def value(key,unit=None,boolean=False):
        row=facts.get(key,{})
        if not isinstance(row,dict) or not isinstance(row.get('source'),str) or not row['source'].strip():reasons.append('missing sourced fan basis: '+key);return None
        v=row.get('value')
        if unit and (type(v) not in (int,float) or not math.isfinite(v) or v<0 or row.get('unit')!=unit):reasons.append('invalid fan quantity/unit: '+key);return None
        if boolean and type(v) is not bool:reasons.append('unknown fan exemption: '+key);return None
        return v
    power=value('fan_motor_power','W');flow=value('supply_design_airflow','L/s');drop=value('clean_treatment_pressure_drop','Pa')
    ahu=value('ahu_individual_fan_exemption_applies',boolean=True);schedule=value('schedule2_exemption_applies',boolean=True)
    mode=value('air_distribution_mode')
    if mode not in ('CAV','VAV'):reasons.append('supported CAV/VAV mode not established');mode=None
    if flow==0:reasons.append('positive supply design airflow required')
    if drop is not None and drop>250:reasons.append('clean treatment drop exceeds base path; separate deduction/applicability assessment required')
    exempt=(power is not None and power<2500) or ahu is True or schedule is True
    maximum=rule['limits'][mode]*flow if mode is not None and flow is not None else None
    if maximum is not None and not math.isfinite(maximum):reasons.append('fan-power maximum overflow');maximum=None
    passed=power is not None and maximum is not None and power<=maximum
    p=copy.deepcopy(project);p['facts']=copy.deepcopy(facts)
    p['facts']['base_fan_power_path_applicable']=dict(value=not exempt,source='Derived from sourced unadjusted system power and explicit exemption assertions')
    p['facts'][rule['metric']]=dict(value=0 if passed else 1,unit=rule['unit'],source='Unadjusted supply/return clean-condition drawn electrical motor watts versus supply design L/s')
    sub=copy.deepcopy(pack);derived=copy.deepcopy(rule);derived.update(method='prescriptive_maximum',maximum=0);sub['rules']=[derived]
    row=evaluate(sub,p,root)['checks'][0]
    guidance=pack['sources'][rule['guidance_source_id']];path=(root/guidance['cache_filename']).resolve()
    if not path.is_relative_to(root):raise ProjectError('fan guidance cache path escapes root')
    if not path.is_file() or digest(path)!=guidance['sha256']:reasons.append('pinned fan-power guidance unavailable or changed')
    decision=project.get('edition_decisions',{}).get(rule['guidance_source_id'],{})
    if not isinstance(decision,dict) or decision.get('edition')!=guidance['edition'] or not isinstance(decision.get('basis'),str) or not decision['basis'].strip():reasons.append('fan-power guidance edition applicability missing')
    if reasons:row.update(status='pending',reasons=row.get('reasons',[])+reasons)
    row.update(mode=mode,unadjusted_fan_motor_power_w=power,supply_design_airflow_l_s=flow,
        maximum_unadjusted_power_w=maximum,exemption_asserted=exempt,deduction_applied_w=0.,guidance_url=guidance['url'],
        guidance_printed_page='76',motor_nameplate_or_air_power_substitution_permitted=False,
        pending_scope=['authentic equipment/inventory and actual clean operating point','6.7.4 reduced-speed/fresh-air requirements','6.7.6 mechanical ventilation route','deductions and full HVAC/engineering acceptance'])
    return row
