"""Necessary planar extent checks for a saved tee/transition composition on native source routes."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from . import rectangular_tee as tee
from . import rectangular_transition as transition
from . import rectangular_tee_transitions as composition
from .cli import digest
from .workspace import allowed

ROOT = Path(__file__).resolve().parents[2]


def assess(review, spec, children, binding):
    if not isinstance(binding, dict) or set(binding) != {'source', 'node', 'arms'} or not isinstance(binding['source'], str) or not binding['source'].strip():
        raise ValueError('Exact source/node/arm binding required')
    arms = binding['arms']
    if not isinstance(arms, dict) or set(arms) != set(tee.NAMES) or any(not isinstance(v, str) or not v.strip() for v in arms.values()) or len(set(arms.values())) != 3:
        raise ValueError('Three unique explicit arm-to-section bindings required')
    if review.get('source_correspondence_pass') is not True: raise ValueError('Source-correspondent node review required')
    matches = [n for n in review['nodes'] if n['node'] == binding['node']]
    if len(matches) != 1 or matches[0]['degree'] != 3: raise ValueError('Exactly one three-section source node required')
    node = matches[0]; incidents = {i['section']: i for i in node['incidents']}
    if len(incidents) != 3 or set(incidents) != set(arms.values()): raise ValueError('Exact node incident-section coverage required')
    point = node['point_m']; origin = spec['placement']['origin_m']
    if math.dist(origin[:2], point[:2]) > 1e-8: raise ValueError('Fitting origin differs from source node XY')
    frames = tee.port_frames(spec); rows = []
    for arm, sid in arms.items():
        incident = incidents[sid]; frame = transition.port_frames(children[arm])['end'] if arm in children else frames[arm]
        direction = incident['outward_unit_vector']
        if not np.allclose(frame[:3, 2], direction, atol=1e-8, rtol=0) or abs(frame[2, 2]) > 1e-8:
            raise ValueError('Fitting outward arm differs from source planar ray')
        expected_direction = 'SINK' if incident['role'] == 'incoming' else 'SOURCE'
        if spec['port_directions'][arm] != expected_direction: raise ValueError('Declared supply direction differs from source tree')
        width, height = children[arm]['end_section_m'] if arm in children else [spec['internal_width_m'], spec['internal_height_m']]
        if not np.allclose([width, height], [incident['width_m'], incident['height_m']], atol=1e-10, rtol=0): raise ValueError('External fitting section differs from selected source size')
        delta = frame[:2, 3]-np.array(point[:2]); projected = float(np.dot(delta, direction[:2]))
        if projected <= 0 or np.linalg.norm(delta-projected*np.array(direction[:2])) > 1e-8: raise ValueError('Fitting end is not on its source forward ray')
        length = incident['source_centreline_length_m']
        if type(length) not in (int, float) or not math.isfinite(length) or length <= 0: raise ValueError('Positive source centreline length required')
        rows.append(dict(arm=arm, section=sid, source_line_handle=incident['line_handle'], width_m=width, height_m=height,
            outward_reach_m=projected, source_centreline_length_m=length, remaining_centreline_m=length-projected,
            extent_within_source_segment=projected <= length, external_end_xy_m=frame[:2, 3].tolist()))
    passed = all(r['extent_within_source_segment'] for r in rows)
    return dict(node=binding['node'], binding_source=binding['source'], arms=rows, plan_extent_check_pass=passed,
        status='review_required' if passed else 'fail', installation_elevation_verified=False, section_roll_verified=False,
        neighbouring_end_fitting_trim_verified=False, design_accepted=False,
        pending=['Opposite-end fitting consumption on each source segment', 'Actual installation elevation and section roll',
            'Outer-envelope/obstacle and product-joint clearances', 'Sheet-normal construction/product selection', 'Fitting loss and full network/requirement acceptance'],
        scope='Necessary XY source-ray/end-size/extent checks for one local fitting composition; remaining centreline is not installed straight length or proof of available space')


def run(plan, workflow, native_task, project, model_directory, binding_path, out):
    from .duct_junction_review import from_workflow
    from .workflow import verify
    plan, workflow, project, model_directory, binding_path, out = [Path(p).resolve() for p in (plan, workflow, project, model_directory, binding_path, out)]
    project, data, source, spec, children = composition.prepare(project)
    paths = [plan, project, source, binding_path, model_directory/'assembly.json', model_directory/'assembly.ifc']
    if out.exists() or not all(allowed(p) for p in (plan,workflow,project,model_directory,binding_path,out)) or any(out == p or out in p.parents for p in paths) or any(out.is_relative_to(p) or p.is_relative_to(out) for p in (workflow, model_directory)):
        raise ValueError('New selected workspace review directory outside source/model/workflow required')
    bundle = json.loads((model_directory/'assembly.json').read_text(encoding='utf-8'))
    if bundle['inputs'].get(str(project)) != digest(project) or bundle['ifc_sha256'] != digest(model_directory/'assembly.ifc'):
        raise ValueError('Saved composition does not match project or IFC')
    artifacts = []
    for name, sha in bundle['source_artifacts'].items():
        artifact = (model_directory/name).resolve()
        if not artifact.is_relative_to(model_directory) or not artifact.is_file() or digest(artifact) != sha: raise ValueError('Component artifact changed')
        artifacts.append(artifact)
    if any(not Path(p).is_file() or digest(Path(p)) != sha for p, sha in bundle['inputs'].items()): raise ValueError('Composition source changed')
    pins = {str(p): digest(p) for p in paths+artifacts+[Path(p) for p in bundle['inputs']]+[Path(__file__)]}
    fresh = composition.inspect(model_directory/'assembly.ifc', spec, data, children)
    out.mkdir(parents=True)
    review = from_workflow(plan, workflow, native_task, out/'junction-review.json')
    result = assess(review, spec, children, json.loads(binding_path.read_text(encoding='utf-8')))
    if any(digest(Path(p)) != sha for p, sha in pins.items()) or not verify(workflow)['integrity_pass']: raise ValueError('Source/model/workflow changed during fit review')
    result.update(inputs=pins, junction_review_sha256=digest(out/'junction-review.json'),
        assembly_checks=fresh, source_workflow_integrity_pass=True, saved_model_reinspected=True)
    (out/'fit-review.json').write_text(json.dumps(result, indent=2), encoding='utf-8'); return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('plan', 'workflow', 'native_task', 'project', 'model_directory', 'binding'): parser.add_argument(arg)
    parser.add_argument('--out', required=True); args = parser.parse_args()
    result = run(args.plan, args.workflow, args.native_task, args.project, args.model_directory, args.binding, args.out)
    print(result['status'], result['plan_extent_check_pass']); raise SystemExit(2 if result['plan_extent_check_pass'] else 1)
