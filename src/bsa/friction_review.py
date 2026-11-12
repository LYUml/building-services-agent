"""Review requests projected from an already verified common friction payload.

No engine, regulation threshold, physical diagnosis or automatic repair.
"""

def requests(payload):
    if payload.get('schema') != 'bsa.straight-friction-components/1':
        return []
    rows=[]
    for terminal, component in sorted(payload['components'].items()):
        identity=dict(terminal=terminal,stub_guid=component['stub_guid'],space_guid=component['space_guid'])
        rows.append(dict(identity,code='flow_development_applicability_unverified',
            evidence=dict(length_over_diameter=component['length_over_diameter'],
                          native_length_m=component['native_length_m'],
                          native_internal_diameter_m=component['native_internal_diameter_m']),
            requested='Provide an applicable source-backed flow-development and entry/joint treatment for the actual geometry; do not treat the theoretical fully-developed component as total short-duct pressure loss.'))
        bore=component['inherited_stub_basis']['internal_diameter_m']
        if bore['classification'] in ('assumed','design_choice'):
            rows.append(dict(identity,code='assumed_bore_requires_product_evidence',
                evidence=dict(native_internal_diameter_m=component['native_internal_diameter_m'],inherited_bore_basis=bore),
                requested='Obtain applicable product and joint evidence for the actual clear bore; nominal connection size or an exterior neck dimension does not establish hydraulic internal diameter. Preserve the original assumption until a source-backed revision is executed.'))
        for condition,case in sorted(component['cases'].items()):
            if case['status']=='pending':
                rows.append(dict(identity,condition=condition,code='transitional_flow_method_required',
                    evidence=dict(reynolds=case['reynolds'],regime=case['regime']),
                    requested='Provide a justified method applicable to this retained flow regime; keep friction unknown until supported.'))
    rows.append(dict(code='air_property_basis_review_required',
        evidence=dict(fluid_basis=payload['fluid_basis'],density_by_terminal={k:v['inherited_density'] for k,v in sorted(payload['components'].items())}),
        requested='Review the declared air state, viscosity, roughness and inherited room density with their original classifications and sources; numerical completion does not verify applicability.'))
    rows.append(dict(code='whole_system_pressure_incomplete',
        evidence=dict(whole_system_pressure_complete=payload['whole_system_pressure_complete']),
        requested='Provide verified network topology, physical joints and component losses before whole-path pressure and fan-duty analysis; do not sum parallel branch pressures or mix terminal static and total pressure.'))
    return rows
