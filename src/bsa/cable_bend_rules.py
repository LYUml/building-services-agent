"""Scoped EMSD PVC stranded-copper cable internal bend table, not product selection."""
import copy
import math
from .engine import ProjectError


def check(pack,rule,project,root):
    from .regulations import evaluate
    limits=rule.get('limits',{})
    if limits!={'diameter_boundaries_mm':[10,25],'non_armoured_factors':[3,4,6],'armoured_factor':6}:
        raise ProjectError('verified CoP 2025 25C(1)(h) table required')
    facts=project.get('facts',{});reasons=[]
    def value(key,unit=None):
        item=facts.get(key,{})
        if not isinstance(item,dict) or not isinstance(item.get('source'),str) or not item['source'].strip():reasons.append('missing sourced cable condition: '+key);return None
        v=item.get('value')
        if unit:
            if type(v) not in (int,float) or not math.isfinite(v) or v<0 or (key=='overall_diameter' and v==0) or item.get('unit')!=unit:
                reasons.append('invalid cable quantity/unit: '+key);return None
        elif type(v) is not bool:reasons.append('unknown cable classification: '+key);return None
        return v
    diameter=value('overall_diameter','mm');inside=value('internal_bend_radius','mm');armoured=value('armoured')
    factor=None;minimum=None;passed=None
    if diameter is not None and inside is not None and armoured is not None:
        index=0 if diameter<=10 else 1 if diameter<=25 else 2
        factor=limits['armoured_factor'] if armoured else limits['non_armoured_factors'][index]
        minimum=factor*diameter
        # Numeric representation roundoff only, not construction/measurement tolerance.
        passed=inside>=minimum or math.isclose(inside,minimum,rel_tol=0,abs_tol=1e-9)
    p=copy.deepcopy(project);p['facts']=copy.deepcopy(facts)
    p['facts'][rule['metric']]=dict(value=0 if passed else 1,unit=rule['unit'],source='Derived from sourced overall diameter, armour and internal bend radius')
    sub=copy.deepcopy(pack);derived=copy.deepcopy(rule);derived.update(method='prescriptive_maximum',maximum=0);sub['rules']=[derived]
    row=evaluate(sub,p,root)['checks'][0]
    if reasons:row.update(status='pending',reasons=row.get('reasons',[])+reasons)
    row.update(overall_diameter_mm=diameter,internal_bend_radius_mm=inside,armoured=armoured,multiplier=factor,minimum_internal_radius_mm=minimum,
               numeric_radius_comparison=passed,numerical_roundoff_mm=1e-9,manufacturer_selection_verified=False)
    return row
