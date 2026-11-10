"""Source-classified rule-of-thumb cooling and constant-property supply airflow."""
import math


UNITS = dict(area='m2', cooling_allowance='W/m2', sensible_fraction='1',
             density='kg/m3', specific_heat='J/(kg K)', temperature_difference='K')


def calculate(inputs):
    if set(inputs) != set(UNITS):
        raise ValueError('Exact area, allowance, sensible fraction and air-condition inputs required')
    values = {}
    for key, unit in UNITS.items():
        row = inputs[key]
        if not isinstance(row, dict) or set(row) != {'value', 'unit', 'source', 'classification'}:
            raise ValueError('Every input needs value, unit, source and classification')
        v = row['value']
        if type(v) not in (int, float) or not math.isfinite(v) or v <= 0 or row['unit'] != unit:
            raise ValueError('Positive finite quantities with exact units required')
        if not isinstance(row['source'], str) or not row['source'].strip() or row['classification'] not in ('given', 'measured', 'assumed', 'secondary_transcription'):
            raise ValueError('Explicit source and supported classification required')
        values[key] = v
    if values['sensible_fraction'] > 1:
        raise ValueError('Sensible fraction cannot exceed one')
    total = values['area']*values['cooling_allowance']
    sensible = total*values['sensible_fraction']
    denominator = values['density']*values['specific_heat']*values['temperature_difference']
    if not math.isfinite(denominator) or denominator <= 0:
        raise ValueError('Thermal transport denominator outside numeric range')
    flow = sensible/denominator
    if any(not math.isfinite(v) or v <= 0 for v in (total, sensible, flow, flow*1000)):
        raise ValueError('Calculated result outside numeric range')
    return dict(inputs={k: dict(v) for k,v in inputs.items()},
                total_cooling_kW_thermal=total/1000,
                sensible_trial_kW_thermal=sensible/1000,
                supply_flow_m3_s=flow, supply_flow_L_s=flow*1000,
                room_sensible_load_verified=False, design_accepted=False,
                scope='Rule-of-thumb total cooling and prescribed sensible-fraction air balance; not electrical demand, detailed load simulation or established room load for ADPI')
