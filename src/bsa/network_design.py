"""Exhaustive, source-bounded discrete sizing for the prescribed-demand tree model."""
import argparse
import copy
import csv
import html
import itertools
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network import validate,calculate,run as analyse

BASIS='prescribed demands; route and local K unchanged across sizes'


def validate_catalogue(project,catalogue):
    validate(project)
    if not isinstance(catalogue,dict) or set(catalogue)!={'sources','options','allowed_options','objective','max_evaluations','hydraulic_basis'}:
        raise ProjectError('explicit sizing catalogue, search bound, objective and hydraulic basis required')
    sources=catalogue['sources']
    if not isinstance(sources,dict) or not sources or any(not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip() for k,v in sources.items()):
        raise ProjectError('catalogue source descriptions required')
    if catalogue['objective']!='minimise sum(length_m * material_score_per_m)':raise ProjectError('unsupported sizing objective')
    basis=catalogue['hydraulic_basis']
    if not isinstance(basis,dict) or set(basis)!={'assumption','source'} or basis['assumption']!=BASIS or not isinstance(basis['source'],str) or basis['source'] not in sources:
        raise ProjectError('explicit source-backed constant-route/local-K sizing assumption required')
    bound=catalogue['max_evaluations']
    if type(bound) is not int or not 1<=bound<=10000:raise ProjectError('search bound must be an integer from 1 to 10000')
    options={}
    if not isinstance(catalogue['options'],list) or not catalogue['options']:raise ProjectError('nonempty sourced options required')
    for row in catalogue['options']:
        if not isinstance(row,dict) or set(row)!={'id','diameter_m','roughness_m','material_score_per_m','source'}:
            raise ProjectError('catalogue options require explicit internal diameter, roughness and material score')
        id=row['id']
        if not isinstance(id,str) or not id.strip() or id in options or not isinstance(row['source'],str) or row['source'] not in sources:raise ProjectError('unique sourced option IDs required')
        for key in ('diameter_m','roughness_m','material_score_per_m'):
            value=row[key]
            if type(value) not in (int,float) or not math.isfinite(value) or value<0 or (key=='diameter_m' and value==0):
                raise ProjectError('finite nonnegative score/roughness and positive internal diameter required')
        if row['roughness_m']/row['diameter_m']>=.05:raise ProjectError('catalogue roughness outside supported range')
        options[id]=row
    allowed=catalogue['allowed_options'];ids=sorted(s['id'] for s in project['segments'])
    if not isinstance(allowed,dict) or set(allowed)!=set(ids):raise ProjectError('exact segment choice coverage required')
    count=1
    for id in ids:
        values=allowed[id]
        if not isinstance(values,list) or not values or any(not isinstance(v,str) or v not in options for v in values) or len(set(values))!=len(values):
            raise ProjectError('unique known allowed option IDs required per segment')
        count*=len(values)
    if count>bound:raise ProjectError(f'{count} combinations exceed search bound {bound}; revise explicit design space, not a hidden truncation')
    for key in sources:
        if 'sizing/'+key in project['sources']:raise ProjectError('reserved sizing source namespace already present')
    return options,ids,count


def derive(project,catalogue,options,choices):
    result=copy.deepcopy(project)
    result['sources'].update({'sizing/'+k:v for k,v in catalogue['sources'].items()})
    for segment in result['segments']:
        option=options[choices[segment['id']]];old_source=segment['source']
        key='sizing/segment/'+segment['id']
        if key in result['sources']:raise ProjectError('sizing provenance namespace collision')
        result['sources'][key]=(project['sources'][old_source]+'; size/roughness: '+catalogue['sources'][option['source']]
                                +'; sizing assumption: '+catalogue['sources'][catalogue['hydraulic_basis']['source']])
        segment.update(diameter_m=option['diameter_m'],roughness_m=option['roughness_m'],source=key)
    return result


