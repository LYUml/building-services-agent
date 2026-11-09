"""Prescribed-flow pressure budget for a saved tee assembly and sourced face coefficients."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import ifcopenshell
import ifcopenshell.util.system as system
import ifcopenshell.util.placement as placement
from .cli import digest
from .network import friction_factor,GRAVITY
from .tee_assembly import verify

CONTRACT='tee face-to-face total-head difference; includes all fitting wall friction; combined inlet velocity'


def run(model,tee_spec,assembly_spec,basis,out):
    paths=[Path(p).resolve() for p in (model,tee_spec,assembly_spec,basis)]
    model,tee_spec,assembly_spec,basis=paths;out=Path(out).resolve()
    before={str(p):digest(p) for p in paths}
    spec,assembly,data=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths[1:]]
    required={'source','fluid_source','coefficient_source','coefficient_contract','inlet_port','run_flow_m3_s','branch_flow_m3_s','density_kg_m3','dynamic_viscosity_pa_s','roughness_m','inlet_total_pressure_pa','required_outlet_total_pressure_pa','max_velocity_m_s','k_run','k_branch'}
    if set(data)!=required:raise ValueError('exact pressure budget basis required')
    if any(not isinstance(data[k],str) or not data[k].strip() for k in ('source','fluid_source','coefficient_source')):raise ValueError('explicit sources required')
    if data['coefficient_contract']!=CONTRACT:raise ValueError('explicit face-to-face coefficient contract required')
    if data['inlet_port'] not in ('main-a','main-b'):raise ValueError('main-leg diverging inlet required')
    numeric=required-{'source','fluid_source','coefficient_source','coefficient_contract','inlet_port','required_outlet_total_pressure_pa'}
    for k in numeric:
        if type(data[k]) not in (int,float) or not math.isfinite(data[k]):raise ValueError('finite numeric basis required')
    for k in ('run_flow_m3_s','branch_flow_m3_s','density_kg_m3','dynamic_viscosity_pa_s','max_velocity_m_s'):
        if data[k]<=0:raise ValueError('positive flow, fluid and velocity inputs required')
    if data['roughness_m']<0:raise ValueError('nonnegative roughness required')
    targets=data['required_outlet_total_pressure_pa']
    if not isinstance(targets,dict) or set(targets)!={'run','branch'} or any(type(x) not in (int,float) or not math.isfinite(x) for x in targets.values()):raise ValueError('two finite total-pressure targets required')
    if importlib.metadata.version('fluids')!='1.3.1':raise ValueError('fluids 1.3.1 required')
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[2]) or any(out==p or out in p.parents for p in paths):raise ValueError('new repository output required')
    f=ifcopenshell.open(str(model))
    if len(f.by_type('IfcPipeFitting'))!=1 or len(f.by_type('IfcElement'))!=4 or len(f.by_type('IfcDistributionPort'))!=9:raise ValueError('exact single tee assembly required')
    check=verify(model,spec,assembly['pipe_lengths_m'])
    if not check['assembly_checks_pass']:raise ValueError('saved assembly verification failed')
    inlet=data['inlet_port'];run_port='main-b' if inlet=='main-a' else 'main-a'
    qr,qb=data['run_flow_m3_s'],data['branch_flow_m3_s'];q=qr+qb
    rho,mu=data['density_kg_m3'],data['dynamic_viscosity_pa_s']
    pipes={p.Name:p for p in f.by_type('IfcPipeSegment')};rows={}
    for name,flow in ((inlet,q),(run_port,qr),('branch',qb)):
        pipe=pipes[name];solid=pipe.Representation.Representations[0].Items[0];d=2*solid.SweptArea.Radius-2*solid.SweptArea.WallThickness
        if data['roughness_m']/d>=.05:raise ValueError('roughness outside supported range')
        velocity=flow/(math.pi*d*d/4);re=rho*velocity*d/mu;factor,regime=friction_factor(re,data['roughness_m']/d)
        ports={p.Name:p for p in system.get_ports(pipe)}
        outer=ports['out'];point=placement.get_local_placement(outer.ObjectPlacement)[:3,3]
        rows[name]=dict(guid=pipe.GlobalId,outer_port_guid=outer.GlobalId,outer_elevation_m=float(point[2]),length_m=solid.Depth,diameter_m=d,flow_m3_s=flow,velocity_m_s=velocity,reynolds=re,darcy_factor=factor,regime=regime,friction_pa=factor*solid.Depth/d*rho*velocity**2/2)
    common=rows[inlet];dynamic=rho*common['velocity_m_s']**2/2
    results={}
    for label,name,k in (('run',run_port,data['k_run']),('branch','branch',data['k_branch'])):
        row=rows[name];dz=row['outer_elevation_m']-common['outer_elevation_m']
        friction=common['friction_pa']+row['friction_pa'];fitting=k*dynamic;gravity=rho*GRAVITY*dz
        available=data['inlet_total_pressure_pa']-friction-fitting-gravity
        results[label]=dict(outlet_port_guid=row['outer_port_guid'],pipe_friction_pa=friction,fitting_signed_pa=fitting,elevation_pa=gravity,outlet_total_pressure_pa=available,required_total_pressure_pa=targets[label],margin_pa=available-targets[label])
    power=dynamic*(qr*data['k_run']+qb*data['k_branch'])
    checks=dict(pressure_targets=all(v['margin_pa']>=0 for v in results.values()),velocity_targets=all(v['velocity_m_s']<=data['max_velocity_m_s'] for v in rows.values()),nonnegative_net_fitting_dissipation=power>=0)
    if not all(math.isfinite(x) for row in results.values() for x in row.values() if isinstance(x,(int,float))) or not math.isfinite(power):raise ValueError('nonfinite derived budget')
    if any(digest(p)!=before[str(p)] for p in paths):raise ValueError('source changed during budget')
    result=dict(inputs=before,basis=data,geometry_checks=check['checks'],pipes=rows,paths=results,net_fitting_dissipation_w=power,checks=checks,calculated_checks_pass=all(checks.values()),design_accepted=False,scope='Prescribed positive split and supplied tee-face coefficients; no passive split, pump solution, product or regulatory acceptance')
    out.mkdir(parents=True);(out/'tee-pressure.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','tee-spec','assembly-spec','basis','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=run(a.model,a.tee_spec,a.assembly_spec,a.basis,a.out);print(json.dumps(r,indent=2));raise SystemExit(0 if r['calculated_checks_pass'] else 2)
