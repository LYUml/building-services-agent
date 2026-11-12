"""Native short-stub straight friction using inherited flows/density and existing fluids engine."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import ifcopenshell
import ifcopenshell.util.element as element
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.unit as unit
import fluids.core as core
import fluids.friction as friction
from . import spatial_terminal_stubs as stubs,network
from .cli import digest
from .module_contract import read_json
from .workspace import allowed


def point(flow_L_s,diameter_m,length_m,density,viscosity,roughness,dz):
    values=(flow_L_s,diameter_m,length_m,density,viscosity,roughness,dz)
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values) or min(values[:5])<=0 or roughness<0 or roughness/diameter_m>=.05:raise ValueError('Finite supported positive straight-friction quantities required')
    flow=flow_L_s/1000;area=math.pi*diameter_m**2/4;velocity=flow/area;re=core.Reynolds(V=velocity,D=diameter_m,rho=density,mu=viscosity)
    base=dict(flow_L_s=flow_L_s,flow_m3_s=flow,velocity_m_s=velocity,reynolds=re,relative_roughness=roughness/diameter_m,
        signed_geometric_rho_g_dz_Pa=density*network.GRAVITY*dz)
    if not all(math.isfinite(v) for v in (flow,area,velocity,re,base['signed_geometric_rho_g_dz_Pa'])) or min(flow,area,velocity,re)<=0:raise ValueError('Derived straight-friction quantities outside numerical range')
    if 2000<=re<4000:return dict(base,status='pending',darcy_friction_factor=None,straight_friction_Pa=None,regime='transitional model unsupported;source-backed method required')
    factor,regime=network.friction_factor(re,roughness/diameter_m);loss=core.dP_from_K(core.K_from_f(factor,length_m,diameter_m),density,velocity)
    if not all(math.isfinite(v) for v in (velocity,re,factor,loss,base['signed_geometric_rho_g_dz_Pa'])) or loss<0:raise ValueError('Straight-friction result outside numerical range')
    return dict(base,status='calculated',darcy_friction_factor=factor,straight_friction_Pa=loss,regime=regime)


def prepare(source,basis):
    before=digest(source);report=stubs.verify(source.parent)
    if source.name!='terminal-stubs.json':raise ValueError('Exact verified short-stub report required')
    pins=dict(report['inputs']);pins[str(source)]=before;pins[str(basis)]=digest(basis)
    def pinned_json(path):
        path=Path(path).resolve();expected=pins.get(str(path))
        if expected is None or not allowed(path) or digest(path)!=expected:raise ValueError('Inherited analysis ancestry changed or omitted')
        data=read_json(path)
        if digest(path)!=expected:raise ValueError('Analysis ancestry changed while reading')
        return data
    inlet=pinned_json(report['inlets']);envelopes=pinned_json(inlet['terminal_ifc']);performance=pinned_json(envelopes['performance']);allocation=pinned_json(performance['allocation_result']);balance=pinned_json(allocation['balance_result'])
    spec=read_json(basis)
    if not isinstance(spec,dict) or set(spec)!={'dynamic_viscosity_pa_s','roughness_m'}:raise ValueError('Viscosity and roughness basis only;replacement flow,length,bore or density forbidden')
    for key,row in spec.items():
        if not isinstance(row,dict) or set(row)!={'value','unit','source','classification'} or type(row['value']) not in (int,float) or not math.isfinite(row['value']) or (row['value']<0 if key=='roughness_m' else row['value']<=0) or row['unit']!=('m' if key=='roughness_m' else 'Pa.s') or not isinstance(row['source'],str) or not row['source'].strip() or row['classification'] not in ('given','measured','assumed','secondary_transcription','design_choice'):raise ValueError('Explicit source-classified viscosity/roughness with SI units required')
    if importlib.metadata.version('fluids')!='1.3.1':raise ValueError('Pinned fluids1.3.1 required')
    target=source.parent/'Terminal Stub Study.ifc';pins[str(target)]=report['ifc_sha256'];model=ifcopenshell.open(str(target));scale=unit.calculate_unit_scale(model);rows={};requests=[]
    for record in report['stubs']:
        obj=model.by_guid(record['stub_guid']);body=[r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body']
        if len(body)!=1 or len(body[0].Items)!=1:raise ValueError('Exact saved straight-wall body required')
        solid=body[0].Items[0];profile=solid.SweptArea
        if not solid.is_a('IfcExtrudedAreaSolid') or not profile.is_a('IfcCircleHollowProfileDef'):raise ValueError('Saved circular hollow profile required')
        diameter=2*(profile.Radius-profile.WallThickness)*scale;length=solid.Depth*scale;ports=system.get_ports(obj);starts=[p for p in ports if p.FlowDirection=='SINK'];ends=[p for p in ports if p.FlowDirection=='SOURCE']
        if len(starts)!=1 or len(ends)!=1:raise ValueError('Directed saved stub boundary ports required')
        start=placement.get_local_placement(starts[0].ObjectPlacement)[:3,3]*scale;end=placement.get_local_placement(ends[0].ObjectPlacement)[:3,3]*scale
        if not math.isclose(math.dist(start,end),length,rel_tol=0,abs_tol=1e-8):raise ValueError('Saved profile length differs from native port separation')
        guid=element.get_container(obj).GlobalId;density=balance['calculation']['room_balances'][guid]['inputs']['density'];properties=element.get_psets(obj)['BSA_DesignInputs'];cases={}
        for name,key in [('maximum','MaximumFlow_L_s'),('minimum','MinimumFlow_L_s')]:
            cases[name]=point(properties[key],diameter,length,density['value'],spec['dynamic_viscosity_pa_s']['value'],spec['roughness_m']['value'],float(end[2]-start[2]))
            if cases[name]['status']=='pending':requests.append(dict(terminal=record['terminal'],condition=name,code='transitional_flow_method_required',reynolds=cases[name]['reynolds']))
        rows[record['terminal']]=dict(stub_guid=obj.GlobalId,space_guid=guid,inlet_port_guid=starts[0].GlobalId,outlet_port_guid=ends[0].GlobalId,
            native_length_m=length,native_internal_diameter_m=diameter,inlet_point_m=start.tolist(),outlet_point_m=end.tolist(),inherited_density=density,inherited_stub_basis=json.loads(properties['StubBasisJSON']),length_over_diameter=length/diameter,cases=cases)
    for module in (stubs,network,core,friction):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    if digest(source)!=before or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Straight-friction source/method changed')
    calculation=dict(schema='bsa.terminal-straight-friction/1',units=dict(flow='L/s',length='m',pressure='Pa'),basis=spec,terminals=rows,status='pending' if requests else 'calculated',data_requests=requests,
        engineering_status='pending',fully_developed_flow_verified=False,air_state_verified=False,whole_system_pressure_complete=False,fan_selection_complete=False,regulatory_acceptance=False,design_accepted=False,
        scope='Incompressible constant-property fully-developed straight-wall friction component only;short-duct entrance/developing-flow applicability is unverified. Signed rho*g*dz is a separate geometric diagnostic,not fan duty or ambient-reference pressure. No parallel pressure sum,minor losses,terminal total/static pressure or whole-network acceptance')
    return calculation,pins


def run(source,basis,out):
    source,basis,out=[Path(p).resolve() for p in (source,basis,out)]
    if not all(allowed(p) for p in (source,basis,out)) or out.exists():raise ValueError('Selected stub source,basis and fresh analysis output required')
    calculation,pins=prepare(source,basis)
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Analysis output overlaps source inputs')
    result=dict(stubs=str(source),basis=str(basis),inputs=pins,calculation=calculation,design_accepted=False)
    out.mkdir(parents=True);(out/'straight-friction.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected friction workspace required')
    result=read_json(folder/'straight-friction.json')
    if set(result)!={'stubs','basis','inputs','calculation','design_accepted'} or result['design_accepted'] is not False:raise ValueError('Exact unaccepted straight-friction report required')
    source=Path(result['stubs']);basis=Path(result['basis'])
    if not allowed(source) or not allowed(basis):raise ValueError('Selected original analysis sources required')
    calculation,pins=prepare(source,basis)
    if pins!=result['inputs'] or calculation!=result['calculation']:raise ValueError('Straight-friction result differs from source/native replay')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('--basis',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.source,args.basis,args.out)