def search(project,catalogue):
    options,ids,count=validate_catalogue(project,catalogue)
    lengths={s['id']:s['length_m'] for s in project['segments']}
    candidates=[];best=None;best_project=None;best_rank=None
    for index,values in enumerate(itertools.product(*(sorted(catalogue['allowed_options'][id]) for id in ids)),1):
        choices=dict(zip(ids,values));candidate=derive(project,catalogue,options,choices)
        score=math.fsum(lengths[id]*options[choices[id]]['material_score_per_m'] for id in ids)
        if not math.isfinite(score):raise ProjectError('derived material score overflow')
        row=dict(id=f'C{index:06}',choices=choices,material_score=score,feasible=False)
        try:
            result=calculate(candidate)
            row.update(calculated_checks=result['calculated_checks'],feasible=result['calculated_checks_pass'],
                       required_source_total_pressure_pa=result['required_source_total_pressure_pa'],
                       failed_velocity_segments=[s['id'] for s in result['segments'] if not s['velocity_pass']],
                       failed_pressure_nodes=[n['id'] for n in result['nodes'] if not n['pressure_pass']])
            rank=(score,result['required_source_total_pressure_pa'],values)
            if row['feasible'] and (best_rank is None or rank<best_rank):best=row;best_project=candidate;best_rank=rank
        except ProjectError as exc:row['analysis_error']=str(exc)
        candidates.append(row)
    return dict(candidate_count=count,evaluated_count=len(candidates),feasible_count=sum(r['feasible'] for r in candidates),
                search_complete=len(candidates)==count,candidates=candidates,selected=best,feasible_design_found=best is not None,
                objective=catalogue['objective'],tie_break='lowest required source total pressure, then lexical option IDs by sorted segment ID',
                design_accepted=False,scope='Global optimum only in the supplied finite catalogue under the existing prescribed-flow tree method',
                pending=['catalogue and invariant K/route applicability','update/reconcile authored BIM after sizing','fan/pump curve, balancing and all domain/code acceptance']),best_project


def run(project,catalogue,out):
    project,catalogue,out=[Path(p).resolve() for p in (project,catalogue,out)]
    if any(out==p or out in p.parents for p in (project,catalogue)):raise ProjectError('output must not contain sources')
    before={str(p):digest(p) for p in (project,catalogue)}
    original=json.loads(project.read_text(encoding='utf-8-sig'));catalog=json.loads(catalogue.read_text(encoding='utf-8-sig'))
    result,selected=search(original,catalog)
    out.mkdir(parents=True,exist_ok=False)
    try:
        baseline=analyse(project,out/'baseline')
        result['baseline']=dict(calculated_checks=baseline['calculated_checks'],calculated_checks_pass=baseline['calculated_checks_pass'],
                                required_source_total_pressure_pa=baseline['required_source_total_pressure_pa'])
    except ProjectError as exc:result['baseline']=dict(analysis_error=str(exc),calculated_checks_pass=False)
    if selected:
        selected_path=out/'selected-network.json';selected_path.write_text(json.dumps(selected,indent=2),encoding='utf-8')
        saved=analyse(selected_path,out/'selected')
        if not saved['calculated_checks_pass'] or not math.isclose(saved['required_source_total_pressure_pa'],result['selected']['required_source_total_pressure_pa'],rel_tol=1e-12):
            raise ProjectError('selected network rerun differs from ranked evidence')
        result['selected_rerun_pass']=True
    else:result['selected_rerun_pass']=False
    def escaped(value):return html.escape(str(value))
    rows=[]
    for row in result['candidates']:
        reason=row.get('analysis_error') or ('velocity: '+','.join(row['failed_velocity_segments'])+'; pressure: '+','.join(row['failed_pressure_nodes']))
        rows.append('<tr>'+''.join('<td>'+escaped(v)+'</td>' for v in (row['id'],json.dumps(row['choices'],sort_keys=True),
            row['material_score'],row['feasible'],row.get('required_source_total_pressure_pa','not calculated'),reason))+'</tr>')
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Conditional network sizing</title>'
        '<h1>Conditional network sizing</h1><p>'+escaped(result['scope'])+'</p><p>Design acceptance: pending. '
        'Material score is a supplied metric; no monetary or environmental estimate is inferred.</p><p>Objective: '+escaped(result['objective'])+
        '</p><p>Baseline: '+escaped(json.dumps(result['baseline']))+'</p><p>Selected: '+escaped(json.dumps(result['selected']))+
        '</p><table border="1"><tr><th>Candidate</th><th>Options by segment</th><th>Material score</th><th>Feasible</th>'
        '<th>Required source total pressure Pa</th><th>Failures / analysis error</th></tr>'+''.join(rows)+
        '</table><h2>Pending</h2><ul>'+''.join('<li>'+escaped(v)+'</li>' for v in result['pending'])+'</ul>',encoding='utf-8')
    with (out/'candidates.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['id','material_score','feasible','required_source_total_pressure_pa','choices','analysis_error'])
        writer.writeheader()
        for row in result['candidates']:
            writer.writerow({key:json.dumps(row[key],sort_keys=True) if key=='choices' else row.get(key,'') for key in writer.fieldnames})
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('source changed during design search')
    result.update(inputs=before,inputs_unchanged=True,catalogue_sources=catalog['sources'])
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'design-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    p.add_argument('--catalogue',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.catalogue,a.out)
    print(json.dumps({k:r[k] for k in ('candidate_count','feasible_count','feasible_design_found','selected','design_accepted')}))
    return 0 if r['feasible_design_found'] else 2

if __name__=='__main__':raise SystemExit(main())
