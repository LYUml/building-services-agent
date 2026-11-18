"""Run the optional ACadSharp worker for source-bound DWG inventory."""
from collections import Counter
import json
import math
import os
from pathlib import Path
import subprocess

from . import workspace
from .source_refs import file_hash


def dxf_geometry(entity):
    dxf = entity.dxf
    kind = entity.dxftype()
    if kind == 'LINE':
        return dict(start=list(dxf.start), end=list(dxf.end))
    if kind == 'TEXT':
        return dict(text=dxf.text, insert=list(dxf.insert), height=dxf.height)
    if kind in ('ARC', 'CIRCLE'):
        result = dict(center=list(dxf.center), normal=list(dxf.extrusion), radius=dxf.radius)
        if kind == 'ARC':
            result.update(start_angle_rad=math.radians(dxf.start_angle), end_angle_rad=math.radians(dxf.end_angle))
        return result
    if kind == 'LWPOLYLINE':
        return dict(closed=entity.closed, elevation=dxf.elevation, constant_width=dxf.const_width,
                    normal=list(dxf.extrusion),
                    vertices=[[float(value) for value in point] for point in entity.get_points('xyseb')])
    return None


def equal_geometry(actual, expected, field=''):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(
            equal_geometry(actual[key], value, key) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            equal_geometry(a, b) for a, b in zip(actual, expected))
    if type(expected) in (int, float):
        if type(actual) not in (int, float) or not math.isfinite(actual):
            return False
        gap = actual - expected
        if field.endswith('_angle_rad'):
            return abs(math.remainder(gap, math.tau)) <= 1e-9
        return abs(gap) <= 1e-7
    return type(actual) is type(expected) and actual == expected


def compare_reference(entities, reference):
    import ezdxf

    expected = {entity.dxf.handle: entity for entity in ezdxf.readfile(reference).modelspace()}
    actual = {row['handle']: row for row in entities}
    differences = [dict(handle=handle, reason='missing_in_dwg') for handle in sorted(expected.keys() - actual.keys())]
    differences.extend(dict(handle=handle, reason='missing_in_dxf') for handle in sorted(actual.keys() - expected.keys()))
    geometry_count = 0
    for handle in sorted(actual.keys() & expected.keys()):
        row, entity = actual[handle], expected[handle]
        if row['type'] != entity.dxftype() or row['layer'] != entity.dxf.layer:
            differences.append(dict(handle=handle, reason='type_or_layer_differs'))
            continue
        geometry = dxf_geometry(entity)
        if geometry is not None:
            geometry_count += 1
        if not equal_geometry(row['geometry'], geometry):
            differences.append(dict(handle=handle, reason='geometry_differs'))
    return dict(correspondence_pass=not differences, matched_handle_count=len(actual.keys() & expected.keys()),
                geometry_compared_count=geometry_count, differences=differences,
                numeric_absolute_tolerance_drawing_units=1e-7, arc_angle_tolerance_rad=1e-9)


def host_file(name):
    path = Path(os.environ.get(name, ''))
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f'Set {name} to an absolute host runtime file')
    return path.resolve()


def run(source, out, reference_dxf=None):
    source, out = (Path(path).resolve() for path in (source, out))
    if not workspace.allowed(source) or not source.is_file() or source.suffix.lower() != '.dwg':
        raise ValueError('Select an existing DWG in the permitted workspace')
    if not workspace.intake_output(out) or out.exists() or out.suffix.lower() != '.json':
        raise ValueError('Use a fresh JSON report in the permitted workspace')
    reference = Path(reference_dxf).resolve() if reference_dxf is not None else None
    if reference is not None and (not workspace.allowed(reference) or not reference.is_file()
                                  or reference.suffix.lower() != '.dxf'):
        raise ValueError('Select an existing DXF reference in the permitted workspace')
    reference_hash = file_hash(reference) if reference is not None else None
    dotnet = host_file('BSA_ACADSHARP_DOTNET')
    worker = host_file('BSA_ACADSHARP_WORKER')
    source_hash, worker_hash = file_hash(source), file_hash(worker)
    completed = subprocess.run([str(dotnet), str(worker), str(source)], cwd=worker.parent,
                               capture_output=True, encoding='utf-8', timeout=120)
    if completed.returncode:
        raise ValueError(f'ACadSharp DWG reader failed (exit {completed.returncode}): {completed.stderr[:1000].strip()}')
    result = json.loads(completed.stdout)
    if (not isinstance(result, dict) or result.get('schema') != 'bsa.acadsharp-modelspace/1'
            or result.get('source_sha256') != source_hash or result.get('reader_version') != '3.8.35'
            or result.get('native_autocad_executed') is not False or result.get('design_accepted') is not False
            or not isinstance(result.get('entities'), list)):
        raise ValueError('ACadSharp report identity or scope differs from the selected input')
    entities = result['entities']
    if any(not isinstance(row, dict) or set(row) != {'handle', 'type', 'layer', 'geometry'}
           or not all(isinstance(row[k], str) and row[k] for k in ('handle', 'type', 'layer'))
           for row in entities) or len({row['handle'] for row in entities}) != len(entities):
        raise ValueError('ACadSharp entity inventory has invalid or duplicate identities')
    result['worker_sha256'] = worker_hash
    summary = {}
    if reference is not None:
        comparison = compare_reference(entities, reference)
        result['comparison'] = dict(reference_sha256=reference_hash, **comparison)
        summary = dict(correspondence_pass=comparison['correspondence_pass'],
                       difference_count=len(comparison['differences']))
    report = json.dumps(result, indent=2, allow_nan=False)
    if file_hash(source) != source_hash or file_hash(worker) != worker_hash:
        raise ValueError('DWG or ACadSharp worker changed during inventory')
    if reference is not None and file_hash(reference) != reference_hash:
        raise ValueError('DXF reference changed during inventory')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        stream.write(report)
    return dict(report=str(out), report_sha256=file_hash(out), source_sha256=source_hash,
                entity_count=len(entities), counts=dict(sorted(Counter(row['type'] for row in entities).items())),
                native_autocad_executed=False, design_accepted=False, **summary)
