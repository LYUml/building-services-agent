"""Scoped emergency accommodation assertions, not a photometric model binding."""
import copy
import math


def check(pack, rule, project, root):
    from .regulations import evaluate

    data = project.get('emergency_accommodation', {})
    if not isinstance(data, dict):
        data = {}
    reasons, comparisons = [], []

    def item(key):
        value = data.get(key)
        if not isinstance(value, dict) or not isinstance(value.get('source'), str) or not value['source'].strip():
            reasons.append('missing sourced emergency condition: ' + key)
            return {}
        return value

    for key in ('space_identity', 'assessment_method_basis', 'rated_duration_basis',
                'degradation_basis'):
        value = item(key).get('value')
        if not isinstance(value, str) or not value.strip():
            reasons.append('nonempty sourced description required: ' + key)
    for key in ('emergency_mode', 'floor_horizontal_assessment',
                'whole_area_minimum_assessed', 'entire_rated_duration_assessed'):
        value = item(key).get('value')
        if value is not True:
            reasons.append('supported assessment requires explicit true: ' + key)

    quantities = {}
    for key, unit in (('gross_area', 'm2'), ('minimum_illuminance', 'lx')):
        value = item(key)
        number = value.get('value')
        if (type(number) not in (int, float) or not math.isfinite(number)
                or number < 0 or (key == 'gross_area' and number == 0)
                or value.get('unit') != unit):
            reasons.append('invalid quantity/unit: ' + key)
        else:
            quantities[key] = number
    lamps = item('emergency_luminaire_ids').get('value')
    if (not isinstance(lamps, list) or not lamps
            or any(not isinstance(x, str) or not x.strip() for x in lamps)
            or len(set(lamps)) != len(lamps)):
        reasons.append('distinct nonempty emergency luminaire identities required')
        lamps = None
    if 'minimum_illuminance' in quantities:
        comparisons.append(dict(condition='minimum_floor_illuminance',
            value=quantities['minimum_illuminance'], minimum=2, unit='lx',
            passed=quantities['minimum_illuminance'] >= 2))
    if 'gross_area' in quantities and lamps is not None:
        triggered = quantities['gross_area'] > 8
        comparisons.append(dict(condition='two_luminaires_above_8_m2',
            gross_area_m2=quantities['gross_area'], triggered=triggered,
            count=len(lamps), passed=not triggered or len(lamps) >= 2))

    derived = copy.deepcopy(project)
    derived.setdefault('facts', {})[rule['metric']] = dict(
        value=sum(not c['passed'] for c in comparisons), unit='count',
        source='Derived from sourced emergency_accommodation assertions; not native photometry')
    simple = copy.deepcopy(rule)
    simple.update(method='prescriptive_maximum', maximum=0)
    subpack = copy.deepcopy(pack)
    subpack['rules'] = [simple]
    row = evaluate(subpack, derived, root)['checks'][0]
    if reasons and row['status'] != 'not_applicable':
        row['reasons'] = row.get('reasons', []) + reasons
        row['status'] = 'pending'
    row['condition_checks'] = comparisons
    row['binding_status'] = 'sourced_assertions_only'
    row['pending_engineering_checks'] = [
        'independent assessment-method and whole-floor/rated-duration evidence review',
        'native emergency photometry, fixture identities and gross-area correspondence',
        'other applicable standards, licensed-premises requirements and installation acceptance']
    return row
