"""Scoped sourced T/L screening, never a measured ADPI or comfort prediction."""
import math


def screen(lookup, *, criterion, room_load_W_m2, facts):
    required={'room_load_verified','product_category_verified','lengths_verified','installation_verified','edition_selected'}
    if set(facts)!=required or any(type(v) not in (bool,type(None)) for v in facts.values()):
        raise ValueError('Exact Boolean/unknown applicability facts required')
    if set(criterion)!={'source','room_load_range_W_m2','ratio_range'} or not isinstance(criterion['source'],str) or not criterion['source'].strip():
        raise ValueError('Explicit criterion source and bounds required')
    def bounds(values):
        if not isinstance(values,list) or len(values)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values) or values[0]>values[1]:
            raise ValueError('Positive finite ordered bounds required')
        return values
    load_low,load_high=bounds(criterion['room_load_range_W_m2'])
    low,high=bounds(criterion['ratio_range'])
    if room_load_W_m2 is not None and (type(room_load_W_m2) not in (int,float) or not math.isfinite(room_load_W_m2) or room_load_W_m2<=0):
        raise ValueError('Positive finite room load or unknown required')
    missing=[k for k,v in facts.items() if v is None]
    rejected=[k for k,v in facts.items() if v is False]
    in_range=None if room_load_W_m2 is None else load_low<=room_load_W_m2<=load_high
    eligibility='inapplicable' if rejected or (facts['room_load_verified'] is True and in_range is False) else 'pending' if missing or room_load_W_m2 is None else 'eligible'
    actions={
        'room_load_verified':'Establish the room sensible load from source-backed room calculations; keep preliminary cooling allowances separate.',
        'product_category_verified':'Document correspondence between the specified diffuser and the selected source category.',
        'lengths_verified':'Verify characteristic lengths against walls, outlet midplanes or intersecting jets under the selected source definition.',
        'installation_verified':'Verify ceiling and installation conditions against the selected source and actual project.',
        'edition_selected':'Record the selected criterion edition and resolve differences from other sources.'}
    requests=[dict(code='applicability_fact_unknown' if facts[k] is None else 'applicability_fact_rejected',
                   fact=k,action=actions[k]) for k in sorted(missing+rejected)]
    if room_load_W_m2 is None:
        requests.append(dict(code='room_load_missing',action=actions['room_load_verified']))
    elif in_range is False:
        requests.append(dict(code='criterion_load_domain_mismatch',
            supplied_load_W_m2=room_load_W_m2,source_range_W_m2=[load_low,load_high],
            load_verified=facts['room_load_verified'],
            action='Resolve the room load and criterion applicability with source evidence; do not clamp the load, extrapolate the interval or silently replace the criterion.'))
    rows=[];ids=set()
    for terminal in lookup['terminals']:
        if terminal['id'] in ids:raise ValueError('Unique terminal identities required')
        ids.add(terminal['id'])
        for direction,item in terminal['directions'].items():
            if set(item['cases'])!={'maximum','minimum'}:raise ValueError('Both maximum and minimum cases required')
            for case,result in item['cases'].items():
                ratio=result['ratio']
                if ratio is not None and (type(ratio) not in (int,float) or not math.isfinite(ratio) or ratio<=0):raise ValueError('Positive finite ratio required')
                inside=None if ratio is None else low<=ratio<=high
                status='not_evaluated' if eligibility!='eligible' else 'fail' if result['status']!='within_catalogue' or inside is not True else 'within_sourced_ratio_range'
                rows.append(dict(terminal=terminal['id'],direction=direction,case=case,ratio=ratio,ratio_in_range=inside,status=status))
    if not rows:raise ValueError('Nonempty terminal cases required')
    return dict(criterion=criterion,facts=facts,room_load_W_m2=room_load_W_m2,load_in_source_range=in_range,
        applicability=eligibility,missing_facts=missing,rejected_facts=rejected,data_requests=requests,cases=rows,
        all_ratios_within_scope=eligibility=='eligible' and all(r['status']=='within_sourced_ratio_range' for r in rows),
        ADPI_verified=False,design_accepted=False,
        scope='Supplied source interval and declared applicability only; not measured/predicted ADPI, source authentication or full comfort acceptance')
