"""Source-inherited VAV connection schedule; conditional flows and planar lengths only."""
import argparse
import csv
import json
import math
import tempfile
from pathlib import Path

import ezdxf
from .air_terminal_drawing import from_workflow
from .cli import digest
from .duct_sheet_native import compare, run as native_run
from .workspace import allowed


HEADERS = ['VAV', 'Diffuser outlets', 'Qmax L/s', 'Qmin L/s', 'Min plan m', 'Max plan m', 'Outlets']
EDGES = [8, 32, 120, 154, 188, 220, 252, 280]
SCOPE = 'Conditional inherited allocation; straight XY centre-to-centre lengths only. Installed flex lengths, hardware, ADPI and regulatory/design acceptance remain pending.'


def rows_from(review, allocation):
    terminals = allocation['terminals']
    by_id = {t['id']: t for t in terminals}
    if len(by_id) != len(terminals):
        raise ValueError('Duplicate terminal identity')
    used = set(); groups = set(); rows = []
    for g in review['groups']:
        if g['id'] in groups:
            raise ValueError('Duplicate VAV identity')
        groups.add(g['id'])
        routes = g['routes']
        if not routes or g['outlet_count'] != len(routes):
            raise ValueError('Outlet coverage mismatch')
        for r in routes:
            if r['terminal'] not in by_id or r['terminal'] in used:
                raise ValueError('Missing or repeated terminal membership')
            used.add(r['terminal'])
            if type(r['plan_length_m']) not in (int, float) or not math.isfinite(r['plan_length_m']) or r['plan_length_m'] <= 0:
                raise ValueError('Positive finite planar length required')
        members = [by_id[r['terminal']] for r in routes]
        for t in members:
            for k in ('maximum_flow_L_s', 'minimum_flow_L_s'):
                if type(t[k]) not in (int, float) or not math.isfinite(t[k]) or t[k] <= 0:
                    raise ValueError('Positive finite inherited flows required')
            if t['minimum_flow_L_s'] > t['maximum_flow_L_s']:
                raise ValueError('Minimum flow exceeds maximum')
        qmax = math.fsum(t['maximum_flow_L_s'] for t in members)
        qmin = math.fsum(t['minimum_flow_L_s'] for t in members)
        if not math.isclose(qmax, g['maximum_flow_L_s'], rel_tol=1e-12, abs_tol=0):
            raise ValueError('Group flow differs from inherited allocation')
        rows.append(dict(id=g['id'], terminals=[r['terminal'] for r in routes],
                         maximum_flow_L_s=qmax, minimum_flow_L_s=qmin,
                         minimum_plan_length_m=min(r['plan_length_m'] for r in routes),
                         maximum_plan_length_m=max(r['plan_length_m'] for r in routes),
                         outlet_count=len(routes), routes=routes))
    if used != set(by_id) or not 1 <= len(rows) <= 20:
        raise ValueError('Complete terminal coverage and 1..20 groups required for this sheet')
    return rows


def cells(row):
    return [row['id'], ', '.join(row['terminals']), f"{row['maximum_flow_L_s']:.1f}",
            f"{row['minimum_flow_L_s']:.1f}", f"{row['minimum_plan_length_m']:.3f}",
            f"{row['maximum_plan_length_m']:.3f}", str(row['outlet_count'])]


def author(rows, path):
    doc = ezdxf.new('R2018'); doc.units = 4
    doc.layers.new('BSA_VAV_TABLE', dxfattribs={'color': 7})
    m = doc.modelspace(); labels = []
    def text(value, x, y, height=2.3):
        entity = m.add_text(value, dxfattribs=dict(layer='BSA_VAV_TABLE', height=height, insert=(x, y)))
        labels.append(dict(handle=entity.dxf.handle, text=value, insert=[x, y, 0], height=height))
    def line(a, b):
        return m.add_line(a, b, dxfattribs=dict(layer='BSA_VAV_TABLE'))
    text('VAV CONNECTION SCHEDULE', 8, 184, 5)
    text('Conditional design flows and saved native-plan connections', 8, 175, 3)
    text('Flows: L/s | Lengths: m, straight XY centre-to-centre | Drawing units: mm | A4 landscape 1:1', 8, 167)
    top = 158; bottom = top - 6 * (len(rows) + 1)
    for x in EDGES: line((x, bottom), (x, top))
    for index in range(len(rows) + 2):
        y = top - index * 6; line((EDGES[0], y), (EDGES[-1], y))
    for index, values in enumerate([HEADERS] + [cells(r) for r in rows]):
        for col, value in enumerate(values):
            # Bound ordinary ASCII table labels rather than clipping/condensing text silently.
            if not value.isascii() or len(value) * 2.3 * .8 > EDGES[col+1] - EDGES[col] - 3:
                raise ValueError('Table text exceeds bounded cell; a different layout is required')
            text(value, EDGES[col]+1.5, top-index*6-4.1)
    text('Plan lengths are lower bounds, not installed flex lengths; elevation, bends and slack remain unknown.', 8, 23)
    text('VAV symbols and group labels do not establish selected hardware or physical outlet-port geometry.', 8, 18)
    text('Source allocation, room load, ADPI, installation and Hong Kong applicability remain under review.', 8, 13)
    ref = line((8, 6), (108, 6)); text('100 mm print reference', 112, 5)
    doc.saveas(path)
    return labels, ref.dxf.handle


