"""Extend a checked local chain's pressure budget to its explicit open boundaries."""
import argparse
import copy
import importlib.metadata
import json
import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element as element
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.unit as unit

from . import network, circular_geometry as circular, circular_elbow as elbow
from .cli import digest
from .engine import ProjectError
from .module_contract import read_json
from .workspace import allowed
from .circular_native import straight_wall
from .product_alignment import aligned_placement
import numpy as np
import fluids.core as fluid_core
import fluids.friction as fluid_friction


def validate(policy):
    keys={'source','classification','pressure_reference','boundary_values','roughness_scope','source_wall_excess_k','interface_excess_k'}
    if not isinstance(policy,dict) or set(policy)!=keys or not isinstance(policy['source'],str) or not policy['source'].strip() or policy['classification'] not in ('assumed','design_choice'):
        raise ProjectError('Exact explicit classified boundary/loss policy required')
    if policy['pressure_reference']!='common-elevation-datum' or policy['boundary_values']!='inherit_numeric_values_at_extended_open_caps' or policy['roughness_scope']!='apply_original_segment_roughness_to_all_local_walls':
        raise ProjectError('Explicit supported pressure-reference, boundary and roughness decisions required')
    walls=policy['source_wall_excess_k']
    if not isinstance(walls,dict) or set(walls)!={'start','end'}:
        raise ProjectError('Both source-wall excess K decisions required')
    for row in [*walls.values(),policy['interface_excess_k']]:
        if not isinstance(row,dict) or set(row)!={'value','unit','source','classification','loss_basis'} or row['unit']!='dimensionless' or row['loss_basis']!=elbow.LOSS_BASIS or row['classification'] not in ('given','measured','assumed','design_choice','secondary_transcription') or not isinstance(row['source'],str) or not row['source'].strip() or type(row['value']) not in (float,int) or not math.isfinite(row['value']) or row['value']<0:
            raise ProjectError('Finite nonnegative sourced dimensionless excess K required; no default loss')
    return policy


