"""Add explicitly sourced logical inlet ports to verified terminal envelopes."""
import argparse
import json
import math
import uuid
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.validate
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.element as element
import ifcopenshell.util.unit as unit
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from . import spatial_terminal_ifc as author,circular_geometry


def prepare(source,basis):
    report=author.verify(source.parent)
    if source.name!='terminal-ifc.json':raise ValueError('Exact verified terminal IFC report required')
    target=source.parent/'Terminal Envelope Study.ifc';model=ifcopenshell.open(str(target));scale=unit.calculate_unit_scale(model)
    data=read_json(basis);terminals={r['id']:r for r in report['terminals']}
    if not isinstance(data,dict) or set(data)!=set(terminals):raise ValueError('Inlet basis must cover every terminal exactly')
    rows=[];systems={};classes={'given','measured','assumed','secondary_transcription','design_choice'}
    for name,terminal in terminals.items():
        row=data[name]
        if not isinstance(row,dict) or set(row)!={'offset_m','outward_axis','diameter_m','system'}:raise ValueError('Exact inlet position,axis,diameter and system basis required')
        for key,record in row.items():
            fields={'id','predefined_type','source','classification'} if key=='system' else {'value','unit','source','classification'}
            if not isinstance(record,dict) or set(record)!=fields or not isinstance(record['source'],str) or not record['source'].strip() or not isinstance(record['classification'],str) or record['classification'] not in classes:raise ValueError('Source-classified inlet/system quantities required')
            if key!='system' and record['unit']!=('1' if key=='outward_axis' else 'm'):raise ValueError('Explicit SI inlet units required')
        group=row['system']
        if not isinstance(group['id'],str) or not group['id'].strip() or group['predefined_type'] not in ('AIRCONDITIONING','VENTILATION'):raise ValueError('Explicit air-system identity/type required')
        if group['id'] in systems and systems[group['id']]!=group:raise ValueError('Repeated system identity has conflicting basis')
        systems[group['id']]=group
        obj=model.by_guid(terminal['guid']);props=element.get_psets(obj)['BSA_SpatialTerminal'];size=json.loads(props['BasisJSON'])['size_m']['value']
        offset=row['offset_m']['value'];normal=row['outward_axis']['value'];diameter=row['diameter_m']['value']
        if any(not isinstance(v,list) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in v) for v in (offset,normal)) or type(diameter) not in (int,float) or not math.isfinite(diameter) or diameter<=0:raise ValueError('Finite inlet vectors and positive diameter required')
        axes=[i for i,x in enumerate(normal) if x!=0]
        if len(axes)!=1 or abs(normal[axes[0]])!=1:raise ValueError('Envelope inlet requires one cardinal outward unit axis')
        axis=axes[0];face=size[axis] if normal[axis]>0 else 0
        if abs(offset[axis]-face)>1e-8 or any(offset[i]-diameter/2<0 or offset[i]+diameter/2>size[i] for i in range(3) if i!=axis):raise ValueError('Declared circular inlet must fit its outward envelope face')
        matrix=placement.get_local_placement(obj.ObjectPlacement);matrix[:3,3]*=scale
        point=(matrix@np.array([*offset,1.]))[:3];direction=matrix[:3,:3]@np.array(normal)
        rows.append(dict(id=name,guid=terminal['guid'],point_m=point.tolist(),axis=direction.tolist(),diameter_m=diameter,basis=row))
    pins=dict(report['inputs']);pins[str(source)]=digest(source);pins[str(target)]=digest(target);pins[str(basis)]=digest(basis)
    for module in (author,circular_geometry):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    return target,rows,systems,pins


def stable(source,role,name):
    projects=ifcopenshell.open(str(source)).by_type('IfcProject')
    if len(projects)!=1:raise ValueError('One inherited IFC project identity required')
    return ifcopenshell.guid.compress(uuid.uuid5(uuid.uuid5(uuid.NAMESPACE_URL,projects[0].GlobalId),role+':'+name).hex)


