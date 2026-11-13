"""Bind the complete represented source network to design flows and native path budgets."""
import argparse
import importlib.metadata
import html
import json
import math
from pathlib import Path
import tempfile
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.system as system
import ifcopenshell.util.placement as placement
import numpy as np
from . import source_compound_network as producer,duct_chain_analysis as local
from . import duct_equivalent,interface_contacts,rectangular_transition as transition
from . import rectangular_cross as cross,rectangular_cross_transitions as cross_composition
from . import compound_junction
from .tee_geometry import stable_guid
from .cli import digest
from .workspace import allowed


def prescribed_flows(owned,directions,links,expected):
    """Derive from source outlet demands and actual graph, then reconcile every source port."""
    ports={g for row in owned.values() for g in row}
    if set(expected)!=ports or set(directions)!=ports or len(ports)!=sum(map(len,owned.values())):raise ValueError('Exact unique owned flow-port coverage required')
    owners={g:o for o,row in owned.items() for g in row};peer={};occupied=set()
    for a,b in links:
        if a not in ports or b not in ports or directions[a]!='SOURCE' or directions[b]!='SINK' or a in occupied or b in occupied:raise ValueError('One directed peer per saved flow interface required')
        peer[a]=b;occupied.update((a,b))
    for row in owned.values():
        if sum(directions[g]=='SINK' for g in row)!=1 or not any(directions[g]=='SOURCE' for g in row) or any(directions[g] not in ('SOURCE','SINK') for g in row):raise ValueError('One-inlet source split/through product required')
    values={};active=set()
    def demand(g):
        if g in active:raise ValueError('Cycle in saved prescribed-flow graph')
        if g in values:return values[g]
        active.add(g)
        if directions[g]=='SINK':q=math.fsum(demand(p) for p in owned[owners[g]] if directions[p]=='SOURCE')
        elif g in peer:q=demand(peer[g])
        else:q=expected[g]['flow_m3_s']
        if type(q) not in (int,float) or not math.isfinite(q) or q<=0:raise ValueError('Positive finite source-prescribed flow required')
        active.remove(g);values[g]=q;return q
    for g in sorted(ports):demand(g)
    for g,q in values.items():
        wanted=expected[g]['flow_m3_s']
        if type(wanted) not in (int,float) or not math.isfinite(wanted) or wanted<=0 or not math.isclose(q,wanted,rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Saved graph flow differs from inherited source section at '+g)
    return values


def source_bindings(model,data,junction,schedule):
    expected={};nodes={n['node']:n for n in junction['nodes']}
    def assign(guid,sid,node):
        if sid not in schedule or guid in expected:raise ValueError('Unique original source-to-port flow binding required')
        model.by_guid(guid)
        expected[guid]=dict(source_section=sid,source_node=node,flow_m3_s=schedule[sid]['flow_m3_s'],classification='inherited preliminary design flow')
    for d in data['model']['devices']:
        objects=[o for o in model.by_type(d['ifc_class']) if o.Name==d['id']]
        if len(objects)!=1:raise ValueError('Unique original retained source body required')
        ports={p.Name:p for p in system.get_ports(objects[0])}
        if d['ifc_class']=='IfcDuctSegment':
            for p in ports.values():assign(p.GlobalId,d['id'],'retained source straight')
        else:
            node=nodes[d['properties']['SourceNode']]
            for pname,role in [('in','incoming'),('out','outgoing')]:
                arms=[r for r in node['incidents'] if r['role']==role]
                if len(arms)!=1:raise ValueError('One source arm for each native bend endpoint required')
                assign(ports[pname].GlobalId,arms[0]['section'],node['node'])
    previous=data['previous']
    for name,row in previous['tee_rows'].items():
        if name in previous['tee_blocked']:continue
        for arm,sid in row['binding']['arms'].items():
            assign(stable_guid(row['spec'],'IfcDistributionPort','RECTANGULAR-TEE',arm),sid,name)
            if arm in row['children']:
                for pname in ('start','end'):assign(stable_guid(row['children'][arm],'IfcDistributionPort',transition.KEY,pname),sid,name)
    for name,row in previous['rows'].items():
        if name in previous['blocked']:continue
        spec=row['data']['cross'];children=cross_composition.children(spec,row['data']['arms'])
        for arm,sid in row['binding'].items():
            assign(stable_guid(spec,'IfcDistributionPort',cross.KEY,arm),sid,name)
            if arm in children:
                for pname in ('start','end'):assign(stable_guid(children[arm],'IfcDistributionPort',transition.KEY,pname),sid,name)
    for row in data['fit']['external_interfaces']:assign(stable_guid(data['spec'],'IfcDistributionPort',compound_junction.KEY,row['compound_port']),row['section'],'compound external source interface')
    assign(stable_guid(data['spec'],'IfcDistributionPort',compound_junction.KEY,'upper'),data['fit']['absorbed_straight_sections'][0],'compound inlet source interface')
    if set(expected)!={p.GlobalId for p in model.by_type('IfcDistributionPort')}:raise ValueError('Every actual saved port needs an original source flow binding')
    return expected


def calculate(model,expected,air):
    if set(air)!={'density_kg_m3','viscosity_Pa_s','roughness_m'} or any(type(air[k]) not in (int,float) or not math.isfinite(air[k]) or air[k]<=0 for k in ('density_kg_m3','viscosity_Pa_s')) or type(air['roughness_m']) not in (int,float) or not math.isfinite(air['roughness_m']) or air['roughness_m']<0:raise ValueError('Exact source air conditions required')
    objects=model.by_type('IfcDistributionElement');owned={o.GlobalId:[p.GlobalId for p in system.get_ports(o)] for o in objects};directions={p.GlobalId:p.FlowDirection for p in model.by_type('IfcDistributionPort')};links=[(r.RelatingPort.GlobalId,r.RelatedPort.GlobalId) for r in model.by_type('IfcRelConnectsPorts')];values=prescribed_flows(owned,directions,links,expected)
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);ports={};products=[];straight=[];missing=[]
    for obj in objects:
        shape=ifcopenshell.geom.create_shape(settings,obj);vertices=np.array(shape.geometry.verts).reshape(-1,3);faces=np.array(shape.geometry.faces).reshape(-1,3)
        for p in system.get_ports(obj):
            cap=interface_contacts.cap(vertices,faces,placement.get_local_placement(p.ObjectPlacement));w,h=cap['inner_section_m'];q=values[p.GlobalId];velocity=q/(w*h)
            ports[p.GlobalId]=dict(**expected[p.GlobalId],graph_derived_flow_m3_s=q,owner_guid=obj.GlobalId,direction=p.FlowDirection,width_m=w,height_m=h,actual_velocity_m_s=velocity,actual_velocity_pressure_Pa=air['density_kg_m3']*velocity**2/2,flow_derivation='Actual saved downstream boundary-demand accumulation, reconciled against every original source section')
        incoming=[g for g in owned[obj.GlobalId] if directions[g]=='SINK'];outgoing=[g for g in owned[obj.GlobalId] if directions[g]=='SOURCE'];qin=math.fsum(values[g] for g in incoming);qout=math.fsum(values[g] for g in outgoing)
        if not math.isclose(qin,qout,rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Saved product flow continuity differs')
        products.append(dict(guid=obj.GlobalId,ifc_class=obj.is_a(),incoming_flow_m3_s=qin,outgoing_flow_m3_s=qout,continuity_pass=True))
        if obj.is_a('IfcDuctSegment'):
            body=obj.Representation.Representations[0].Items[0]
            if not body.is_a('IfcExtrudedAreaSolid') or not body.SweptArea.is_a('IfcRectangleHollowProfileDef') or len(outgoing)!=1:raise ValueError('Supported native rectangular straight required')
            first,last=[ports[g] for g in [incoming[0],outgoing[0]]];w,h=first['width_m'],first['height_m']
            if not np.allclose([w,h],[last['width_m'],last['height_m']],atol=1e-8,rtol=0):raise ValueError('Saved straight native end sections differ')
            friction=duct_equivalent.calculate(flow_m3_s=qin,width_m=w,height_m=h,**air);length=body.Depth
            if not math.isfinite(length) or length<=0:raise ValueError('Positive native straight length required')
            straight.append(dict(guid=obj.GlobalId,source_section=first['source_section'],length_m=length,width_m=w,height_m=h,flow_m3_s=qin,calculation=friction,straight_friction_Pa=friction['friction_Pa_m']*length))
        else:
            for a in incoming:
                for b in outgoing:missing.append(dict(product_guid=obj.GlobalId,ifc_class=obj.is_a(),predefined_type=obj.PredefinedType,inlet_port_guid=a,outlet_port_guid=b,coefficient=None,inlet_actual_velocity_m_s=ports[a]['actual_velocity_m_s'],outlet_actual_velocity_m_s=ports[b]['actual_velocity_m_s'],required_basis=['Applicable native fitting geometry, flow/area ratios and total-pressure path coefficient','Explicit actual-port reference velocity and cited source/edition applicability','Whole-fitting wall-friction inclusion convention; no hidden double counting']))
    connected={g for pair in links for g in pair};interfaces=[dict(source_port=a,sink_port=b,flow_m3_s=values[a],continuity_pass=math.isclose(values[a],values[b],rel_tol=1e-12,abs_tol=1e-12)) for a,b in links]
    if not all(r['continuity_pass'] for r in interfaces):raise ValueError('Saved linked port flows differ')
    boundaries={g:row for g,row in ports.items() if g not in connected};qin=math.fsum(values[g] for g in boundaries if directions[g]=='SINK');qout=math.fsum(values[g] for g in boundaries if directions[g]=='SOURCE')
    if not math.isclose(qin,qout,rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Whole represented boundary flow differs')
    paths=local.boundary_paths(ports,products,interfaces,straight,missing,boundaries)
    return dict(status='pending',port_flows=ports,products=products,interfaces=interfaces,boundary_ports=list(boundaries),boundary_inlet_flow_m3_s=qin,boundary_outlet_flow_m3_s=qout,flow_continuity_pass=True,straight_sections=straight,straight_friction_subtotal_Pa=math.fsum(r['straight_friction_Pa'] for r in straight),boundary_paths=paths,boundary_path_accounting_pass=True,missing_fitting_path_losses=missing,critical_path=None,complete_total_pressure_drop_Pa=None,pressure_budget_complete=False,design_accepted=False,scope='Source-prescribed complete represented graph flow continuity, native-cap velocities, saved straight-friction contributions and all boundary paths; missing fitting/joint, terminal/equipment and pressure requirements prevent fan duty or full engineering acceptance. Across-product straight subtotal is not system pressure.')


def prepare(source,folder):
    record=json.loads((source/'network.json').read_text());data=producer.prepare(Path(record['source']),folder/'source');old=data['previous'];tee_record=json.loads((old['tee_source']/'tee-candidates.json').read_text());selection=Path(tee_record['source']['selection']);selected=json.loads((selection/'selection.json').read_text());context=selected['source'];air,schedule,schedule_path,project=local.source_schedule(Path(context['plan']),Path(context['workflow']),context['native_task']);junction=json.loads((selection/'junction.json').read_text());model=ifcopenshell.open(str(source/'Supply Network.ifc'));expected=source_bindings(model,data,junction,schedule)
    result=calculate(model,expected,air)
    # The absorbed shared source section remains an explicit internal flow obligation.
    shared=data['fit']['absorbed_straight_sections'][1];upper,lower=[next(n for n in junction['nodes'] if n['node']==name) for name in data['fit']['source_nodes']];flows={row['source_section']:row['graph_derived_flow_m3_s'] for row in result['port_flows'].values()};qin=flows[data['fit']['absorbed_straight_sections'][0]];up=qin-math.fsum(flows[r['section']] for r in upper['incidents'] if r['role']=='outgoing' and r['section']!=shared);down=math.fsum(flows[r['section']] for r in lower['incidents'] if r['role']=='outgoing');wanted=schedule[shared]['flow_m3_s']
    if not math.isclose(up,wanted,rel_tol=1e-12,abs_tol=1e-12) or not math.isclose(down,wanted,rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Absorbed shared-source flow does not conserve')
    for row in result['straight_sections']:
        selected_row=schedule[row['source_section']]
        if not np.allclose([row['width_m'],row['height_m'],row['flow_m3_s']],[selected_row['width_m'],selected_row['height_m'],selected_row['flow_m3_s']],atol=1e-10,rtol=0):raise ValueError('Native retained straight dimensions/flow differ from source schedule')
    result.update(air=air,air_basis='Unchanged original selected schedule conditions, not measured installation properties',air_source_basis=dict(project=str(project),sha256=digest(project),basis=json.loads(project.read_text()).get('basis'),interpretation='Original source design conditions/assumptions, not measured properties'),internal_compound_source_flows=[dict(source_section=shared,flow_m3_s=wanted,upstream_derived_m3_s=up,downstream_derived_m3_s=down,continuity_pass=True)],original_requirement_ids=record['original_requirement_ids'],geometry_basis='Native saved material caps and straight extrusions of the verified compound construction; source scale/elevation/gauge assumptions retained')
    return result,[schedule_path,project]


def methods():
    import fluids.friction as friction
    if importlib.metadata.version('fluids')!='1.3.1':raise ValueError('Pinned fluids 1.3.1 required')
    return [Path(m.__file__) for m in (producer,local,duct_equivalent,interface_contacts,friction)]+[Path(__file__)]


def render(result):
    def table(headers,rows):return '<table><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'
    paths=[]
    for path in result['boundary_paths']:
        outlet=result['port_flows'][path['outlet_port_guid']]
        paths.append([outlet['source_section'],f"{path['outlet_flow_m3_s']*1000:.3f}",f"{path['known_straight_friction_Pa']:.5f}",path['missing_fitting_path_count'],'Pending'])
    straights=[[r['source_section'],f"{r['length_m']:.4f}",f"{r['width_m']*1000:.1f} × {r['height_m']*1000:.1f}",f"{r['flow_m3_s']*1000:.3f}",f"{r['calculation']['friction_Pa_m']:.5f}",f"{r['straight_friction_Pa']:.5f}"] for r in result['straight_sections']]
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Airflow and Pressure Path Review</title><style>body{font:16px/1.5 Arial;max-width:1200px;margin:30px auto;padding:20px;color:#243843}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{border:1px solid #ccd7dc;padding:8px;text-align:left}th{background:#eef4f6}.pending{background:#fff2d4;padding:16px}</style><h1>Airflow and Pressure Path Review</h1><p class="pending">Complete pressure and fan duty remain undetermined. '+str(len(result['missing_fitting_path_losses']))+' fitting flow paths require applicable loss data; joint, terminal and equipment losses and boundary pressures also remain unresolved.</p><p>Source-prescribed inlet and outlet design flow: '+f"{result['boundary_inlet_flow_m3_s']*1000:.3f}"+' L/s. Every saved port is reconciled to the original source. These are calculated design quantities, not measured installation flow.</p><h2>Separate outlet pressure paths</h2><p>Known values contain retained straight friction only. Parallel paths must not be summed, and their ordering does not establish the full critical path or a fan pressure requirement.</p>'+table(['Outlet source section','Design flow L/s','Known straight friction Pa','Missing fitting paths','Complete path pressure'],paths)+'<h2>Retained native straight sections</h2><p>Original equivalent-round/Colebrook friction method with inherited air conditions. Actual saved lengths and clear sections are used; fitting body friction is unresolved.</p>'+table(['Source section','Native length m','Clear size mm','Design flow L/s','Friction Pa/m','Straight contribution Pa'],straights)+'<p>Original source scale, elevation, gauge and air-property assumptions remain. Physical installation, products, fitting losses and full engineering acceptance are pending.</p><p><a href="analysis.json">Source and numerical evidence</a></p></html>'


def run(source,out):
    source,out=[Path(p).resolve() for p in (source,out)]
    if not all(allowed(p) for p in (source,out)) or out.exists() or out.is_relative_to(source) or source.is_relative_to(out):raise ValueError('Fresh selected workspace outside source required')
    producer.verify(source);pins={str(p):digest(p) for p in [source/'network.json',source/'Supply Network.ifc',*methods()]};result,inputs=prepare(source,out/'inputs');pins.update({str(p):digest(p) for p in inputs})
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Network analysis source/method changed')
    result.update(source=str(source),inputs=pins,complete_network=False)
    (out/'Airflow and Pressure Paths.html').write_text(render(result),encoding='utf-8');result['report_sha256']=digest(out/'Airflow and Pressure Paths.html');(out/'analysis.json').write_text(json.dumps(result,indent=2));return result


def verify(out):
    out=Path(out).resolve()
    if not allowed(out):raise ValueError('Selected workspace required')
    report=json.loads((out/'analysis.json').read_text());source=Path(report['source']);producer.verify(source)
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='network-analysis-audit-') as folder:
        fresh,inputs=prepare(source,Path(folder));pins={str(p):digest(p) for p in [source/'network.json',source/'Supply Network.ifc',*methods(),*inputs]}
        if report['inputs']!=pins or report['complete_network'] is not False or any(report.get(k)!=v for k,v in fresh.items()) or digest(out/'Airflow and Pressure Paths.html')!=report['report_sha256'] or (out/'Airflow and Pressure Paths.html').read_text(encoding='utf-8')!=render(fresh):raise ValueError('Network flow/native/pressure-path/report replay differs')
    return dict(integrity_pass=True,ports=len(fresh['port_flows']),straight_sections=len(fresh['straight_sections']),outlet_paths=len(fresh['boundary_paths']),missing_fitting_paths=len(fresh['missing_fitting_path_losses']),flow_continuity_pass=True,pressure_budget_complete=False,design_accepted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);a=s.add_parser('run');a.add_argument('source');a.add_argument('--out',required=True);s.add_parser('verify').add_argument('out');a=p.parse_args();r=run(a.source,a.out) if a.command=='run' else verify(a.out);print(json.dumps({k:r[k] for k in (('flow_continuity_pass','boundary_inlet_flow_m3_s','boundary_outlet_flow_m3_s','pressure_budget_complete','design_accepted') if a.command=='run' else r)},indent=2));raise SystemExit(2)
