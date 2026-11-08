"""Pressure-based route choice for a fixed-bore, prescribed-flow planar pipe."""
import argparse
import copy
import json
import math
from pathlib import Path

from .cli import digest
from .engine import ProjectError
from .network import calculate
from .network_binding import prepare
from .route_model import compile_route, run as model_run


def select(routing,settings,network):
    if 'bend_penalty_m' in routing or 'objective_source' in routing:
        raise ProjectError('pressure objective derives its own penalty; do not supply a second objective')
    baseline=compile_route(routing,settings,network)
    def evaluate(compiled):
        route,model,binding,skeleton=compiled
        derived,_=prepare(skeleton,model,binding)
        result=calculate(derived)
        return result,result['segments'][0]
    baseline_result,base_segment=evaluate(baseline)
    # Fixed bore, prescribed flow and constant properties make friction per
    # metre constant. Each added bend adds one straight piece as well.
    gradient=base_segment['friction_pa']/baseline[0]['length_m']
    dynamic=network['fluid']['density_kg_m3']*base_segment['velocity_m_s']**2/2
    if not math.isfinite(gradient) or gradient<=0:raise ProjectError('positive finite friction gradient required')
    penalty=(settings['elbow_excess_k']+settings['straight_excess_k'])*dynamic/gradient
    candidate=copy.deepcopy(routing)
    candidate.update(bend_penalty_m=penalty,objective_source='Derived from supplied fixed-bore prescribed-flow pressure inputs: (elbow excess K + additional straight excess K) times dynamic pressure / friction Pa per metre; '+settings['source'])
    chosen=compile_route(candidate,settings,network)
    chosen_result,segment=evaluate(chosen)
    predicted=gradient*chosen[0]['objective_cost_m']+settings['straight_excess_k']*dynamic
    if not math.isclose(predicted,segment['dissipative_loss_pa'],rel_tol=1e-10,abs_tol=1e-10):raise ProjectError('selected pressure differs from search objective')
    if segment['dissipative_loss_pa']>base_segment['dissipative_loss_pa']+1e-10:raise ProjectError('pressure search worsened its baseline')
    return candidate,dict(baseline_route=baseline[0],baseline_pressure=baseline_result,selected_route=chosen[0],selected_pressure=chosen_result,
                          friction_gradient_pa_m=gradient,derived_bend_penalty_m=penalty,predicted_selected_loss_pa=predicted,
                          pressure_reduction_pa=base_segment['dissipative_loss_pa']-segment['dissipative_loss_pa'],
                          calculated_checks_pass=chosen_result['calculated_checks_pass'],design_accepted=False,
                          scope='minimum dissipative pressure on the declared conservative planar grid at fixed bore, prescribed flow and constant fluid properties; no pump operating point or installation optimum')


def run(routing,settings,network,out):
    paths=[Path(p).resolve() for p in (routing,settings,network)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain sources')
    hashes={str(p):digest(p) for p in paths}
    data=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
    selected,result=select(*data)
    out.mkdir(parents=True,exist_ok=False)
    selected_path=out/'selected-routing.json';selected_path.write_text(json.dumps(selected,indent=2),encoding='utf-8')
    # Retain comparison even if downstream native authoring fails.
    (out/'selection.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    native=model_run(selected_path,paths[1],paths[2],out/'selected')
    if any(digest(Path(p))!=h for p,h in hashes.items()):raise ProjectError('optimisation sources changed')
    result.update(inputs=hashes,inputs_unchanged=True,selected_model=native,
                  calculated_checks_pass=result['calculated_checks_pass'] and native['calculated_checks_pass'])
    (out/'route-optimisation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('routing',type=Path)
    for name in ('settings','network','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=run(args.routing,args.settings,args.network,args.out)
    print(json.dumps({'pressure_reduction_pa':result['pressure_reduction_pa'],'calculated_checks_pass':result['calculated_checks_pass'],'design_accepted':False}))
    return 0 if result['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
