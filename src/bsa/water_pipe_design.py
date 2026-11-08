"""Finite water-pipe selection requiring hydraulic and scoped regulatory passes."""
import argparse
import copy
import itertools
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network_design import validate_catalogue,derive
from .regulations import source_paths
from .water_pipe_regulations import run as check


def run(project,catalogue,basis,classifications,pack,sources,out):
    paths=[Path(p).resolve() for p in (project,catalogue,basis,classifications,pack)];out=Path(out).resolve()
    before={str(p):digest(p) for p in paths}
    original,cat,bases,classes,rules=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
    options,ids,count=validate_catalogue(original,cat)
    if set(classes)!=set(options) or set(bases)!=set(ids):raise ProjectError('exact option classification and segment basis coverage required')
    for value in classes.values():
        if not isinstance(value,dict) or type(value.get('value')) not in (int,float) or not math.isfinite(value['value']) or value['value']<=0 or value.get('unit')!='mm' or not isinstance(value.get('source'),str) or not value['source'].strip():
            raise ProjectError('each option requires explicit sourced positive code diameter in mm')
    official=source_paths(rules,sources)
    if any(out==p or out in p.parents for p in set(paths)|official):raise ProjectError('output must not contain inputs')
    cached={str(p):digest(p) if p.is_file() else None for p in official}
    out.mkdir(parents=True,exist_ok=False)
    rows=[];best=None;best_rank=None
    lengths={s['id']:s['length_m'] for s in original['segments']}
    for i,values in enumerate(itertools.product(*(sorted(cat['allowed_options'][id]) for id in ids)),1):
        choices=dict(zip(ids,values));candidate=derive(original,cat,options,choices)
        score=math.fsum(lengths[id]*options[choices[id]]['material_score_per_m'] for id in ids)
        if not math.isfinite(score):raise ProjectError('candidate score overflow')
        b=copy.deepcopy(bases)
        for id in ids:b[id].setdefault('water_pipe',{})['code_diameter']=copy.deepcopy(classes[choices[id]])
        folder=out/('candidate-'+str(i));folder.mkdir()
        np=folder/'network.json';bp=folder/'bases.json'
        np.write_text(json.dumps(candidate,indent=2));bp.write_text(json.dumps(b,indent=2))
        result=check(np,bp,paths[4],sources,folder/'checks')
        row=dict(id=folder.name,choices=choices,material_score=score,status=result['status'],hydraulic_checks_pass=result['hydraulic_checks_pass'],supported_checks_pass=result['supported_checks_pass'],checks_sha256=digest(folder/'checks/water-pipe-checks.json'))
        rows.append(row);rank=(score,tuple(values))
        if row['status']=='pass' and (best_rank is None or rank<best_rank):best=row;best_rank=rank
    rerun=False
    if best:
        folder=out/best['id']
        result=check(folder/'network.json',folder/'bases.json',paths[4],sources,out/'selected-rerun')
        if result['status']!='pass':raise ProjectError('selected candidate rerun did not pass')
        rerun=True
    if any(digest(Path(p))!=h for p,h in before.items()) or any((digest(Path(p)) if Path(p).is_file() else None)!=h for p,h in cached.items()):raise ProjectError('design search inputs changed')
    result=dict(inputs=before,official_sources=cached,inputs_unchanged=True,candidate_count=count,candidates=rows,selected=best,selected_rerun_pass=rerun,
                feasible_design_found=best is not None,design_accepted=False,regulatory_compliance='not_established',
                scope='Exhaustive supplied finite catalogue, prescribed demands and fixed route/K; minimum supplied material score among hydraulic and scoped-rule passing candidates; no product or whole-project acceptance')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'design-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    for k in ('catalogue','basis','classifications','pack','sources','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.catalogue,a.basis,a.classifications,a.pack,a.sources,a.out)
    print(json.dumps({'selected':r['selected'],'design_accepted':False}))
    return 0 if r['feasible_design_found'] else 2


if __name__=='__main__':raise SystemExit(main())
