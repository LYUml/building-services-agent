"""Independent equation checks of a saved,source-native duct sizing schedule."""
import argparse
import html
import json
import math
from pathlib import Path

from .cli import digest
from .workspace import allowed
from .delivery import context
from .duct_junction_review import from_workflow

ROOT = Path(__file__).resolve().parents[2]
RELATIVE = 1e-10
RESIDUAL = 1e-10


def positive(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value <= 0:
        raise ValueError('Finite positive numerical quantities required')
    return value


def section(inputs, air, recorded):
    """Check identities and Colebrook residual without another friction solver."""
    q,w,h=[positive(inputs[k]) for k in ('flow_m3_s','width_m','height_m')]
    rho,mu=[positive(air[k]) for k in ('density_kg_m3','viscosity_Pa_s')]
    roughness=air['roughness_m']
    if type(roughness) not in (int,float) or not math.isfinite(roughness) or roughness<0:
        raise ValueError('Finite nonnegative roughness required')
    de=1.30*(w*h)**0.625/(w+h)**0.25
    actual=q/(w*h); circular=4*q/(math.pi*de*de)
    reynolds=rho*circular*de/mu
    if reynolds<4000:raise ValueError('Supported turbulent equivalent-round domain required')
    factor=positive(recorded['darcy_factor'])
    lhs=1/math.sqrt(factor)
    residual=lhs+2*math.log10(roughness/(3.7*de)+2.51/(reynolds*math.sqrt(factor)))
    expected=dict(equivalent_diameter_m=de,actual_velocity_m_s=actual,
        equivalent_round_velocity_m_s=circular,reynolds=reynolds,
        friction_Pa_m=factor*rho*circular*circular/(2*de),aspect_ratio=max(w,h)/min(w,h))
    for key,value in expected.items():
        if not math.isclose(positive(recorded[key]),value,rel_tol=RELATIVE,abs_tol=1e-12):
            raise ValueError('Saved schedule equation mismatch: '+key)
    if abs(residual)>RESIDUAL:raise ValueError('Saved Darcy factor fails independent Colebrook residual')
    return dict(**expected,darcy_factor=factor,colebrook_residual=residual)


def calculate(schedule, project):
    if schedule.get('status')!='pass' or schedule['air']!=project['air']:
        raise ValueError('Passing source-air schedule required')
    original={r['id']:r for r in project['sections']}
    rows=schedule['sections']
    if not rows or len(original)!=len(project['sections']) or len(rows)!=len(original) or {r['id'] for r in rows}!=set(original):
        raise ValueError('Exact source section coverage required')
    results=[];candidate_count=0;maximum_residual=0.
    for row in rows:
        source=original[row['id']]
        if row['limits']!=source['limits'] or row.get('failures'):
            raise ValueError('Source criteria or passing selected state differs')
        limits=source['limits']
        if set(limits)!={'actual_velocity_m_s','friction_Pa_m','aspect_ratio'}:
            raise ValueError('Explicit supported section limits required')
        for limit in limits.values():positive(limit)
        checked=section(row['inputs'],schedule['air'],row['calculation'])
        maximum_residual=max(maximum_residual,abs(checked['colebrook_residual']))
        if 'flow_m3_s' in source and source['flow_m3_s']!=row['inputs']['flow_m3_s']:
            raise ValueError('Prescribed source flow differs')
        if any(checked[k]>value for k,value in limits.items()):
            raise ValueError('Selected section exceeds declared source criteria')
        if 'candidates' in source:
            selection=row['selection'];candidates=selection['candidates']
            by_id={r['id']:r for r in candidates};supplied={r['id']:r for r in source['candidates']}
            if len(by_id)!=len(candidates) or len(supplied)!=len(source['candidates']) or set(by_id)!=set(supplied):
                raise ValueError('Exact unique source candidate coverage required')
            eligible=[]
            for name,candidate in by_id.items():
                declared=supplied[name]
                if any(candidate[k]!=declared[k] for k in ('width_m','height_m')):
                    raise ValueError('Source candidate dimensions differ')
                geometry=dict(flow_m3_s=row['inputs']['flow_m3_s'],width_m=declared['width_m'],height_m=declared['height_m'])
                values=section(geometry,schedule['air'],candidate['calculation'])
                maximum_residual=max(maximum_residual,abs(values['colebrook_residual']))
                failures=[k for k,limit in limits.items() if values[k]>limit]
                if set(failures)!=set(candidate['failures']):
                    raise ValueError('Saved candidate failure classification differs')
                if not failures:eligible.append(candidate)
            eligible.sort(key=lambda r:(r['width_m']*r['height_m'],r['width_m']+r['height_m'],r['id']))
            if not eligible or selection['feasible_count']!=len(eligible) or selection['selected']!=eligible[0]:
                raise ValueError('Saved candidate ranking differs from independent eligibility and source preference')
            chosen=eligible[0]
            if any(row['inputs'][k]!=chosen[k] for k in ('width_m','height_m')) or row['calculation']!=chosen['calculation']:
                raise ValueError('Selected schedule differs from ranked candidate')
            candidate_count+=len(candidates)
        elif any(row['inputs'][k]!=source[k] for k in ('width_m','height_m')):
            raise ValueError('Prescribed source dimensions differ')
        results.append(dict(id=row['id'],inputs=row['inputs'],independent_quantities=checked,
            source_criteria=limits,selected_source_criteria_pass=True))
    return dict(status='review_required',section_count=len(results),candidate_count=candidate_count,
        independent_equation_checks_pass=True,source_candidate_ranking_pass=True if candidate_count else None,
        numerical_relative_tolerance=RELATIVE,colebrook_absolute_residual_tolerance=RESIDUAL,
        software_tolerances_are_engineering_acceptance_bands=False,sections=results,
        maximum_absolute_colebrook_residual=maximum_residual,
        scanned_chart_readings_verified=False,physical_applicability_verified=False,design_accepted=False,
        scope='Independent algebra,stored Colebrook residual and source candidate/limit correspondence only. Original source chart edition/reading,air-property and geometry applicability,manufacturability,acoustics,installation and complete engineering acceptance remain separate.')


def render(result):
    esc=lambda v:html.escape(str(v))
    rows=[]
    for row in result['sections']:
        q=row['independent_quantities'];p=row['inputs']
        values=[row['id'],f"{p['flow_m3_s']*1000:.3f}",f"{p['width_m']*1000:g} × {p['height_m']*1000:g}",
            f"{q['equivalent_diameter_m']*1000:.3f}",f"{q['actual_velocity_m_s']:.5f}",
            f"{q['equivalent_round_velocity_m_s']:.5f}",f"{q['friction_Pa_m']:.7f}",f"{q['colebrook_residual']:.3g}"]
        rows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Duct sizing equation review</title><style>body{font:16px/1.5 Arial;color:#20343c;max-width:1250px;margin:32px auto;padding:0 18px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:8px;border:1px solid #cbd4d8;text-align:left}th{background:#edf2f4}.notice{background:#fff1d6;padding:16px;border-left:5px solid #a96a10}.table{overflow-x:auto}a{color:#075665}</style><h1>Duct sizing equation review</h1><p class="notice">Independent numerical review. Scanned chart readings,source applicability and full engineering acceptance remain pending. Numerical tolerances are software checks,not engineering acceptance bands.</p><p>'+str(result['section_count'])+' saved source sections and '+str(result['candidate_count'])+' source candidates checked. Actual rectangular velocity and equivalent-round chart velocity remain distinct. Colebrook factors are checked by their equation residual,without another friction solver.</p><div class="table"><table><tr><th>Section</th><th>Flow L/s</th><th>Size mm</th><th>Equivalent diameter mm</th><th>Actual m/s</th><th>Equivalent-round m/s</th><th>Friction Pa/m</th><th>Colebrook residual</th></tr>'+''.join(rows)+'</table></div><p>'+esc(result['scope'])+'</p><p><a href="review.json">Complete source-bound numerical record</a> · <a href="junction-review.json">Saved native/source correspondence</a></p></html>'


def run(plan,workflow,native_task,out):
    plan,workflow,out=[Path(p).resolve() for p in (plan,workflow,out)]
    source,record,integrity=context(plan,workflow)
    if not integrity['integrity_pass']:raise ValueError('Source workflow integrity failed')
    if out.exists() or not allowed(out) or out.is_relative_to(workflow) or workflow.is_relative_to(out) or plan.is_relative_to(out):
        raise ValueError('New repository output outside immutable source inputs required')
    pins={str(p):digest(p) for p in (plan,workflow/'workflow.json',Path(__file__),ROOT/'src/bsa/workspace.py')}
    junction=from_workflow(plan,workflow,native_task,out/'junction-review.json')
    schedule_id=junction['lineage'][-1]
    task=next(t for t in source['tasks'] if t['id']==schedule_id)
    project=plan.parent/task['project'];schedule_path=workflow/schedule_id/'results.json'
    for group in (record['inputs'],record.get('runtime_inputs',{}),junction['inputs'],
                  {str(workflow/p):sha for p,sha in record['artifact_hashes'].items()}):
        for name,sha in group.items():
            if name in pins and pins[name]!=sha:raise ValueError('Source context changed between checks')
            pins[name]=sha
    result=calculate(json.loads(schedule_path.read_text(encoding='utf-8')),json.loads(project.read_text(encoding='utf-8')))
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in pins.items()):
        raise ValueError('Source,method or saved artifact changed during equation review')
    result.update(inputs=pins,native_schedule_lineage=junction['lineage'],original_requirements=record['requirements'])
    (out/'review.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (out/'index.html').write_text(render(result),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan');parser.add_argument('workflow');parser.add_argument('native_task');parser.add_argument('--out',required=True)
    args=parser.parse_args();result=run(args.plan,args.workflow,args.native_task,args.out)
    print(result['section_count'],'sections;',result['candidate_count'],'candidates;engineering acceptance pending')
    raise SystemExit(2)
