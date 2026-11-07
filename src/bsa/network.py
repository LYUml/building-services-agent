"""Steady prescribed-demand tree-network pressure budgets for circular ducts/pipes.

Not a looped hydraulic solver or a pressure-dependent demand/fan-curve solution.
"""
import argparse
import csv
import html
import json
import math
from pathlib import Path
from .cli import digest
from .engine import ProjectError

GRAVITY=9.80665


def validate(p):
    if not isinstance(p,dict) or p.get('model')!='steady incompressible circular tree':
        raise ProjectError('explicit steady incompressible circular tree model required')
    if not isinstance(p.get('name'),str) or not p['name'].strip():raise ProjectError('name required')
    sources=p.get('sources')
    if not isinstance(sources,dict) or not sources or any(not isinstance(v,str) or not v.strip() for v in sources.values()):
        raise ProjectError('source descriptions required')
    def source(row):
        if not isinstance(row,dict) or not isinstance(row.get('source'),str) or row['source'] not in sources:
            raise ProjectError('known source required for fluid, supply, nodes and segments')
    def number(row,key,minimum=None,positive=False):
        value=row.get(key)
        if type(value) not in (int,float) or not math.isfinite(value) or (minimum is not None and (value<minimum or (positive and value==minimum))):
            raise ProjectError(f'invalid finite input: {key}')
    fluid=p.get('fluid');source(fluid)
    for k in ('density_kg_m3','dynamic_viscosity_pa_s'):number(fluid,k,0,True)
    supply=p.get('supply');source(supply);number(supply,'total_pressure_pa',0)
    nodes=p.get('nodes');segments=p.get('segments')
    if not isinstance(nodes,list) or len(nodes)<2 or not isinstance(segments,list):raise ProjectError('nodes and segments required')
    def identities(rows):
        result={}
        for row in rows:
            source(row);id=row.get('id')
            if not isinstance(id,str) or not id.strip() or id in result:raise ProjectError('unique nonempty IDs required')
            result[id]=row
        return result
    nd=identities(nodes);sd=identities(segments)
    root=supply.get('node')
    if not isinstance(root,str) or root not in nd:raise ProjectError('supply node must exist')
    for n in nodes:
        number(n,'elevation_m');number(n,'demand_m3_s',0);number(n,'required_total_pressure_pa',0)
    if nd[root]['demand_m3_s']!=0:raise ProjectError('supply node must have zero withdrawal')
    incoming={};outgoing={id:[] for id in nd}
    for s in segments:
        a,b=s.get('from'),s.get('to')
        if not isinstance(a,str) or not isinstance(b,str) or a not in nd or b not in nd or a==b:
            raise ProjectError('segment requires distinct known endpoints')
        if b==root or b in incoming:raise ProjectError('tree nodes require exactly one parent; supply has none')
        incoming[b]=s;outgoing[a].append(s)
        for k in ('diameter_m','length_m','max_velocity_m_s'):number(s,k,0,True)
        for k in ('roughness_m','minor_k'):number(s,k,0)
        if s['roughness_m']/s['diameter_m']>=0.05:raise ProjectError('roughness ratio outside supported range (<0.05)')
        dz=nd[b]['elevation_m']-nd[a]['elevation_m']
        if s['length_m']+1e-9<abs(dz):raise ProjectError('route length shorter than elevation difference')
    if len(sd)!=len(nd)-1 or set(incoming)!=set(nd)-{root}:raise ProjectError('connected directed tree required')
    order=[];stack=[root];seen=set()
    while stack:
        node=stack.pop()
        if node in seen:raise ProjectError('cycle detected')
        seen.add(node);order.append(node)
        stack.extend(s['to'] for s in outgoing[node])
    if seen!=set(nd):raise ProjectError('disconnected tree or cycle')
    if sum(n['demand_m3_s'] for n in nodes)<=0:raise ProjectError('positive total withdrawal required')
    for id,n in nd.items():
        if not outgoing[id] and n['demand_m3_s']<=0:raise ProjectError('terminal nodes need positive specified demand')
    return p,nd,incoming,outgoing,order


def friction_factor(reynolds,relative_roughness):
    if reynolds==0:return 0.,'zero flow'
    if reynolds<2000:return 64/reynolds,'laminar 64/Re'
    if reynolds<4000:raise ProjectError('transitional Reynolds number 2000<=Re<4000; select a justified model outside this adapter')
    from fluids.friction import Colebrook
    return Colebrook(reynolds,relative_roughness),'turbulent Colebrook Darcy'


