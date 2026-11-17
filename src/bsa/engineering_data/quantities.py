"""Explicit conversions for supported exchange quantities, not a unit parser."""
import math

# Electrical/thermal semantics are deliberately distinct even in SI.
UNITS = {
    'm': ('length', 'm', 1), 'mm': ('length', 'm', .001),
    'm2': ('area', 'm2', 1),
    'L/s': ('volume_flow', 'm3/s', .001), 'm3/s': ('volume_flow', 'm3/s', 1),
    'kW thermal': ('thermal_power', 'W thermal', 1000),
    'W thermal': ('thermal_power', 'W thermal', 1),
    'kW electrical': ('electrical_real_power', 'W electrical', 1000),
    'W electrical': ('electrical_real_power', 'W electrical', 1),
    'VA': ('apparent_power', 'VA', 1), 'kVA': ('apparent_power', 'VA', 1000),
    'A': ('current', 'A', 1), 'V': ('voltage', 'V', 1),
    'Pa': ('pressure', 'Pa', 1),
    '1': ('ratio', '1', 1), '%': ('ratio', '1', .01),
}


def quantity(value, unit, pointer, classification='calculated'):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Finite explicit numerical quantity required')
    if unit not in UNITS:
        raise ValueError('Unsupported or ambiguous engineering unit: '+str(unit))
    dimension, si_unit, factor = UNITS[unit]
    converted = value*factor
    if not math.isfinite(converted):
        raise ValueError('SI quantity overflow')
    return dict(value=value, unit=unit, dimension=dimension, si_value=converted,
                si_unit=si_unit, classification=classification, source_pointer=pointer)


def validate_quantity(row):
    expected = quantity(row['value'], row['unit'], row['source_pointer'], row['classification'])
    if row.keys() != expected.keys() or any(row[k] != expected[k] for k in expected):
        raise ValueError('Quantity unit, dimension or SI conversion differs')

