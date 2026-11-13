"""Compare declared raster round-duct points with the existing friction engine."""
import argparse
from importlib.metadata import version
import json
import math
from pathlib import Path
import tempfile

from . import raster_chart_points,duct_equivalent
from .cli import digest
from .workspace import allowed

ROOT=Path(__file__).resolve().parents[2]


def run(basis,out):
    basis,out=Path(basis).resolve(),Path(out).resolve()
    if not allowed(basis) or not allowed(out) or out.exists():raise ValueError('Selected workspace and new output required')
    before=digest(basis);data=json.loads(basis.read_text(encoding='utf-8-sig'))
    if set(data)!={'points_project','points_result','points_result_sha256','air','air_basis','diameters'}:raise ValueError('Exact chart comparison basis required')
    def local(name):
        if not isinstance(name,str) or Path(name).is_absolute():raise ValueError('Relative source path required')
        path=(basis.parent/name).resolve()
        if not allowed(path) or not path.is_file():raise ValueError('Selected existing source required')
        return path
    project,record=[local(data[key]) for key in ('points_project','points_result')]
    if out.is_relative_to(record.parent):raise ValueError('Comparison output must stay outside saved point results')
    if digest(record)!=data['points_result_sha256']:raise ValueError('Raster point record changed')
    saved=json.loads(record.read_text(encoding='utf-8'))
    # Recompute the complete source-bound record instead of trusting edited values.
    with tempfile.TemporaryDirectory(dir=ROOT/'runs') as temporary:
        replay=raster_chart_points.run(project,Path(temporary)/'replayed')
    if saved!=replay:raise ValueError('Saved raster points differ from current source replay')
    if saved['axes']['x']['unit']!='L/s' or saved['axes']['y']['unit']!='Pa/m':raise ValueError('Round-duct comparison requires L/s and Pa/m axes')
    air=data['air'];air_basis=data['air_basis']
    if set(air)!={'density_kg_m3','viscosity_Pa_s','roughness_m'} or set(air_basis)!=set(air):raise ValueError('Explicit source-classified air conditions required')
    for key,value in air.items():
        if type(value) not in (int,float) or not math.isfinite(value) or value<0 or (key!='roughness_m' and value==0):raise ValueError('Finite supported air properties required')
        item=air_basis[key]
        if set(item)!={'classification','basis'} or item['classification'] not in ('given','assumed','measured') or not isinstance(item['basis'],str) or not item['basis'].strip():raise ValueError('Source classification and substantive property basis required')
    diameters=data['diameters']
    if not isinstance(diameters,list) or not diameters:raise ValueError('Source-labelled diameters required')
    by_id={}
    for row in diameters:
        if set(row)!={'point_id','diameter_m','source_label','identity_observation'}:raise ValueError('Exact diameter and identity observation required')
        if any(not isinstance(row[k],str) or not row[k].strip() for k in ('point_id','source_label','identity_observation')) or row['point_id'] in by_id:raise ValueError('Unique source-labelled point identities required')
        d=row['diameter_m']
        if type(d) not in (int,float) or not math.isfinite(d) or d<=0:raise ValueError('Positive finite diameter in metres required')
        by_id[row['point_id']]=row
    if set(by_id)!={p['id'] for p in saved['points']}:raise ValueError('Every raster point needs exactly one diameter interpretation')
    pins={**saved['inputs'],str(basis):before,str(record):data['points_result_sha256'],
          str(Path(__file__)):digest(Path(__file__)),str(Path(duct_equivalent.__file__)):digest(Path(duct_equivalent.__file__))}
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Output must preserve every input')
    rows=[]
    for point in saved['points']:
        interpretation=by_id[point['id']];d=interpretation['diameter_m']
        # A computational square realizes the prescribed equivalent diameter.
        # It is not a proposed rectangular physical duct or an authored model.
        side=d/(1.30/(2**.25))
        def gradient(flow_L_s):
            if flow_L_s<=0:raise ValueError('Positive source chart flow required')
            result=duct_equivalent.calculate(flow_m3_s=flow_L_s/1000,width_m=side,height_m=side,**air)
            if not math.isclose(result['equivalent_diameter_m'],d,rel_tol=1e-12,abs_tol=0):raise ValueError('Equivalent-diameter correspondence failed')
            return result['friction_Pa_m']
        if point['y_range'][0]<=0:raise ValueError('Positive source chart gradient required')
        center=gradient(point['x']);ends=[gradient(v) for v in point['x_range']];low,high=min(ends),max(ends)
        rows.append(dict(**interpretation,manual_point=point,equation_gradient_Pa_m=center,
            flow_endpoint_equation_gradients_Pa_m=ends,equation_endpoint_range_Pa_m=[low,high],
            center_relative_difference=(center-point['y'])/point['y'],
            endpoint_ranges_overlap=max(low,point['y_range'][0])<=min(high,point['y_range'][1])))
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Comparison source or method changed')
    result=dict(inputs=pins,air=air,air_basis=air_basis,points=rows,fluids_version=version('fluids'),
        source_image_derivation_verified=False,curve_identity_verified=False,scanned_chart_readings_accepted=False,design_accepted=False,
        scope='Existing equivalent-round engine evaluated at declared diameter and flow endpoints; interval overlap is descriptive, not curve identity, full uncertainty coverage, source-method equivalence or sizing acceptance. Computational square is not physical design.')
    out.mkdir(parents=True);(out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('basis');parser.add_argument('--out',required=True)
    args=parser.parse_args();result=run(args.basis,args.out)
    print(len(result['points']),'manual chart points compared; source curve and engineering acceptance remain unverified')
    return 0


if __name__=='__main__':raise SystemExit(main())
