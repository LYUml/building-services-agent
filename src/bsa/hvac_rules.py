"""Scoped load-design condition checks, distinct from thermostat operation."""
import copy
import math


def design_conditions_check(pack,rule,project,root):
    from .regulations import evaluate
    data=project.get('load_design_conditions',{})
    if not isinstance(data,dict):data={}
    reasons=[];comparisons=[]
    def sourced(name):
        item=data.get(name)
        if not isinstance(item,dict) or not isinstance(item.get('source'),str) or not item['source'].strip():
            reasons.append('missing sourced load-design input: '+name);return None
        return item
    def category(name,allowed):
        item=sourced(name)
        if item is None:return None
        if not isinstance(item.get('value'),str) or item['value'] not in allowed:
            reasons.append('unsupported '+name);return None
        return item['value']
    def quantity(name,unit):
        item=sourced(name)
        if item is None:return None
        v=item.get('value')
        if type(v) not in (int,float) or not math.isfinite(v) or item.get('unit')!=unit:
            reasons.append('invalid load-design quantity/unit: '+name);return None
        if unit=='percent' and not 0<=v<=100 or unit=='degC' and v<=-273.15:
            reasons.append('nonphysical load-design quantity: '+name);return None
        return v
    season=category('season',rule['indoor_limits'])
    application=category('application',rule['applications'])
    db=quantity('indoor_dry_bulb','degC');rh=quantity('indoor_relative_humidity','percent')
    outdoor=quantity('outdoor_dry_bulb','degC')
    def compare(name,value,limit,method):
        if value is not None:
            comparisons.append(dict(input=name,value=value,method=method,limit=limit,passed=value>=limit if method=='minimum' else value<=limit))
    if season and application:
        indoor=rule['indoor_limits'][season][application]
        compare('indoor_dry_bulb',db,indoor['dry_bulb_degC'],indoor['method'])
        compare('indoor_relative_humidity',rh,indoor['relative_humidity_percent'],indoor['method'])
    if season=='summer':
        wet=quantity('outdoor_wet_bulb','degC');limit=rule['outdoor_limits']['summer']
        if outdoor is not None and wet is not None:
            if wet>outdoor:reasons.append('outdoor wet bulb exceeds dry bulb; conditions inconsistent')
            comparisons.append(dict(input='outdoor_dry_and_wet_bulb',dry_bulb_degC=outdoor,wet_bulb_degC=wet,
                limits=limit,passed=(outdoor<=limit['dry_bulb_max_degC'] and wet<limit['wet_bulb_max_degC']) or
                                  (wet<=limit['wet_bulb_max_degC'] and outdoor<limit['dry_bulb_max_degC'])))
    elif season=='winter':
        compare('outdoor_dry_bulb',outdoor,rule['outdoor_limits']['winter']['dry_bulb_min_degC'],'minimum')
    p=copy.deepcopy(project)
    p['facts']=copy.deepcopy(project.get('facts',{}))
    p['facts'][rule['metric']]=dict(value=sum(not c['passed'] for c in comparisons),unit=rule['unit'],
        source='Computed only from sourced load_design_conditions; no thermostat or weather-series substitution')
    derived=copy.deepcopy(rule);derived.update(method='prescriptive_maximum',maximum=0)
    subpack=copy.deepcopy(pack);subpack['rules']=[derived]
    row=evaluate(subpack,p,root)['checks'][0]
    if reasons:
        existing=row.get('reasons',[]) if row['status']=='pending' else []
        row['status']='pending';row['reasons']=existing+reasons
    row.update(condition_checks=comparisons,season=season,application=application,
               calculation_scope='Selected human-comfort load-design condition limits only; no load solver or operating thermostat check')
    return row
