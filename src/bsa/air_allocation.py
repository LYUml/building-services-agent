"""Compose classified load balance and explicit nearest-centre service allocation."""
import math
import json
import hashlib
from pathlib import Path
from .air_load import calculate
from .service_areas import allocate


def run(project_path, output):
    project_path, output = Path(project_path).resolve(), Path(output).resolve()
    raw = project_path.read_bytes()
    project = json.loads(raw.decode('utf-8-sig'))
    if set(project)-{'references'} != {'boundary', 'boundary_sha256', 'geometry_basis', 'terminals', 'load_inputs', 'turndown'}:
        raise ValueError('Exact allocation project fields required')
    references=reference_files(project_path,project)
    relative = project['boundary']
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('Relative boundary path required')
    boundary = (project_path.parent/relative).resolve()
    data = boundary.read_bytes()
    if hashlib.sha256(data).hexdigest() != project['boundary_sha256']:
        raise ValueError('Boundary source hash mismatch')
    if not isinstance(project['geometry_basis'], str) or not project['geometry_basis'].strip():
        raise ValueError('Geometry units and interpretation basis required')
    if output.exists() or any(output == p or output in p.parents for p in (project_path,boundary,*references)):
        raise ValueError('New output separate from inputs required')
    result = prepare(json.loads(data.decode('utf-8-sig')), project['terminals'],
                     project['load_inputs'], project['turndown'])
    if project_path.read_bytes() != raw or boundary.read_bytes() != data:
        raise ValueError('Inputs changed during allocation')
    if reference_files(project_path,project)!=references:raise ValueError('References changed during allocation')
    result.update(inputs={str(project_path):hashlib.sha256(raw).hexdigest(),
                          str(boundary):hashlib.sha256(data).hexdigest()},
                  geometry_basis=project['geometry_basis'])
    result['inputs'].update({str(p):sha for p,sha in references.items()})
    output.mkdir(parents=True)
    (output/'allocation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def reference_files(project_path,project):
    references=project.get('references',{})
    if not isinstance(references,dict):raise ValueError('Reference path/hash mapping required')
    result={}
    for relative,sha in references.items():
        if not isinstance(relative,str) or not relative.strip() or Path(relative).is_absolute():
            raise ValueError('Relative reference path required')
        p=(Path(project_path).parent/relative).resolve()
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
            raise ValueError('Allocation reference source hash mismatch')
        result[p]=sha
    return result


def prepare(boundary, terminals, load_inputs, turndown):
    if type(turndown) not in (int, float) or not math.isfinite(turndown) or not 0 < turndown <= 1:
        raise ValueError('Explicit turndown in (0,1] required')
    load = calculate(load_inputs)
    allocation = allocate(boundary, terminals, load_inputs['area']['value'])
    rows = []
    for cell in allocation['terminals']:
        fraction = cell['allocated_load_area_m2']/allocation['given_load_area_m2']
        flow = fraction*load['supply_flow_L_s']
        rows.append(dict(cell, maximum_flow_L_s=flow, minimum_flow_L_s=flow*turndown))
    area = math.fsum(r['allocated_load_area_m2'] for r in rows)
    flow = math.fsum(r['maximum_flow_L_s'] for r in rows)
    if not math.isclose(area, allocation['given_load_area_m2'], rel_tol=1e-10) or not math.isclose(flow, load['supply_flow_L_s'], rel_tol=1e-10):
        raise ValueError('Allocated area or flow does not conserve total')
    return dict(load=load, allocation=allocation, terminals=rows, turndown=turndown,
                checks=dict(allocated_area_m2=area, allocated_flow_L_s=flow,
                            area_conserved=True, flow_conserved=True),
                scope='Uniform allowance allocated by nearest-centre area; not spatial load simulation, duct routing, air coverage or ADPI acceptance',
                design_accepted=False)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project');parser.add_argument('--out',required=True)
    args=parser.parse_args();result=run(args.project,args.out)
    print(len(result['terminals']), 'terminal allocations calculated; design acceptance pending')
