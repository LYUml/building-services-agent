"""Sourced HVAC water-piping conditions; hydraulic bore is not code diameter."""
import copy
import math


def check(pack,rule,project,root):
    from .regulations import evaluate
    data=project.get('water_pipe',{});reasons=[];comparisons=[]
    if not isinstance(data,dict):data={}
    def item(key):
        v=data.get(key)
        if not isinstance(v,dict) or not isinstance(v.get('source'),str) or not v['source'].strip():
            reasons.append('missing sourced pipe condition: '+key);return {}
        return v
    def quantity(key,unit,positive=False):
        q=item(key);v=q.get('value')
        if type(v) not in (int,float) or not math.isfinite(v) or q.get('unit')!=unit or v<0 or positive and v==0:
            reasons.append('invalid pipe quantity/unit: '+key);return None
        return v
    def compare(key,value,maximum):
        if value is not None:comparisons.append(dict(input=key,value=value,maximum=maximum,passed=value<=maximum))
    diameter=quantity('code_diameter','mm',True);velocity=quantity('velocity','m/s')
    limits=rule['limits']
    if diameter is not None:
        if diameter<=limits['small_diameter_max_mm']:
            compare('velocity',velocity,limits['small_velocity_max_m_s'])
        else:
            compare('linear_friction',quantity('linear_friction','Pa/m'),limits['large_friction_max_pa_m'])
            mode=item('flow_mode').get('value')
            if mode not in ('non_variable','variable'):reasons.append('explicit supported flow mode required')
            else:
                compare('velocity',velocity,limits['large_'+('variable' if mode=='variable' else 'fixed')+'_velocity_max_m_s'])
                if mode=='variable':
                    control=item('pump_control').get('value')
                    if not isinstance(control,str) or not control.strip():reasons.append('explicit pump control description required')
                    else:comparisons.append(dict(input='pump_control',value=control,allowed=rule['allowed_variable_pump_controls'],passed=control in rule['allowed_variable_pump_controls']))
    p=copy.deepcopy(project);p['facts']=copy.deepcopy(project.get('facts',{}))
    p['facts'][rule['metric']]=dict(value=sum(not row['passed'] for row in comparisons),unit=rule['unit'],source='Derived from sourced water_pipe conditions; diameter classification remains explicit')
    derived=copy.deepcopy(rule);derived.update(method='prescriptive_maximum',maximum=0)
    sub=copy.deepcopy(pack);sub['rules']=[derived]
    result=evaluate(sub,p,root)['checks'][0]
    if reasons:
        result['reasons']=(result['reasons'] if result['status']=='pending' else [])+reasons
        result['status']='pending'
    result['condition_checks']=comparisons
    return result
