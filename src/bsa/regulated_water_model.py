"""Finite regulatory sizing followed by saved-IFC revision and rule recheck."""
import argparse
import copy
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from .network_model_design import prepare,filter_geometry,resize,verify_saved,verify_identities
from .network_binding import run as coordinate
from .bim import run as author
from .water_pipe_design import run as search
from .ifc_water_rules import run as recheck
from .regulations import source_paths


def run(network,model,binding,catalogue,geometry,basis,classifications,pack,sources,out):
    paths=[Path(p).resolve() for p in (network,model,binding,catalogue,geometry,basis,classifications,pack)]
    out=Path(out).resolve();before={str(p):digest(p) for p in paths}
    n,m,b,c,g,_,_,rules=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
    official=source_paths(rules,sources);cached={str(p):digest(p) if p.is_file() else None for p in official}
    if any(out==p or out in p.parents for p in set(paths)|official):raise ProjectError('output must not contain sources')
    baseline,_,_,count=prepare(n,m,b,c,g)
    filtered,rejected=filter_geometry(n,m,b,c,g)
    out.mkdir(parents=True,exist_ok=False)
    def save(name,data):
        p=out/name;p.write_text(json.dumps(data,indent=2),encoding='utf-8');return p
    baseline_path=save('baseline-network.json',baseline);filtered_path=save('filtered-catalogue.json',filtered)
    author(paths[1],out/'baseline-bim')
    result=dict(original_candidate_count=count,rejected_geometry_options=rejected,selected=None,
                calculated_checks_pass=False,saved_ifc_checks_pass=False,design_accepted=False,regulatory_compliance='not_established')
    if all(filtered['allowed_options'].values()):
        sizing=search(baseline_path,filtered_path,paths[5],paths[6],paths[7],sources,out/'sizing')
        if sizing['selected']:
            chosen=sizing['selected'];candidate=out/'sizing'/chosen['id']
            revised=resize(m,b,chosen['choices'],c,g);mp=save('selected-model.json',revised)
            skeleton=json.loads((candidate/'network.json').read_text())
            for node in skeleton['nodes']:node.pop('elevation_m')
            for segment in skeleton['segments']:segment.pop('length_m');segment.pop('diameter_m')
            np=save('selected-skeleton.json',skeleton)
            coordinated=coordinate(np,mp,paths[2],out/'selected-coordination')
            verify_saved(m,out/'selected-coordination/bim/model.ifc',b,chosen['choices'],c,g)
            verify_identities(out/'baseline-bim/model.ifc',out/'selected-coordination/bim/model.ifc')
            checked=recheck(out/'selected-coordination',mp,paths[2],candidate/'bases.json',paths[7],sources,out/'selected-rules')
            ranked=json.loads((candidate/'checks/network/network.json').read_text())
            actual=json.loads((out/'selected-rules/network/network.json').read_text())
            if not math.isclose(ranked['required_source_total_pressure_pa'],actual['required_source_total_pressure_pa'],rel_tol=1e-9,abs_tol=1e-8):raise ProjectError('selected IFC hydraulic rerun differs from ranked candidate')
            result.update(selected=chosen,saved_ifc_checks_pass=True,stable_object_port_ids_match=True,
                          calculated_checks_pass=coordinated['calculated_checks_pass'] and checked['status']=='pass')
    if any(digest(Path(p))!=h for p,h in before.items()) or any((digest(Path(p)) if Path(p).is_file() else None)!=h for p,h in cached.items()):raise ProjectError('model design sources changed')
    result.update(inputs=before,official_sources=cached,inputs_unchanged=True,
                  scope='Finite sourced catalogue and fixed straight-route resizing; saved IFC identity/geometry, hydraulic and scoped regulatory recheck; clash, product and full acceptance pending')
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    save('regulated-model.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('network','model','binding','catalogue','geometry','basis','classifications','pack','sources','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();r=run(**vars(a));print(json.dumps({'selected':r['selected'],'calculated_checks_pass':r['calculated_checks_pass'],'design_accepted':False}))
    return 0 if r['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
