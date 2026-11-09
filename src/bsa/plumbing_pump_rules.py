"""WSD sump/pump facts; asserted duty capacity is not an executed pump analysis."""
import copy
import math


def check(pack, rule, project, root):
    from .regulations import evaluate
    data = project.get('sump_pump', {})
    reasons = []
    comparisons = []
    if not isinstance(data, dict):data = {}
    def item(key):
        value = data.get(key)
        if not isinstance(value, dict) or not isinstance(value.get('source'), str) or not value['source'].strip():
            reasons.append('missing sourced sump-pump condition: '+key); return {}
        return value
    duplicate = item('duplicate_pumpset_provided').get('value')
    if type(duplicate) is not bool:reasons.append('explicit duplicate-pumpset Boolean required')
    else:comparisons.append(dict(condition='duplicate_pumpset_provided', passed=duplicate))
    quantities = {}
    for key in ('available_pumping_capacity', 'tank_design_outflow'):
        value = item(key)
        number = value.get('value')
        if type(number) not in (int, float) or not math.isfinite(number) or number <= 0 or value.get('unit') != 'm3/s':
            reasons.append('positive sourced flow in m3/s required: '+key)
        else:quantities[key] = number
    for key in ('capacity_duty_basis', 'tank_identity', 'pump_configuration_basis'):
        value = item(key).get('value')
        if not isinstance(value, str) or not value.strip():reasons.append('explicit sourced description required: '+key)
    if len(quantities) == 2:
        comparisons.append(dict(condition='capacity_at_least_tank_design_outflow',
                                available_m3_s=quantities['available_pumping_capacity'],
                                required_m3_s=quantities['tank_design_outflow'],
                                passed=quantities['available_pumping_capacity'] >= quantities['tank_design_outflow']))
    data_project = copy.deepcopy(project)
    data_project['facts'] = copy.deepcopy(project.get('facts', {}))
    data_project['facts'][rule['metric']] = dict(value=sum(not c['passed'] for c in comparisons), unit=rule['unit'],
        source='Derived from sourced sump_pump assertions; no native hydraulic or installed configuration proof')
    simple = copy.deepcopy(rule); simple.update(method='prescriptive_maximum', maximum=0)
    subpack = copy.deepcopy(pack); subpack['rules'] = [simple]
    row = evaluate(subpack, data_project, root)['checks'][0]
    if reasons:
        row['reasons'] = (row['reasons'] if row['status']=='pending' else [])+reasons
        row['status'] = 'pending'
    row['condition_checks'] = comparisons
    row['binding_status'] = 'sourced_assertions_only'
    row['pending_engineering_checks'] = ['actual pump duty and system head/curve correspondence',
        'duplicate-set arrangement, controls and installed/model identity', 'tank design outflow derivation and other plumbing requirements']
    return row
