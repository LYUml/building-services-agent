"""Compare observed native pipe geometry to stored creation intent, not source truth."""
import math
from .engine import ProjectError


def audit_pipe(pipe, tolerance_m):
    if type(tolerance_m) not in (int, float) or not math.isfinite(tolerance_m) or tolerance_m <= 0:
        raise ProjectError('Finite positive comparison tolerance required')
    provenance = pipe.get('creation_provenance')
    if provenance is None:
        return dict(status='pending', reasons=['no_creation_provenance'])
    if not isinstance(provenance, dict) or provenance.get('schema_version') != 1:
        raise ProjectError('Unsupported creation provenance')
    request = provenance.get('creation_request')
    if not isinstance(request, dict) or not isinstance(request.get('Source'), str) or not request['Source'].strip():
        raise ProjectError('Missing stored source declaration')

    def positive(value):
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ProjectError('Invalid pipe dimension')
        return value

    def point(value):
        if not isinstance(value, list) or len(value) != 3 or any(
                type(x) not in (int, float) or not math.isfinite(x) for x in value):
            raise ProjectError('Invalid pipe endpoint')
        return value

    reasons = []
    original = provenance.get('original_element_unique_id')
    if not isinstance(original, str) or not original:
        raise ProjectError('Missing original identity')
    if original != pipe.get('unique_id') or provenance.get('element_identity_matches') is not True:
        reasons.append('original_identity_mismatch')
    endpoints = pipe.get('endpoints_m')
    if not isinstance(endpoints, list) or len(endpoints) != 2:
        raise ProjectError('Two measured endpoints required')
    observed = [point(p) for p in endpoints]
    expected = [point(request.get(k)) for k in ('StartMetres', 'EndMetres')]
    if math.dist(*expected) <= 0:
        raise ProjectError('Stored pipe request has zero length')
    # Revit curve orientation may reverse without changing the physical segment.
    endpoint_error = min(max(math.dist(observed[i], expected[i]) for i in (0, 1)),
                         max(math.dist(observed[i], expected[1-i]) for i in (0, 1)))
    if endpoint_error > tolerance_m:
        reasons.append('endpoints_changed')
    if pipe.get('curve_kind') != 'Line':
        reasons.append('curve_is_not_original_straight_segment')
    if abs(positive(pipe.get('length_m')) - math.dist(*expected)) > tolerance_m:
        reasons.append('length_changed')
    if abs(positive(pipe.get('diameter_m')) - positive(request.get('DiameterMetres'))) > tolerance_m:
        reasons.append('diameter_changed')
    for observed_key, request_key in (('type_unique_id', 'PipeTypeUniqueId'),
                                      ('system_type_unique_id', 'SystemTypeUniqueId'),
                                      ('level_unique_id', 'LevelUniqueId')):
        if not isinstance(request.get(request_key), str) or not request[request_key]:
            raise ProjectError('Missing original type/system/level identity')
        if pipe.get(observed_key) != request[request_key]:
            reasons.append(observed_key + '_changed_or_missing')
    return dict(status='fail' if reasons else 'consistent', reasons=reasons,
                endpoint_error_m=endpoint_error, source_declaration=request['Source'],
                source_verified=False, design_accepted=False,
                scope='Current observations versus original request; no approval of revisions or source inputs')
