"""Fail-closed reader for a single serial OpenFOAM 12 checkMesh log.

Native checks retain their own thresholds. This is not a mesh or CFD engine.
"""
import re


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
