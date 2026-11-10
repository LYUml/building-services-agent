"""Bind externally sourced rectangular fitting tables to a fresh saved-chain case."""
import argparse
import html
import importlib.metadata
import itertools
import json
import math
from pathlib import Path
import re

import ifcopenshell
import numpy as np
from scipy.interpolate import RegularGridInterpolator

from . import duct_chain_analysis as analysis
from .duct_fitting_chain import shape_hash
from .cli import digest

ROOT = Path(__file__).resolve().parents[2]
QUANTITIES = {'outlet_to_inlet_flow_ratio', 'outlet_to_inlet_area_ratio',
    'outlet_to_inlet_width_ratio', 'outlet_to_inlet_height_ratio',
    'outlet_to_inlet_velocity_ratio', 'inlet_aspect_ratio', 'outlet_aspect_ratio'}


def render(result, case):
    def esc(v): return html.escape(str(v))
    tables = []
    for row in result['table_results']:
        a, b = [case['port_flows'][row[k]] for k in ('inlet_port_guid', 'outlet_port_guid')]
        q = row['native_quantities']
        values = [a['source_node'], a['source_section']+' → '+b['source_section'],
            f"{q['outlet_to_inlet_flow_ratio']:.6f}", f"{q['outlet_to_inlet_velocity_ratio']:.6f}",
            row['reason'], 'Unavailable' if row['coefficient'] is None else f"{row['coefficient']:.6g}"]
        tables.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    paths = []
    for row in result['boundary_paths']:
        port = case['port_flows'][row['outlet_port_guid']]
        values = [port['source_section'], f"{row['known_straight_friction_Pa']:.5f}", row['unresolved_fitting_path_count'], 'Pending']
        paths.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    citations = ''.join('<li>'+esc(s['citation'])+'; edition '+esc(s['edition'])+'</li>' for s in result['sources'].values())
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Duct Fitting Data Review</title><style>body{font:16px/1.5 Arial;color:#20343c;max-width:1250px;margin:35px auto;padding:0 20px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #cbd4d8;padding:10px;text-align:left}th{background:#eaf0f2}.pending{background:#fff0d2;border-left:5px solid #b47016;padding:16px}</style><h1>Duct Fitting Data Review</h1><p class="pending"><strong>Complete pressure assessment pending.</strong> '+str(result['calculated_table_paths'])+' table paths calculated out of '+str(result['unique_fitting_paths'])+' unique fitting paths. '+str(result['unsupplied_table_paths'])+' paths have no supplied table. Physical applicability and source transcription remain review-required even when interpolation succeeds.</p><h2>Native quantities and bounded source queries</h2><p>Each query uses actual saved port geometry and inherited design flow. Missing table cells stay unknown; no clamping or extrapolation is used.</p><table><tr><th>Source node</th><th>Source flow path</th><th>Outlet/inlet flow</th><th>Outlet/inlet velocity</th><th>Query result</th><th>Coefficient</th></tr>'+''.join(tables)+'</table><h2>Separate outlet paths</h2><table><tr><th>Outlet section</th><th>Known separate straight Pa</th><th>Unresolved fitting paths</th><th>Complete pressure</th></tr>'+''.join(paths)+'</table><p>Zero supplied fitting contribution does not mean zero fitting loss. Partial sums are not lower bounds; parallel paths must not be added. Critical path and fan duty remain unavailable.</p><h2>Sources</h2><ul>'+citations+'</ul><p>Coefficient reference port,friction convention,applicability note and source location are retained per table in <a href="fitting-data.json">the numerical record</a>. Tables themselves are not reproduced here. <a href="analysis/index.html">Saved flow and straight-friction analysis</a>.</p></html>'


def number(x):
    return type(x) in (int, float) and math.isfinite(x)


def prepare(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT): raise ValueError('Repository-local fitting basis required')
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if set(data) != {'sources', 'tables'} or not isinstance(data['sources'], dict) or not data['sources'] or not isinstance(data['tables'], list) or not data['tables']:
        raise ValueError('Nonempty source map and fitting tables required')
    pins = {str(path): digest(path)}
    for source in data['sources'].values():
        if set(source) != {'document', 'sha256', 'citation', 'edition'} or any(not isinstance(source[k], str) or not source[k].strip() for k in source):
            raise ValueError('Exact source document,hash,citation,edition required')
        document = (path.parent/source['document']).resolve()
        if not document.is_relative_to(ROOT) or not document.is_file() or digest(document) != source['sha256']:
            raise ValueError('Source document hash or repository location differs')
        pins[str(document)] = source['sha256']
    keys = set()
    required = {'source_id', 'citation_location', 'classification', 'applicability_note', 'friction_scope',
        'product_guid', 'geometry_sha256', 'inlet_port_guid', 'outlet_port_guid', 'reference_port_guid', 'axes', 'coefficients'}
    for table in data['tables']:
        if set(table) != required or any(not isinstance(table[k], str) or not table[k].strip() for k in required-{'axes', 'coefficients'}):
            raise ValueError('Exact source-linked fitting-table record required')
        if table['source_id'] not in data['sources'] or not re.fullmatch('[0-9a-f]{64}', table['geometry_sha256']):
            raise ValueError('Known source and native body hash required')
        if table['classification'] not in ('published correlation', 'manufacturer data', 'synthetic') or table['friction_scope'] not in ('local_dynamic_only', 'whole_fitting_including_internal_straights'):
            raise ValueError('Explicit source classification and friction convention required')
        key = tuple(table[k] for k in ('product_guid', 'inlet_port_guid', 'outlet_port_guid'))
        if key in keys: raise ValueError('Duplicate fitting path table')
        keys.add(key)
        axes = table['axes']
        if not isinstance(axes, list) or not 1 <= len(axes) <= 3: raise ValueError('One to three bounded native quantity axes required')
        names = set()
        for axis in axes:
            if not isinstance(axis, dict) or set(axis) != {'quantity', 'values'} or axis['quantity'] not in QUANTITIES or axis['quantity'] in names:
                raise ValueError('Unique supported native quantity axes required')
            names.add(axis['quantity']); values = axis['values']
            if not isinstance(values, list) or len(values) < 2 or not all(number(v) and v > 0 for v in values) or any(b <= a for a, b in zip(values, values[1:])):
                raise ValueError('Finite positive strictly increasing table axes required')
        def check_grid(grid, dimension):
            if dimension == len(axes):
                if grid is not None and not number(grid): raise ValueError('Finite signed coefficients or explicit null required')
            elif not isinstance(grid, list) or len(grid) != len(axes[dimension]['values']):
                raise ValueError('Coefficient grid shape differs from axes')
            else:
                for child in grid: check_grid(child, dimension+1)
        check_grid(table['coefficients'], 0)
    return data, pins


def lookup(table, quantities):
    """Use SciPy only within a fully populated support cell, without clamping."""
    indexes = []; axes = []; query = []
    for axis in table['axes']:
        values = np.asarray(axis['values']); q = quantities[axis['quantity']]
        if q < values[0] or q > values[-1]: return dict(status='pending', reason='query outside table bounds', coefficient=None)
        exact = np.flatnonzero(values == q)
        if len(exact): chosen = [int(exact[0])]
        else:
            high = int(np.searchsorted(values, q)); chosen = [high-1, high]
        indexes.append(chosen); axes.append(values[chosen]); query.append(q)
    grid = np.asarray(table['coefficients'], dtype=float)
    support = grid[np.ix_(*indexes)]
    if not np.isfinite(support).all(): return dict(status='pending', reason='query support contains unpublished or null cells', coefficient=None)
    # Collapsing exact axes avoids NaN*zero contamination from unrelated blank cells.
    value = float(RegularGridInterpolator(tuple(axes), support, bounds_error=True)(np.asarray([query]))[0])
    if not math.isfinite(value): raise ValueError('Interpolated coefficient is nonfinite')
    return dict(status='calculated', coefficient=value, support_indexes=[list(p) for p in itertools.product(*indexes)],
        reason='Bounded interpolation only; engineering applicability and source transcription remain review-required')


def calculate(model, case, data):
    requested = {(r['product_guid'], r['inlet_port_guid'], r['outlet_port_guid']): r for r in case['missing_fitting_path_losses']}
    results = {}
    for table in data['tables']:
        key = tuple(table[k] for k in ('product_guid', 'inlet_port_guid', 'outlet_port_guid'))
        if key not in requested: raise ValueError('Table must identify an actual saved fitting path')
        obj = model.by_guid(key[0]); a, b = [case['port_flows'][g] for g in key[1:]]
        ref = case['port_flows'].get(table['reference_port_guid'])
        if shape_hash(obj) != table['geometry_sha256'] or ref is None or ref['owner_guid'] != obj.GlobalId:
            raise ValueError('Native fitting geometry or owned reference port differs')
        quantities = dict(outlet_to_inlet_flow_ratio=b['flow_m3_s']/a['flow_m3_s'],
            outlet_to_inlet_area_ratio=b['width_m']*b['height_m']/(a['width_m']*a['height_m']),
            outlet_to_inlet_width_ratio=b['width_m']/a['width_m'], outlet_to_inlet_height_ratio=b['height_m']/a['height_m'],
            outlet_to_inlet_velocity_ratio=b['actual_velocity_m_s']/a['actual_velocity_m_s'],
            inlet_aspect_ratio=a['width_m']/a['height_m'], outlet_aspect_ratio=b['width_m']/b['height_m'])
        value = lookup(table, quantities)
        value.update(product_guid=key[0], inlet_port_guid=key[1], outlet_port_guid=key[2],
            native_quantities=quantities, reference_port_guid=table['reference_port_guid'],
            reference_velocity_pressure_Pa=ref['actual_velocity_pressure_Pa'],
            signed_tabulated_contribution_Pa=None if value['coefficient'] is None else value['coefficient']*ref['actual_velocity_pressure_Pa'],
            source_id=table['source_id'], citation_location=table['citation_location'], classification=table['classification'],
            applicability_note=table['applicability_note'], friction_scope=table['friction_scope'], physical_applicability_verified=False)
        if value['signed_tabulated_contribution_Pa'] is not None and not math.isfinite(value['signed_tabulated_contribution_Pa']):
            raise ValueError('Tabulated pressure contribution overflowed')
        results[key] = value
    paths = []
    for path in case['boundary_paths']:
        contributions = []; missing = 0
        for step in path['steps']:
            if step['kind'] != 'fitting': continue
            key = tuple(step[k] for k in ('product_guid', 'inlet_port_guid', 'outlet_port_guid'))
            value = results.get(key, {}).get('signed_tabulated_contribution_Pa')
            if value is None: missing += 1
            else: contributions.append(value)
        paths.append(dict(inlet_port_guid=path['inlet_port_guid'], outlet_port_guid=path['outlet_port_guid'],
            known_straight_friction_Pa=path['known_straight_friction_Pa'], supplied_table_contribution_Pa=math.fsum(contributions),
            unresolved_fitting_path_count=missing,
            tabulated_plus_separate_straight_Pa=None if missing else path['known_straight_friction_Pa']+math.fsum(contributions),
            complete_total_pressure_drop_Pa=None))
    return dict(status='pending', table_results=list(results.values()), boundary_paths=paths,
        unique_fitting_paths=len(requested), calculated_table_paths=sum(r['coefficient'] is not None for r in results.values()),
        unsupplied_table_paths=len(requested)-len(results), sources=data['sources'], pressure_budget_complete=False,
        critical_path=None, design_accepted=False,
        scope='Source-linked table interpolation with actual native-port reference pressures only. Source transcription, physical applicability, friction inclusion, fitting interaction/joints, boundary pressure requirements and complete engineering acceptance remain unverified. Partial sums are not lower bounds or fan duties.')


def run(project, chain_directory, basis, out):
    basis, out = Path(basis).resolve(), Path(out).resolve()
    data, pins = prepare(basis)
    chain_directory = Path(chain_directory).resolve()
    if out.exists() or not out.is_relative_to(ROOT) or out.is_relative_to(chain_directory) or chain_directory.is_relative_to(out) or any(Path(p).is_relative_to(out) for p in pins):
        raise ValueError('New repository-local output outside immutable sources required')
    if importlib.metadata.version('scipy') != '1.18.1': raise ValueError('Pinned SciPy1.18.1 required')
    import scipy.interpolate._rgi as rgi
    for p in (Path(__file__), Path(rgi.__file__)):
        pins[str(p.resolve())] = digest(p)
    case = analysis.run(project, chain_directory, out/'analysis')
    result = calculate(ifcopenshell.open(str(chain_directory/'chain.ifc')), case, data)
    if any(digest(Path(p)) != sha for p, sha in pins.items()): raise ValueError('Table basis,source or engine changed during interpolation')
    result.update(inputs=pins, analysis_sha256=digest(out/'analysis/analysis.json'), scipy_version='1.18.1',
        same_saved_ifc_verified=case['same_saved_ifc_verified'])
    (out/'fitting-data.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (out/'index.html').write_text(render(result, case), encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('project'); p.add_argument('chain_directory'); p.add_argument('--basis', required=True); p.add_argument('--out', required=True)
    args = p.parse_args(); r = run(args.project, args.chain_directory, args.basis, args.out)
    print(r['status'], r['calculated_table_paths'], 'calculated table paths;', r['unique_fitting_paths'], 'unique fitting paths'); raise SystemExit(2)
