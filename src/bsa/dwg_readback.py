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
        return dict(start=list(dxf.start), end=list(dxf.end), normal=list(dxf.extrusion), thickness=dxf.thickness)
    if kind == 'POINT':
        return dict(location=list(dxf.location))
    if kind == 'TEXT':
        return dict(text=dxf.text, insert=list(dxf.insert), height=dxf.height, width_factor=dxf.width,
                    rotation_angle_rad=math.radians(dxf.rotation), oblique_angle_rad=math.radians(dxf.oblique),
                    normal=list(dxf.extrusion), horizontal_alignment=dxf.halign, vertical_alignment=dxf.valign,
                    alignment_point=list(dxf.align_point) if dxf.halign or dxf.valign else None, style=dxf.style)
    if kind == 'INSERT':
        return dict(block_name=dxf.name, insert=list(dxf.insert), normal=list(dxf.extrusion),
                    scale=[dxf.xscale, dxf.yscale, dxf.zscale], rotation_angle_rad=math.radians(dxf.rotation),
                    row_count=dxf.row_count, column_count=dxf.column_count,
                    row_spacing=dxf.row_spacing, column_spacing=dxf.column_spacing)
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


def compare_reference(entities, insunits, reference):
    import ezdxf

    document = ezdxf.readfile(reference)
    modelspace = document.modelspace()
    expected = {entity.dxf.handle: entity for entity in modelspace}
    duplicated = {handle for handle, count in Counter(entity.dxf.handle for entity in modelspace).items()
                  if count > 1}
    actual = {row['handle']: row for row in entities}
    differences = [dict(handle=handle, reason='duplicate_handle_in_dxf') for handle in sorted(duplicated)]
    differences.extend(dict(handle=handle, reason='missing_in_dwg') for handle in sorted(expected.keys() - actual.keys()))
    differences.extend(dict(handle=handle, reason='missing_in_dxf') for handle in sorted(actual.keys() - expected.keys()))
    if document.units != insunits:
        differences.append(dict(reason='drawing_units_differ', dwg_insunits=insunits, dxf_insunits=document.units))
    geometry_count = 0
    identity_only_counts = Counter()
    matched = (actual.keys() & expected.keys()) - duplicated
    for handle in sorted(matched):
        row, entity = actual[handle], expected[handle]
        identity = dict(type=entity.dxftype(), layer=entity.dxf.layer)
        fields = [key for key, value in identity.items() if row[key] != value]
        if fields:
            differences.append(dict(handle=handle, reason='type_or_layer_differs', fields=fields))
            continue
        geometry = dxf_geometry(entity)
        if geometry is not None:
            geometry_count += 1
        else:
            identity_only_counts[identity['type']] += 1
        observed = row['geometry']
        if not equal_geometry(observed, geometry):
            fields = ['geometry']
            if isinstance(observed, dict) and isinstance(geometry, dict):
                fields = [key for key in sorted(observed.keys() | geometry.keys())
                          if key not in observed or key not in geometry
                          or not equal_geometry(observed[key], geometry[key], key)]
            differences.append(dict(handle=handle, reason='geometry_differs', fields=fields))
    return dict(correspondence_pass=not differences, matched_handle_count=len(matched),
                geometry_compared_count=geometry_count,
                identity_only_counts_by_type=dict(sorted(identity_only_counts.items())), differences=differences,
                numeric_absolute_tolerance_drawing_units=1e-7, angle_tolerance_rad=1e-9)


def host_file(name):
    path = Path(os.environ.get(name, ''))
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f'Set {name} to an absolute host runtime file')
    return path.resolve()


def run(source, out, reference_dxf=None, *, expected_hashes=None):
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
    source_hash = file_hash(source)
    if expected_hashes is not None and (source_hash, reference_hash) != expected_hashes:
        raise ValueError('DWG or DXF differs from the verified revision artifact hashes')
    dotnet = host_file('BSA_ACADSHARP_DOTNET')
    worker = host_file('BSA_ACADSHARP_WORKER')
    worker_hash = file_hash(worker)
    reader = worker.with_name('ACadSharp.dll')
    if not reader.is_file():
        raise ValueError('Build the DWG worker with its locked adjacent ACadSharp.dll')
    reader_hash = file_hash(reader)
    completed = subprocess.run([str(dotnet), str(worker), str(source)], cwd=worker.parent,
                               capture_output=True, encoding='utf-8', timeout=120)
    if completed.returncode:
        raise ValueError(f'ACadSharp DWG reader failed (exit {completed.returncode}): {completed.stderr[:1000].strip()}')
    result = json.loads(completed.stdout)
    if isinstance(result, dict) and result.get('schema') == 'bsa.acadsharp-modelspace/1':
        raise ValueError('Rebuild the ACadSharp DWG worker from the current checkout (inventory schema v2 required)')
    if (not isinstance(result, dict) or result.get('schema') != 'bsa.acadsharp-modelspace/2'
            or result.get('source_sha256') != source_hash or result.get('reader_version') != '3.8.35'
            or result.get('reader_sha256') != reader_hash
            or result.get('native_autocad_executed') is not False or result.get('design_accepted') is not False
            or type(result.get('insunits')) is not int or not isinstance(result.get('entities'), list)):
        raise ValueError('ACadSharp report identity or scope differs from the selected input')
    entities = result['entities']
    if any(not isinstance(row, dict) or set(row) != {'handle', 'type', 'layer', 'geometry'}
           or not all(isinstance(row[k], str) and row[k] for k in ('handle', 'type', 'layer'))
           for row in entities) or len({row['handle'] for row in entities}) != len(entities):
        raise ValueError('ACadSharp entity inventory has invalid or duplicate identities')
    result['worker_sha256'] = worker_hash
    summary = {}
    if reference is not None:
        comparison = compare_reference(entities, result['insunits'], reference)
        result['comparison'] = dict(reference_sha256=reference_hash, **comparison)
        summary = dict(reference_sha256=reference_hash, correspondence_pass=comparison['correspondence_pass'],
                       difference_count=len(comparison['differences']),
                       geometry_compared_count=comparison['geometry_compared_count'],
                       identity_only_counts_by_type=comparison['identity_only_counts_by_type'])
    report = json.dumps(result, indent=2, allow_nan=False)
    if file_hash(source) != source_hash or file_hash(worker) != worker_hash or file_hash(reader) != reader_hash:
        raise ValueError('DWG, worker or ACadSharp library changed during inventory')
    if reference is not None and file_hash(reference) != reference_hash:
        raise ValueError('DXF reference changed during inventory')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        stream.write(report)
    return dict(report=str(out), report_sha256=file_hash(out), source_sha256=source_hash,
                worker_sha256=worker_hash, reader_sha256=reader_hash,
                entity_count=len(entities), insunits=result['insunits'],
                counts=dict(sorted(Counter(row['type'] for row in entities).items())),
                native_autocad_executed=False, design_accepted=False, **summary)