def inspect(source,target,rows,systems):
    original=ifcopenshell.open(str(source));model=ifcopenshell.open(str(target));scale=unit.calculate_unit_scale(model)
    for obj in original:
        if model.by_id(obj.id()).to_string()!=obj.to_string():raise ValueError('Original IFC entity changed during inlet authoring')
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(model,logger,express_rules=True)
    if logger.statements:raise ValueError('Port IFC schema/EXPRESS validation failed')
    if len(model.by_type('IfcDistributionPort'))!=len(original.by_type('IfcDistributionPort'))+len(rows) or len(model.by_type('IfcDistributionSystem'))!=len(original.by_type('IfcDistributionSystem'))+len(systems) or len(model.by_type('IfcRelConnectsPorts'))!=len(original.by_type('IfcRelConnectsPorts')):raise ValueError('Unexpected added ports,systems or links')
    records=[]
    for row in rows:
        obj=model.by_guid(row['guid']);ports=system.get_ports(obj)
        if len(ports)!=1:raise ValueError('Exactly one declared terminal inlet required')
        port=ports[0];matrix=placement.get_local_placement(port.ObjectPlacement);point=matrix[:3,3]*scale
        if port.GlobalId!=stable(source,'inlet',row['id']) or port.Name!=row['id']+'_inlet' or port.FlowDirection!='SINK' or port.PredefinedType!='DUCT' or port.SystemType!=row['basis']['system']['predefined_type'] or port.ConnectedFrom or port.ConnectedTo:raise ValueError('Inlet identity/direction/type or unintended connection differs')
        if not np.allclose(point,row['point_m'],atol=1e-8,rtol=0) or not np.allclose(matrix[:3,2],row['axis'],atol=1e-8,rtol=0):raise ValueError('Saved inlet position/outward axis differs')
        props=element.get_psets(port)['BSA_InletBasis']
        if props.get('Diameter_m')!=row['diameter_m'] or props.get('BasisJSON')!=json.dumps(row['basis'],sort_keys=True):raise ValueError('Saved inlet source/diameter differs')
        assigned=system.get_element_systems(obj);expected=stable(source,'system',row['basis']['system']['id'])
        if {s.GlobalId for s in assigned}!={expected}:raise ValueError('Saved terminal system differs')
        group=model.by_guid(expected)
        if group.Name!=row['basis']['system']['id'] or group.PredefinedType!=row['basis']['system']['predefined_type']:raise ValueError('Saved system identity/type differs')
        records.append(dict(terminal=row['id'],terminal_guid=obj.GlobalId,port_guid=port.GlobalId,point_m=point.tolist(),outward_axis=matrix[:3,2].tolist(),diameter_m=row['diameter_m'],system_guid=expected))
    return records


def run(source,basis,out):
    source,basis,out=[Path(p).resolve() for p in (source,basis,out)]
    if not all(allowed(p) for p in (source,basis,out)) or out.exists():raise ValueError('Selected source/basis and new inlet output required')
    before=digest(source);target,rows,systems,pins=prepare(source,basis)
    if before!=pins[str(source)] or any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Inlet source changed or output overlaps sources')
    model=ifcopenshell.open(str(target));groups={}
    new_guids=[stable(target,'system',key) for key in systems]+[stable(target,'inlet',row['id']) for row in rows]
    if set(new_guids)&{obj.GlobalId for obj in model.by_type('IfcRoot')}:raise ValueError('Inlet/system GUID collision')
    for key,basis_row in systems.items():groups[key]=model.create_entity('IfcDistributionSystem',GlobalId=stable(target,'system',key),Name=key,PredefinedType=basis_row['predefined_type'])
    for row in rows:
        obj=model.by_guid(row['guid']);port=api.run('system.add_port',model,element=obj);port.GlobalId=stable(target,'inlet',row['id']);port.Name=row['id']+'_inlet';port.FlowDirection='SINK';port.PredefinedType='DUCT';port.SystemType=row['basis']['system']['predefined_type']
        matrix=circular_geometry.frame(row['axis']);matrix[:3,3]=row['point_m'];api.run('geometry.edit_object_placement',model,product=port,matrix=matrix,is_si=True)
        api.run('system.assign_system',model,products=[obj],system=groups[row['basis']['system']['id']])
        pset=api.run('pset.add_pset',model,product=port,name='BSA_InletBasis');api.run('pset.edit_pset',model,pset=pset,properties=dict(Diameter_m=row['diameter_m'],BasisJSON=json.dumps(row['basis'],sort_keys=True)))
    out.mkdir(parents=True);output=out/'Terminal Inlet Study.ifc';model.write(str(output));records=inspect(target,output,rows,systems)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Inlet source/method changed')
    result=dict(terminal_ifc=str(source),basis=str(basis),inputs=pins,ifc_sha256=digest(output),inlets=records,original_entities_unchanged=True,design_accepted=False,
        scope='Source-classified logical SINK ports on envelope faces and declared air-system groups only;no body opening,duct connection,physical joint or installed product is inferred')
    (out/'terminal-inlets.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected inlet workspace required')
    result=read_json(folder/'terminal-inlets.json')
    if set(result)!={'terminal_ifc','basis','inputs','ifc_sha256','inlets','original_entities_unchanged','design_accepted','scope'} or result['design_accepted'] is not False:raise ValueError('Exact unaccepted inlet report required')
    source=Path(result['terminal_ifc']);basis=Path(result['basis'])
    if not all(allowed(p) for p in (source,basis)):raise ValueError('Selected original inlet sources required')
    target,rows,systems,pins=prepare(source,basis);output=folder/'Terminal Inlet Study.ifc'
    if pins!=result['inputs'] or any(digest(Path(p))!=sha for p,sha in pins.items()) or digest(output)!=result['ifc_sha256']:raise ValueError('Inlet source/output pins differ')
    if inspect(target,output,rows,systems)!=result['inlets'] or result['original_entities_unchanged'] is not True:raise ValueError('Saved inlet replay differs')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('--basis',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.source,args.basis,args.out)
