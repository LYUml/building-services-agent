"""Research-only operating-flow envelope for quantified log-chart interpolation error."""
import copy
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .rectangular_fan import run as analyse,validate_curve

COVERAGE='native log-log LINE interpolation only'


def curves(curve,basis):
    validate_curve(curve)
    if not isinstance(basis,dict) or set(basis)!={'source','relative_pressure_excess','coverage','manufacturer_performance_uncertainty'} or basis['coverage']!=COVERAGE or basis['manufacturer_performance_uncertainty'] is not None:raise ProjectError('explicit interpolation-only basis with unresolved manufacturer uncertainty required')
    error=basis['relative_pressure_excess']
    if not isinstance(basis['source'],str) or not basis['source'].strip() or type(error) not in (int,float) or not math.isfinite(error) or error<0:raise ProjectError('sourced finite nonnegative relative interpolation error required')
    low=copy.deepcopy(curve);high=copy.deepcopy(curve)
    key='interpolation/envelope'
    if key in low['sources']:raise ProjectError('reserved interpolation provenance namespace')
    low['sources'][key]='Derived lower pressure envelope, not manufacturer data: '+basis['source']
    low['source']=key
    for point in low['points']:point['total_pressure_rise_pa']/=1+error
    validate_curve(low)
    return low,high


def run(project,curve,basis,out):
    paths=[Path(p).resolve() for p in (project,curve,basis)];out=Path(out).resolve()
    if out.exists() or any(out==p or out in p.parents for p in paths):raise ProjectError('new separate interpolation research output required')
    before={str(p):digest(p) for p in paths}
    p,c,b=[json.loads(path.read_text(encoding='utf-8-sig')) for path in paths]
    low,high=curves(c,b);out.mkdir(parents=True)
    results={}
    for label,curve_data in [('lower',low),('upper',high)]:
        file=out/(label+'-curve.json');file.write_text(json.dumps(curve_data,indent=2),encoding='utf-8')
        results[label]=analyse(paths[0],file,out/label)
    converged=all(r['status']=='converged' for r in results.values())
    interval=None
    if converged:
        interval=[results['lower']['flow_bracket_m3_s'][0],results['upper']['flow_bracket_m3_s'][1]]
        if interval[0]>interval[1]:raise ProjectError('operating-flow envelope ordering failed')
    numerical=converged and all(r['calculated_checks_pass'] for r in results.values())
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('interpolation research inputs changed')
    result=dict(status='pending' if numerical else 'fail',inputs=before,inputs_unchanged=True,basis=b,interpolation_only_checks_pass=numerical,calculated_checks_pass=False,operating_flow_envelope_m3_s=interval,
        endpoints={k:dict(status=r['status'],checks=r.get('checks'),operating_point=r.get('operating_point'),flow_bracket_m3_s=r.get('flow_bracket_m3_s')) for k,r in results.items()},
        scope='Numerical envelope for native graph interpolation only; cannot release a manufacturer selection or design',
        solver_ready=False,design_accepted=False,pending=['Source axis/graph rounding and manufacturer performance tolerance','CSV endpoint errors if rounded coordinates are substituted','Installation/stable interval, actual product, viscosity and motor evidence','Native fan equipment and full Hong Kong/engineering acceptance'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'interpolation-envelope.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result