def derive(ifc,owners,canonical,original,policy):
    validate(policy)
    if len(original.get('segments',[]))!=1 or len(original.get('nodes',[]))!=2:
        raise ProjectError('One inherited prescribed-flow path with two boundary nodes required')
    segment=original['segments'][0]
    if any(k in segment for k in ('length_m','diameter_m')) or any('elevation_m' in n for n in original['nodes']):
        raise ProjectError('Inherited skeleton must not duplicate saved geometry')
    if 'minor_k' in segment:
        values=[d.get('properties',{}).get('LocalLossCoefficient') for d in canonical['devices']]
        if any(d.get('body_shape')==elbow.WALL for d in canonical['devices']) or type(segment['minor_k']) not in (int,float) or not values or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values) or not math.isclose(segment['minor_k'],math.fsum(values),rel_tol=0,abs_tol=1e-10):
            raise ProjectError('Inherited straight aggregate K must exactly reconcile to canonical body losses')
    model=ifcopenshell.open(str(ifc))
    if model.schema!='IFC4' or not math.isclose(unit.calculate_unit_scale(model),1.,rel_tol=0,abs_tol=1e-12):
        raise ProjectError('Saved IFC4 metre chain required')
    owners=set(owners);objects={o.GlobalId:o for o in model.by_type('IfcElement') if o.GlobalId in owners}
    if set(objects)!=owners:raise ProjectError('Exact saved local owner coverage required')
    route={}
    for d in canonical['devices']:
        matches=[o for o in objects.values() if o.Name==d['id'] and o.is_a()==d['ifc_class']]
        if len(matches)!=1:raise ProjectError('Unambiguous native canonical route identity required')
        route[matches[0].GlobalId]=d
    if len(owners-set(route))!=2:raise ProjectError('Exactly two source walls beyond the searched route required')
    ends={};ports={}
    for guid,obj in objects.items():
        native=system.get_ports(obj);ins=[p for p in native if p.FlowDirection=='SINK'];outs=[p for p in native if p.FlowDirection=='SOURCE']
        if len(native)!=2 or len(ins)!=1 or len(outs)!=1:raise ProjectError('Each local body needs exactly one SINK and one SOURCE')
        ends[guid]=(ins[0],outs[0]);ports.update({p.GlobalId:guid for p in native})
    pairs=[(r.RelatingPort.GlobalId,r.RelatedPort.GlobalId) for r in model.by_type('IfcRelConnectsPorts') if r.RelatingPort.GlobalId in ports and r.RelatedPort.GlobalId in ports]
    outgoing={};incoming=set()
    for a,b in pairs:
        if a in outgoing or b in incoming:raise ProjectError('One peer per connected local port required')
        if model.by_guid(a).FlowDirection!='SOURCE' or model.by_guid(b).FlowDirection!='SINK':raise ProjectError('Directed local SOURCE-to-SINK links required')
        outgoing[a]=b;incoming.add(b)
    starts=[g for g,(p,_) in ends.items() if p.GlobalId not in incoming]
    if len(starts)!=1:raise ProjectError('One open upstream local boundary required')
    order=[];current=starts[0]
    while current not in order:
        order.append(current);target=outgoing.get(ends[current][1].GlobalId)
        if target is None:break
        current=ports[target]
    if len(order)!=len(owners) or outgoing.get(ends[order[-1]][1].GlobalId) is not None or {order[0],order[-1]}!=owners-set(route):
        raise ProjectError('Every local body must lie between the two outer source-wall caps')
    if any(p.ConnectedTo or p.ConnectedFrom for p in (ends[order[0]][0],ends[order[-1]][1])):
        raise ProjectError('Outer pressure boundaries must be genuinely open; external peers need another declared boundary contract')
    ledger=[]
    for index,guid in enumerate(order):
        obj=objects[guid];inlet,outlet=ends[guid];points=[placement.get_local_placement(p.ObjectPlacement)[:3,3].tolist() for p in (inlet,outlet)]
        props=element.get_psets(obj).get('BSA_DesignInputs',{})
        if guid in route:
            d=route[guid];module=elbow if d.get('body_shape')==elbow.WALL else circular;spec=module.specification(d)
            if module is elbow:
                length,arc_ends,_=elbow.saved_arc_length(obj)
                if not math.isclose(length,spec['length_m'],rel_tol=0,abs_tol=1e-8) or not all(any(math.dist(p,q)<1e-8 for q in arc_ends) for p in points):raise ProjectError('Saved route arc/ports differ from canonical source')
            else:
                native=straight_wall(obj);length=native['length_m']
                if not math.isclose(native['inner_m'],spec['inner_m'],rel_tol=0,abs_tol=1e-10) or not math.isclose(length,spec['length_m'],rel_tol=0,abs_tol=1e-8):raise ProjectError('Native straight route differs from canonical bore/length')
            for port in (inlet,outlet):
                declared=[p for p in d['ports'] if p['id']==port.Name and p['direction']==port.FlowDirection]
                frame=placement.get_local_placement(port.ObjectPlacement);aligned_placement(frame,np.eye(4),0)
                if len(declared)!=1 or port.Name not in spec['normals'] or not np.allclose(frame[:3,3],np.asarray(d['origin_m'])+declared[0]['offset_m'],atol=1e-8,rtol=0) or not np.allclose(frame[:3,2],spec['normals'][port.Name],atol=1e-8,rtol=0):
                    raise ProjectError('Canonical route cap station/direction differs from saved port')
            bore=spec['inner_m'];k=d['properties'].get('LocalLossCoefficient')
            if type(k) not in (int,float) or not math.isfinite(k) or k<0 or props.get('LocalLossBasis')!=elbow.LOSS_BASIS or props.get('LocalLossCoefficient')!=k or props.get('InternalDiameter_m')!=bore:
                raise ProjectError('Canonical route body excess K/bore must match saved metadata')
            loss_basis=dict(value=k,source=canonical['sources'][d['source']],classification='inherited source text; canonical contract has no separate K classification',loss_basis=elbow.LOSS_BASIS)
        else:
            native=straight_wall(obj);bore=native['inner_m'];length=native['length_m']
            if not math.isclose(length,math.dist(*points),rel_tol=0,abs_tol=1e-8):raise ProjectError('Source native depth and cap separation differ')
            loss_basis=policy['source_wall_excess_k']['start' if index==0 else 'end'];k=loss_basis['value']
            if 'LocalLossCoefficient' in props and (type(props['LocalLossCoefficient']) not in (int,float) or not math.isclose(props['LocalLossCoefficient'],k,rel_tol=0,abs_tol=1e-10) or props.get('LocalLossBasis')!=elbow.LOSS_BASIS):
                raise ProjectError('Explicit source-wall loss policy conflicts with saved source K/basis')
        if not math.isfinite(length) or length<=0 or not math.isfinite(bore) or bore<=0:raise ProjectError('Positive finite native length/bore required')
        joint=policy['interface_excess_k']['value'] if index<len(order)-1 else 0
        ledger.append(dict(owner_guid=guid,name=obj.Name,inlet_port_guid=inlet.GlobalId,outlet_port_guid=outlet.GlobalId,
            from_point_m=points[0],to_point_m=points[1],length_m=length,diameter_m=bore,body_excess_k=k,body_loss_basis=loss_basis,
            downstream_interface_excess_k=joint,interface_loss_basis=policy['interface_excess_k'] if index<len(order)-1 else None,
            original_geometry_source=props.get('Source'),
            geometry_classification='geometry-derived from saved source/canonical route; original assumed construction remains unverified'))
    if any(not math.isclose(r['diameter_m'],ledger[0]['diameter_m'],rel_tol=0,abs_tol=1e-10) for r in ledger):raise ProjectError('Uniform-bore local pressure path required')
    for first,second in zip(ledger,ledger[1:]):
        if math.dist(first['to_point_m'],second['from_point_m'])>1e-8:raise ProjectError('Actual saved local cap stations must coincide')
    result=copy.deepcopy(original);key='joined_boundary_policy'
    if key in result['sources']:raise ProjectError('Reserved joined-boundary source key already present')
    result['sources'][key]=policy['source']+'; original numeric properties, supply, demand and targets inherited from original sources'
    result['supply']['source']=key
    nodes={n['id']:n for n in result['nodes']}
    if segment['from']!=result['supply']['node'] or set(nodes)!={segment['from'],segment['to']}:raise ProjectError('Original source-to-terminal boundary identity required')
    for node,point in [(segment['from'],ledger[0]['from_point_m']),(segment['to'],ledger[-1]['to_point_m'])]:
        nodes[node]['elevation_m']=point[2];nodes[node]['source']=key
    result['segments'][0].update(length_m=math.fsum(r['length_m'] for r in ledger),diameter_m=ledger[0]['diameter_m'],minor_k=math.fsum(r['body_excess_k']+r['downstream_interface_excess_k'] for r in ledger),source=key)
    network.validate(result)
    return result,ledger