def run(plan, workflow, native_task, layers, output, autocad=None):
    plan, workflow, output = (Path(p).resolve() for p in (plan, workflow, output))
    if not all(allowed(p) for p in (plan, workflow, output)):
        raise ValueError('Explicit host-selected project workspace required')
    if output.exists() or workflow in output.parents or output in workflow.parents or output == workflow or output == plan or output in plan.parents:
        raise ValueError('Fresh output outside immutable workflow and source plan required')
    output.mkdir(parents=True)
    review = from_workflow(plan, workflow, native_task, output/'connections.json', layers=layers)
    allocation_path = workflow/review['lineage'][-1]/'allocation.json'
    allocation = json.loads(allocation_path.read_text(encoding='utf-8'))
    rows = rows_from(review, allocation)
    dxf = output/'VAV Connection Schedule.dxf'
    labels, reference = author(rows, dxf)
    with (output/'VAV Connection Schedule.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f); writer.writerow(HEADERS); writer.writerows(cells(r) for r in rows)
    settings = dict(source_sha256=digest(dxf), layers=['BSA_VAV_TABLE'], sheet=dict(
        source='Paper-space connection table; 100 mm generated print reference, not building geometry scale',
        window_drawing_units=[0, 0, 290, 200], scale_denominator=1,
        reference_handle=reference, pdf_tolerance_mm=.2))
    (output/'native-settings.json').write_text(json.dumps(settings, indent=2), encoding='utf-8')
    native = native_run(dxf, output/'native-settings.json', output/'native', autocad) if autocad else None
    files = [p for p in output.rglob('*') if p.is_file()]
    result = dict(plan=str(plan), workflow=str(workflow), native_task=native_task, layers=layers,
                  plan_sha256=digest(plan), workflow_sha256=digest(workflow/'workflow.json'),
                  generator_sha256=digest(Path(__file__)), rows=rows, labels=labels,
                  group_count=len(rows), terminal_count=sum(r['outlet_count'] for r in rows),
                  maximum_flow_L_s=math.fsum(r['maximum_flow_L_s'] for r in rows),
                  minimum_flow_L_s=math.fsum(r['minimum_flow_L_s'] for r in rows),
                  artifacts={str(p.relative_to(output)): digest(p) for p in files},
                  native_reopen_pass=bool(native and native['native_reopen_pass']),
                  visual_review='pending', scope=SCOPE, design_accepted=False)
    (output/'schedule.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def verify(output):
    output = Path(output).resolve()
    if not allowed(output): raise ValueError('Host-selected project required')
    saved = json.loads((output/'schedule.json').read_text(encoding='utf-8'))
    for relative, sha in saved['artifacts'].items():
        path = (output/relative).resolve()
        if not path.is_relative_to(output) or digest(path) != sha:
            raise ValueError('Schedule artifact changed')
    plan, workflow = Path(saved['plan']), Path(saved['workflow'])
    if not allowed(plan) or not allowed(workflow) or digest(plan) != saved['plan_sha256'] or digest(workflow/'workflow.json') != saved['workflow_sha256'] or digest(Path(__file__)) != saved['generator_sha256']:
        raise ValueError('Schedule source or method changed')
    # Reconstruct actual saved native-symbol membership and line lengths, not cached group totals.
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        review = from_workflow(plan, workflow, saved['native_task'], Path(temp)/'connections.json', layers=saved['layers'])
        allocation = json.loads((workflow/review['lineage'][-1]/'allocation.json').read_text(encoding='utf-8'))
        rows = rows_from(review, allocation)
        reconstructed = Path(temp)/'table.dxf'
        labels, _ = author(rows, reconstructed)
        if rows != saved['rows'] or labels != saved['labels']:
            raise ValueError('Saved rows or labels differ from reconstructed source')
        for key, value in dict(group_count=len(rows), terminal_count=sum(r['outlet_count'] for r in rows),
                               maximum_flow_L_s=math.fsum(r['maximum_flow_L_s'] for r in rows),
                               minimum_flow_L_s=math.fsum(r['minimum_flow_L_s'] for r in rows)).items():
            if saved[key] != value: raise ValueError('Saved aggregate differs from source')
        compare(reconstructed, output/'VAV Connection Schedule.dxf', ['BSA_VAV_TABLE'])
        if saved['native_reopen_pass']:
            compare(reconstructed, output/'native/reopened/source-export.dxf', ['BSA_VAV_TABLE'])
    return dict(source_reconstruction_pass=True, group_count=len(rows), terminal_count=saved['terminal_count'],
                native_reopen_pass=saved['native_reopen_pass'], scope=SCOPE, design_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('run')
    for name in ('plan', 'workflow', 'native_task'): p.add_argument(name)
    for name in ('supply', 'vav', 'terminal', 'flex'): p.add_argument('--'+name+'-layer', required=True)
    p.add_argument('--out', required=True); p.add_argument('--autocad')
    p = sub.add_parser('verify'); p.add_argument('output')
    a = parser.parse_args()
    result = verify(a.output) if a.command == 'verify' else run(a.plan, a.workflow, a.native_task,
        {k: getattr(a, k+'_layer') for k in ('supply','vav','terminal','flex')}, a.out, a.autocad)
    print(json.dumps({k:result[k] for k in ('group_count','terminal_count','native_reopen_pass','design_accepted')}))