def calculate(p):
    p,nodes,incoming,outgoing,order=validate(p)
    rho=p['fluid']['density_kg_m3'];mu=p['fluid']['dynamic_viscosity_pa_s']
    flow={id:n['demand_m3_s'] for id,n in nodes.items()}
    for id in reversed(order[1:]):flow[incoming[id]['from']]+=flow[id]
    root=order[0];pressure={root:p['supply']['total_pressure_pa']};path={root:[]};cost={root:0.}
    results=[]
    for id in order[1:]:
        s=incoming[id];parent=s['from'];q=flow[id]
        area=math.pi*s['diameter_m']**2/4;velocity=q/area
        re=rho*velocity*s['diameter_m']/mu
        if not all(math.isfinite(v) for v in (q,area,velocity,re)):raise ProjectError('derived flow inputs overflowed')
        factor,regime=friction_factor(re,s['roughness_m']/s['diameter_m'])
        dynamic=rho*velocity**2/2
        major=factor*s['length_m']/s['diameter_m']*dynamic
        minor=s['minor_k']*dynamic
        elevation=rho*GRAVITY*(nodes[id]['elevation_m']-nodes[parent]['elevation_m'])
        loss=major+minor
        if not all(math.isfinite(v) for v in (factor,major,minor,elevation,loss)):raise ProjectError('derived pressure inputs overflowed')
        cost[id]=cost[parent]+loss+elevation
        pressure[id]=p['supply']['total_pressure_pa']-cost[id]
        path[id]=path[parent]+[s['id']]
        results.append(dict(id=s['id'],from_node=parent,to_node=id,flow_m3_s=q,area_m2=area,
            velocity_m_s=velocity,reynolds=re,darcy_friction_factor=factor,regime=regime,
            friction_pa=major,minor_pa=minor,dissipative_loss_pa=loss,elevation_pressure_pa=elevation,
            downstream_total_pressure_pa=pressure[id],velocity_pass=velocity<=s['max_velocity_m_s'],source=s['source']))
    node_results=[dict(id=id,demand_m3_s=nodes[id]['demand_m3_s'],total_pressure_pa=pressure[id],
        required_total_pressure_pa=nodes[id]['required_total_pressure_pa'],
        pressure_margin_pa=pressure[id]-nodes[id]['required_total_pressure_pa'],
        pressure_pass=pressure[id]>=nodes[id]['required_total_pressure_pa'],path=path[id],source=nodes[id]['source']) for id in order]
    critical=max(order,key=lambda id:cost[id]+nodes[id]['required_total_pressure_pa'])
    required=max(0.,cost[critical]+nodes[critical]['required_total_pressure_pa'])
    checks=dict(velocity=all(s['velocity_pass'] for s in results),pressure=all(n['pressure_pass'] for n in node_results),
        flow_continuity=math.isclose(flow[root],sum(n['demand_m3_s'] for n in nodes.values()),rel_tol=1e-10,abs_tol=1e-12))
    return dict(name=p['name'],supply_flow_m3_s=flow[root],segments=results,nodes=node_results,
        critical_node=critical,critical_path=path[critical],required_source_total_pressure_pa=required,
        calculated_checks=checks,calculated_checks_pass=all(checks.values()),design_accepted=False,
        pressure_basis='Total pressure (static + velocity), with elevation potential handled separately; common reference. Not an ambient-referenced vertical air pressure model.',
        scope='Prescribed withdrawals in a constant-density, fully filled circular tree; no loops or pressure-dependent flow solution',
        pending=['source demand and route evidence','component K/reference velocity validation','fan/pump curve and operating-point selection','noise, cavitation, compressibility and domain/code checks','physical routing and clash review'])


def run(project,out):
    import importlib.metadata
    project,out=project.resolve(),out.resolve()
    if out==project or out in project.parents:raise ProjectError('output must not contain source')
    before=digest(project);p=json.loads(project.read_text(encoding='utf-8-sig'))
    result=calculate(p)
    result.update(input_sha256=before,fluids_version=importlib.metadata.version('fluids'),sources=p['sources'],
        methods=['Darcy-Weisbach: f_D L/D rho v^2/2','Fittings: K rho v^2/2 using local segment velocity',
                 'Elevation: rho g dz, g=9.80665 m/s2','https://fluids.readthedocs.io/fluids.friction.html'])
    out.mkdir(parents=True,exist_ok=False)
    (out/'network.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (out/'segments.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(result['segments'][0]));writer.writeheader();writer.writerows(result['segments'])
    rows=''.join('<tr><td>'+html.escape(n['id'])+'</td><td>'+f"{n['total_pressure_pa']:.2f}"+'</td><td>'+f"{n['pressure_margin_pa']:.2f}"+'</td><td>'+str(n['pressure_pass'])+'</td></tr>' for n in result['nodes'])
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Network pressure budget</title><h1>'+html.escape(p['name'])+'</h1><p>'+html.escape(result['scope'])+'</p><p>'+html.escape(result['pressure_basis'])+'</p><p>Design acceptance pending. Required source budget: '+f"{result['required_source_total_pressure_pa']:.2f}"+' Pa</p><table border="1"><tr><th>Node</th><th>Total pressure Pa</th><th>Margin Pa</th><th>Check</th></tr>'+rows+'</table><h2>Unresolved</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in result['pending'])+'</ul>',encoding='utf-8')
    if digest(project)!=before:raise ProjectError('source changed during calculation')
    manifest=dict(input_sha256=before,input_unchanged=True,artifacts={f.name:digest(f) for f in out.iterdir() if f.is_file()})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.out)
    print(json.dumps(dict(calculated_checks_pass=r['calculated_checks_pass'],required_source_total_pressure_pa=r['required_source_total_pressure_pa'],design_accepted=False)))
    return 0 if r['calculated_checks_pass'] else 2

if __name__=='__main__':raise SystemExit(main())