def run(producer,basis,out):
    producer,basis,out=[Path(p).resolve() for p in (producer,basis,out)]
    if out.exists() or not all(allowed(p) for p in (producer,basis,out)) or producer==out or producer in out.parents or out in producer.parents or out==basis or out in basis.parents:
        raise ProjectError('Fresh selected-workspace pressure output outside all sources required')
    versions={name:importlib.metadata.version(name) for name in ('fluids','ifcopenshell','numpy')}
    if versions!={'fluids':'1.3.1','ifcopenshell':'0.8.5','numpy':'2.5.4'}:raise ProjectError('Pinned pressure/IFC engines required')
    receipt=producer/'route-material.json';material=read_json(receipt)
    if material.get('calculated_checks_pass') is not True or material.get('design_accepted') is not False:raise ProjectError('Passing local material QA required before extended pressure')
    inputs={**material['inputs'],**material['method_inputs'],str(receipt):digest(receipt),str(basis):digest(basis)}
    for path,sha in inputs.items():
        if not allowed(Path(path)) or digest(Path(path))!=sha:raise ProjectError('Inherited material/source/method changed')
    canonical=[Path(p) for p in inputs if Path(p).name=='model-input.json'];joined=[Path(p) for p in inputs if Path(p).name=='joined.ifc']
    if len(canonical)!=1 or len(joined)!=1:raise ProjectError('Exact canonical route and saved joined IFC required')
    skeleton=canonical[0].parent/'network-source.json'
    if str(skeleton) not in inputs:raise ProjectError('Original geometry-free network skeleton must be inherited')
    methods={str(Path(p).resolve()):digest(Path(p)) for p in (__file__,network.__file__,circular.__file__,elbow.__file__,straight_wall.__code__.co_filename,aligned_placement.__code__.co_filename,fluid_core.__file__,fluid_friction.__file__)}
    policy=validate(read_json(basis));derived,ledger=derive(joined[0],material['local_chain_owners'],read_json(canonical[0]),read_json(skeleton),policy)
    out.mkdir(parents=True);generated=out/'network-input.json';generated.write_text(json.dumps(derived,indent=2),encoding='utf-8')
    calculation=network.run(generated,out/'analysis');segment=calculation['segments'][0];gradient=segment['friction_pa']/derived['segments'][0]['length_m'];dynamic=derived['fluid']['density_kg_m3']*segment['velocity_m_s']**2/2
    pressure=derived['supply']['total_pressure_pa']
    for row in ledger:
        row['friction_pa']=gradient*row['length_m'];row['minor_pa']=dynamic*(row['body_excess_k']+row['downstream_interface_excess_k'])
        row['elevation_pressure_pa']=derived['fluid']['density_kg_m3']*network.GRAVITY*(row['to_point_m'][2]-row['from_point_m'][2]);row['upstream_total_pressure_pa']=pressure
        pressure-=row['friction_pa']+row['minor_pa']+row['elevation_pressure_pa'];row['downstream_total_pressure_pa']=pressure
        row['intermediate_pressure_acceptance']=None
    final=next(n['total_pressure_pa'] for n in calculation['nodes'] if n['id']==derived['segments'][0]['to'])
    if not math.isclose(pressure,final,rel_tol=0,abs_tol=1e-8):raise ProjectError('Native body ledger does not reconcile to network engine result')
    if any(digest(Path(p))!=sha for p,sha in {**inputs,**methods}.items()):raise ProjectError('Extended pressure source or method changed during calculation')
    report=dict(inputs=inputs,method_inputs=methods,runtime_versions=versions,policy=policy,ledger=ledger,length_m=derived['segments'][0]['length_m'],aggregate_excess_k=derived['segments'][0]['minor_k'],boundary_ports={'start':ledger[0]['inlet_port_guid'],'end':ledger[-1]['outlet_port_guid']},
        inherited_straight_aggregate_k_reconciled='minor_k' in read_json(skeleton)['segments'][0],
        boundary_value_decision='Original numeric supply/target explicitly applied at different outer source-wall cap stations; no equivalence with original stations asserted',
        calculated_checks_pass=calculation['calculated_checks_pass'],design_accepted=False,
        scope='Uniform-bore prescribed-flow local chain including both source walls; explicit common-reference pressure/boundary/roughness/K assumptions. No ambient-gauge fan duty, operating-point solution, intermediate pressure acceptance, product or regulatory approval')
    report['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'route-pressure.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('producer',type=Path);parser.add_argument('--basis',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=run(args.producer,args.basis,args.out);print(json.dumps({'length_m':result['length_m'],'aggregate_excess_k':result['aggregate_excess_k'],'calculated_checks_pass':result['calculated_checks_pass'],'design_accepted':False}));raise SystemExit(0 if result['calculated_checks_pass'] else 2)
