"""Fail-closed reader for a single serial OpenFOAM 12 checkMesh log.

Native checks retain their own thresholds. This is not a mesh or CFD engine.
"""
import re
import math


def assess_check_mesh(log, returncode):
    """Require a completed, unambiguous native success, not just exit zero."""
    if not isinstance(log, str) or type(returncode) is not int:
        raise ValueError('Text log and integer process return code required')
    failures = [int(n) for n in re.findall(r'^Failed (\d+) mesh checks\.$', log, re.M)]
    successes = len(re.findall(r'^Mesh OK\.$', log, re.M))
    completed = bool(re.search(r'^End\s*$', log, re.M))
    fatal = bool(re.search(r'FOAM FATAL|Generating stack trace|Backtrace:', log))
    native_pass = (returncode == 0 and completed and successes == 1
                   and not failures and not fatal)
    return {
        'returncode': returncode,
        'completed': completed,
        'reported_failed_checks': failures,
        'native_mesh_checks_passed': native_pass,
        'engineering_accepted': False,
    }


def assess_layer_coverage(patches, requested_layers):
    """Screen declared native wall-face counts separately from mesh quality.

    Each patch supplies face_count and values (a uniform number or one number
    per face). The caller binds these to the native field/patch and source hashes.
    Face-count coverage does not establish area, layer height, yPlus or pressure.
    """
    if type(requested_layers) is not int or requested_layers < 1:
        raise ValueError('Positive integer requested layer count required')
    if not isinstance(patches, dict) or not patches:
        raise ValueError('Explicit nonempty wall patch set required')
    reviewed = {}
    total = present = complete = 0
    for name, patch in patches.items():
        if not isinstance(name, str) or not name:
            raise ValueError('Named wall patches required')
        if not isinstance(patch, dict) or set(patch) != {'face_count', 'values'}:
            raise ValueError('Explicit face_count and native values required')
        count = patch['face_count']
        if type(count) is not int or count < 1:
            raise ValueError('Positive native patch face count required')
        raw = patch['values']
        uniform = type(raw) in (int, float)
        if not uniform and (not isinstance(raw, list) or len(raw) != count):
            raise ValueError('Native nonuniform field must match patch face count')
        values = [raw] if uniform else raw
        for value in values:
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or value < 0 or int(value) != value):
                raise ValueError('Finite nonnegative integer native layer counts required')
        multiplier = count if uniform else 1
        any_layers = sum(value > 0 for value in values) * multiplier
        requested = sum(value >= requested_layers for value in values) * multiplier
        reviewed[name] = {
            'face_count': count,
            'faces_with_any_layers': any_layers,
            'faces_with_requested_layers': requested,
            'any_layer_face_fraction': any_layers / count,
            'requested_layer_face_fraction': requested / count,
        }
        total += count
        present += any_layers
        complete += requested
    return {
        'scope': 'Declared native wall-face counts only; caller binds patch/field/source evidence',
        'requested_layers': requested_layers,
        'patches': reviewed,
        'wall_faces': total,
        'any_layer_face_fraction': present / total,
        'requested_layer_face_fraction': complete / total,
        'all_wall_faces_have_requested_layers': complete == total,
        'wall_area_coverage_verified': False,
        'actual_first_layer_height_verified': False,
        'yPlus_verified': False,
        'engineering_accepted': False,
    }
