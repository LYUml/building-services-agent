"""Source-bound diagnostic for one equal-bore 90-degree diverging tee."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import ifcopenshell
import ifcopenshell.util.system as system
import fluids.fittings as fittings
from bsa.cli import digest
from .tee_assembly import verify


def run(model,tee_spec,assembly_spec,basis,out):
    paths=[Path(p).resolve() for p in (model,tee_spec,assembly_spec,basis)]
    model,tee_spec,assembly_spec,basis=paths;out=Path(out).resolve()
    before={str(p):digest(p) for p in paths}
    spec,assembly,data=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths[1:]]
    keys={'source','correlation_assumption','inlet_port','run_flow_m3_s','branch_flow_m3_s','density_kg_m3'}
    if set(data)!=keys or any(not isinstance(data[k],str) or not data[k].strip() for k in ('source','correlation_assumption')):
        raise ValueError('exact sourced diagnostic basis required')
    if data['inlet_port'] not in ('main-a','main-b'):raise ValueError('main-leg diverging inlet required')
    qrun,qbranch,rho=[data[k] for k in ('run_flow_m3_s','branch_flow_m3_s','density_kg_m3')]
    if any(type(x) not in (float,int) or not math.isfinite(x) or x<=0 for x in (qrun,qbranch,rho)):
        raise ValueError('positive finite outlet flows and density required')
    if importlib.metadata.version('fluids')!='1.3.1':raise ValueError('fluids 1.3.1 required')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out==p or out in p.parents for p in paths):
        raise ValueError('new repository output required')
    f=ifcopenshell.open(str(model))
    if len(f.by_type('IfcPipeFitting'))!=1 or len(f.by_type('IfcElement'))!=4 or len(f.by_type('IfcDistributionPort'))!=9:
        raise ValueError('exact single tee assembly required')
    geometry=verify(model,spec,assembly['pipe_lengths_m'])
    if not geometry['assembly_checks_pass']:raise ValueError('saved assembly geometry/identity failed')
    f=ifcopenshell.open(str(model));tee=f.by_type('IfcPipeFitting')[0]
    ports={p.Name:p.GlobalId for p in system.get_ports(tee)}
    # Saved profile and supplied source dimensions have already been reconciled by verify.
    d=2*spec['inner_radius_m'];q=qrun+qbranch;velocity=q/(math.pi*d*d/4)
    reference=rho*velocity*velocity/2
    kbranch=fittings.K_branch_diverging_Crane(d,d,qrun,qbranch,angle=90)
    krun=fittings.K_run_diverging_Crane(d,d,qrun,qbranch,angle=90)
    run_port='main-b' if data['inlet_port']=='main-a' else 'main-a'
    result=dict(inputs=before,basis=data,fluids_version='1.3.1',fittings_module_sha256=digest(Path(fittings.__file__)),
        tee_guid=tee.GlobalId,inlet_guid=ports[data['inlet_port']],combined_flow_m3_s=q,
        combined_velocity_m_s=velocity,reference_dynamic_pressure_pa=reference,
        coefficient_reference='combined inlet velocity; signed values retained',
        paths={name:dict(outlet_guid=ports[port],flow_m3_s=flow,k_combined_velocity=k,signed_k_times_dynamic_pressure_pa=k*reference)
            for name,port,flow,k in [('run',run_port,qrun,krun),('branch','branch',qbranch,kbranch)]},
        geometry_checks=geometry['checks'],diagnostic_executed=True,design_accepted=False,
        pending=['physical correlation applicability','finite fitting distributed friction/reference stations','passive flow split and network pressure solution','product and regulatory acceptance'])
    if any(digest(p)!=before[str(p)] for p in paths):raise ValueError('input changed during diagnostic')
    out.mkdir(parents=True);(out/'tee-loss.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','tee-spec','assembly-spec','basis','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();print(json.dumps(run(a.model,a.tee_spec,a.assembly_spec,a.basis,a.out),indent=2))
