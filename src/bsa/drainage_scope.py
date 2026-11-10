"""APP-164 2(d)/(e) floor selection only; not a drainage conformity check."""


def separate_discharge_floors(*, building_storeys, stack_scope,
                              scope_storeys=None, edition_basis=None,
                              works_basis=None, evidence=None):
    """Return relative floor offsets requiring separate discharge pipework.

    Offset zero means the floor where this stack discharges to a manhole,
    not an assumed ground-floor label. Never use stack served-floor count
    as building height. Podium/basement-only stacks need their own count.
    Applicability is supplied reviewed evidence, not inferred from today's date.
    """
    for name, value in [('building_storeys', building_storeys),
                        ('scope_storeys', scope_storeys)]:
        if value is not None and (type(value) is not int or value < 1):
            raise ValueError(name + ' must be a positive integer or unknown')
    if stack_scope not in (None, 'building', 'podium_only', 'basement_only'):
        raise ValueError('Explicit building/podium_only/basement_only scope required')
    if stack_scope == 'building' and scope_storeys is not None:
        raise ValueError('Building scope must use total building storeys')
    result = dict(status='pending', clause=None,
                  separate_discharge_floor_offsets=None,
                  building_storeys=building_storeys, stack_scope=stack_scope,
                  scope_storeys=scope_storeys, evidence=evidence,
                  edition_basis=edition_basis, works_basis=works_basis,
                  regulatory_compliance='not_established', design_accepted=False,
                  source='HK BD PNAP APP-164, November 2023, 2(d)/(e), footnote 5',
                  scope='Floor selection only; no fixture, route, geometry or discharge verification')
    reasons = []
    for name, value in [('edition_basis', edition_basis), ('works_basis', works_basis),
                        ('evidence', evidence)]:
        if not isinstance(value, str) or not value.strip():
            reasons.append('Missing reviewed ' + name)
    if stack_scope is None:
        reasons.append('Stack building/podium/basement scope unknown')
    count = building_storeys if stack_scope == 'building' else scope_storeys
    if count is None:
        reasons.append('Relevant total storey count unknown; served floors cannot substitute')
    if reasons:
        return result | dict(reasons=reasons)
    if count <= 3:
        return result | dict(status='outside_supported_height_band',
                             reasons=['2(d)/(e) height bands do not cover this count; other drainage requirements remain unresolved'])
    clause, offsets = ('2(d)', [0]) if count <= 20 else ('2(e)', [0, 1])
    return result | dict(status='selected', clause=clause,
                         separate_discharge_floor_offsets=offsets,
                         effective_storeys=count,
                         reasons=['Sanitary fitments, if any, on these floors require separate pipework discharging directly to a manhole'])
