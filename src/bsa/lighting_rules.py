"""Office LPD calculation from full-output circuit watts and sourced floor area."""
import copy
import math


def office_check(pack,rule,project,root):
    from .regulations import evaluate
    facts=project.get('facts',{});reasons=[]
    def quantity(item,unit,positive=False):
        return (isinstance(item,dict) and isinstance(item.get('source'),str) and bool(item['source'].strip())
                and item.get('unit')==unit and type(item.get('value')) in (int,float)
                and math.isfinite(item['value']) and (item['value']>0 if positive else item['value']>=0))
    space=project.get('lighting_space',{})
    if not isinstance(space,dict):space={}
    area=space.get('internal_floor_area');lights=space.get('luminaires')
    valid=quantity(area,'m2',True)
    if not valid:reasons.append('sourced positive internal floor area in m2 required')
    if not isinstance(lights,list) or not lights:reasons.append('complete nonempty luminaire inventory required');lights=[]
    ids=set();power=0.
    for light in lights:
        if (not isinstance(light,dict) or not isinstance(light.get('id'),str) or not light['id'].strip()
                or light['id'] in ids or not quantity(light.get('full_output_circuit_power'),'W')):
            reasons.append('unique luminaire ids and sourced full-output circuit watts required');continue
        ids.add(light['id']);power+=light['full_output_circuit_power']['value']
    if not math.isfinite(power):reasons.append('finite summed circuit watts required')
    enclosed=facts.get('enclosed_office')
    if not isinstance(enclosed,dict) or type(enclosed.get('value')) is not bool or not isinstance(enclosed.get('source'),str) or not enclosed['source'].strip():
        reasons.append('sourced enclosed-office classification required')
    selected=None
    if valid:
        for band in rule['area_bands']:
            if area['value']>band['lower_exclusive_m2'] and (band['upper_inclusive_m2'] is None or area['value']<=band['upper_inclusive_m2']):
                selected=band;break
        if selected is None:reasons.append('unsupported office area classification')
        elif selected.get('requires_enclosed') and (not isinstance(enclosed,dict) or enclosed.get('value') is not True):
            reasons.append('small office row requires enclosed space; no applicable row inferred')
    p=copy.deepcopy(project);p['facts']=copy.deepcopy(facts)
    evidence='Computed from lighting_space full-output luminaire inventory and internal floor area; no demand/dimming factor'
    lpd=power/area['value'] if valid and math.isfinite(power) else None
    p['facts'][rule['metric']]=dict(value=lpd,unit=rule['unit'],source=evidence)
    p['facts']['above_lpd_low_power_exception']=dict(value=power>rule['low_power_exception_w'],source=evidence)
    derived=copy.deepcopy(rule);derived['method']='prescriptive_maximum'
    derived['maximum']=selected['maximum_w_m2'] if selected else 0
    subpack=copy.deepcopy(pack);subpack['rules']=[derived]
    row=evaluate(subpack,p,root)['checks'][0]
    if reasons:
        row['status']='pending';row['reasons']=row.get('reasons',[])+reasons
    row.update(total_full_output_circuit_w=power,computed_lpd_w_m2=lpd,selected_area_band=selected,
               calculation_scope='All listed luminaires counted at full circuit watts; exclusions/multifunction spaces unsupported')
    return row
