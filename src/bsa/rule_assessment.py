"""Common conservative projection of existing scoped jurisdiction results."""
from .module_contract import validate


def assessment(checks,pack,producer_hash,coordinate_frame):
    rules={r['id']:r for r in pack['rules']};rows=[]
    for entity,result in sorted(checks.items()):
        for row in result['checks']:
            rule=rules[row['id']];source=pack['sources'][rule['source_id']]
            original=row['status'];state='pass' if original=='pass' else 'fail' if original=='review_required' else 'pending'
            rows.append(dict(entity_id=entity,rule_id=row['id'],status=state,original_status=original,
                source_id=rule['source_id'],source_sha256=source['sha256'],edition=source['edition'],
                clause=rule['clause'],scope=row['scope']))
    states=[r['status'] for r in rows]
    return validate(dict(schema='bsa.rule-assessment/1',coordinate_frame=coordinate_frame,jurisdiction=pack['jurisdiction'],rule_pack=pack['id'],
        producer_sha256=producer_hash,status='fail' if 'fail' in states else 'pending' if 'pending' in states else 'pass',
        coverage=[dict(entity_id=entity,implemented=result['coverage']['implemented'],pending=result['coverage']['pending']) for entity,result in sorted(checks.items())],
        checks=rows,coverage_complete=False,regulatory_compliance='not_established',design_accepted=False))
