"""Add source-classified terminal envelopes to an inherited IFC without replacing rooms."""
import argparse
import importlib.metadata
import json
import math
import uuid
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.validate
import ifcopenshell.util.element as element
from shapely.geometry import Polygon,box
from .cli import digest
from .module_contract import read_json
from .modules import verify_result
from .workspace import allowed
from . import spatial_terminal_performance as performance,spatial_air_allocation as allocation,spatial_air_balance as balance,box_geometry


def prepare(path,basis):
    report=performance.verify(path.parent)
    if path.name!='terminal-performance.json':raise ValueError('Exact verified performance report required')
    allocations=allocation.verify(Path(report['allocation_result']).parent);balances=balance.verify(Path(allocations['balance_result']).parent);producer=verify_result(balances['producer_result'])
    request_path=Path(producer['request']['path']);request=read_json(request_path)
    if request['capability']!='spatial.ifc-room-recognition':raise ValueError('Original saved IFC recognition required;no replacement IFC')
    source=(request_path.parent/request['sources']['ifc']['path']).resolve()
    if not allowed(source) or digest(source)!=request['sources']['ifc']['sha256']:raise ValueError('Inherited IFC source differs')
    choices=read_json(basis);spaces={s['id']:s for s in producer['payload']['spaces']};rows=[]
    ids={t['id'] for room in allocations['calculation']['rooms'].values() for t in room['allocation']['terminals']}
    if not isinstance(choices,dict) or set(choices)!=ids:raise ValueError('Envelope basis must cover every allocated terminal exactly')
    for guid,room in allocations['calculation']['rooms'].items():
        space=spaces[guid];boundary=Polygon(space['boundary_vertices'])
        for terminal in room['allocation']['terminals']:
            key=terminal['id'];choice=choices[key]
            if set(choice)!={'size_m','bottom_above_floor_m'}:raise ValueError('Exact envelope dimensions and bottom elevation basis required')
            for name,record in choice.items():
                if not isinstance(record,dict) or set(record)!={'value','unit','source','classification'} or record['unit']!='m' or not isinstance(record['source'],str) or not record['source'].strip() or record['classification'] not in ('given','measured','assumed','secondary_transcription','design_choice'):raise ValueError('Source-classified metre envelope basis required')
            size=choice['size_m']['value'];z=choice['bottom_above_floor_m']['value']
            if not isinstance(size,list) or len(size)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in size) or type(z) not in (int,float) or not math.isfinite(z) or z<0 or z+size[2]>space['height_m']:raise ValueError('Finite positive envelope within inherited room height required')
            x,y=terminal['center_m'];origin=[x-size[0]/2,y-size[1]/2,room['floor_elevation_m']+z]
            if not boundary.covers(box(origin[0],origin[1],origin[0]+size[0],origin[1]+size[1])):raise ValueError('Terminal envelope extends outside original room polygon')
            product=report['calculation']['terminals'][key]
            rows.append(dict(id=key,space_guid=guid,origin_m=origin,size_m=size,maximum_flow_L_s=terminal['maximum_flow_L_s'],minimum_flow_L_s=terminal['minimum_flow_L_s'],basis=choice,product=product['product']))
    pins=dict(report['inputs']);pins[str(path)]=digest(path);pins[str(basis)]=digest(basis)
    for module in (performance,allocation,balance,box_geometry):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    if importlib.metadata.version('ifcopenshell')!='0.8.5':raise ValueError('Pinned IfcOpenShell0.8.5 required')
    return source,rows,pins


def inspect(source,target,rows):
    original=ifcopenshell.open(str(source));model=ifcopenshell.open(str(target))
    for entity in original:
        if model.by_id(entity.id()).to_string()!=entity.to_string():raise ValueError('Original IFC entity changed')
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(model,logger,express_rules=True)
    if logger.statements:raise ValueError('Saved IFC schema/EXPRESS validation failed')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);records=[]
    for row in rows:
        matches=[o for o in model.by_type('IfcAirTerminal') if o.Tag=='BSA_SPATIAL:'+row['id']]
        if len(matches)!=1:raise ValueError('Exact saved terminal identity required')
        obj=matches[0]
        expected_guid=ifcopenshell.guid.compress(uuid.uuid5(uuid.uuid5(uuid.NAMESPACE_URL,digest(source)),'terminal:'+row['id']).hex)
        if obj.GlobalId!=expected_guid or obj.PredefinedType!='NOTDEFINED' or obj.HasPorts:raise ValueError('Terminal stable identity/type or unsupported ports differ')
        shape=ifcopenshell.geom.create_shape(settings,obj);vertices=np.array(shape.geometry.verts).reshape(-1,3);faces=np.array(shape.geometry.faces).reshape(-1,3)
        lo,size,volume=box_geometry.box_mesh(vertices,faces)
        if not np.allclose(lo,row['origin_m'],atol=1e-7,rtol=0) or not np.allclose(size,row['size_m'],atol=1e-7,rtol=0):raise ValueError('Saved terminal geometry differs')
        container=element.get_container(obj)
        if container is None or container.GlobalId!=row['space_guid']:raise ValueError('Saved terminal space differs')
        props=element.get_psets(obj)['BSA_SpatialTerminal']
        expected=dict(InputID=row['id'],MaximumFlow_L_s=row['maximum_flow_L_s'],MinimumFlow_L_s=row['minimum_flow_L_s'],GeometryScope='source-classified bounding envelope only',BasisJSON=json.dumps(row['basis'],sort_keys=True),ProductJSON=json.dumps(row['product'],sort_keys=True))
        if any(props.get(k)!=v for k,v in expected.items()):raise ValueError('Saved terminal source/flow properties differ')
        records.append(dict(id=row['id'],guid=obj.GlobalId,space_guid=container.GlobalId,volume_m3=volume))
    if len([o for o in model.by_type('IfcAirTerminal') if (o.Tag or '').startswith('BSA_SPATIAL:')])!=len(rows):raise ValueError('Extra saved terminal envelopes')
    return records


def run(path,basis,out):
    path,basis,out=[Path(p).resolve() for p in (path,basis,out)]
    if not all(allowed(p) for p in (path,basis,out)) or out.exists():raise ValueError('Selected sources and new IFC output required')
    source,rows,pins=prepare(path,basis)
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('IFC output overlaps source')
    model=ifcopenshell.open(str(source));body=next(c for c in model.by_type('IfcGeometricRepresentationSubContext') if c.ContextIdentifier=='Body')
    namespace=uuid.uuid5(uuid.NAMESPACE_URL,digest(source))
    for row in rows:
        guid=ifcopenshell.guid.compress(uuid.uuid5(namespace,'terminal:'+row['id']).hex)
        if any(o.GlobalId==guid for o in model.by_type('IfcRoot')):raise ValueError('Terminal GUID collision')
        obj=model.create_entity('IfcAirTerminal',GlobalId=guid,Name=row['id'],Tag='BSA_SPATIAL:'+row['id'],PredefinedType='NOTDEFINED')
        w,d,h=row['size_m'];vertices=[(0,0,0),(w,0,0),(w,d,0),(0,d,0),(0,0,h),(w,0,h),(w,d,h),(0,d,h)];faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        rep=api.run('geometry.add_mesh_representation',model,context=body,vertices=[vertices],faces=[faces]);api.run('geometry.assign_representation',model,product=obj,representation=rep)
        matrix=np.eye(4);matrix[:3,3]=row['origin_m'];api.run('geometry.edit_object_placement',model,product=obj,matrix=matrix,is_si=True)
        model.create_entity('IfcRelContainedInSpatialStructure',GlobalId=ifcopenshell.guid.compress(uuid.uuid5(namespace,'containment:'+row['id']).hex),RelatedElements=[obj],RelatingStructure=model.by_guid(row['space_guid']))
        pset=api.run('pset.add_pset',model,product=obj,name='BSA_SpatialTerminal');api.run('pset.edit_pset',model,pset=pset,properties=dict(InputID=row['id'],MaximumFlow_L_s=row['maximum_flow_L_s'],MinimumFlow_L_s=row['minimum_flow_L_s'],GeometryScope='source-classified bounding envelope only',BasisJSON=json.dumps(row['basis'],sort_keys=True),ProductJSON=json.dumps(row['product'],sort_keys=True)))
    out.mkdir(parents=True);target=out/'Terminal Envelope Study.ifc';model.write(str(target));records=inspect(source,target,rows)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('IFC source/method changed')
    result=dict(performance=str(path),basis=str(basis),source_ifc=str(source),inputs=pins,ifc_sha256=digest(target),terminals=records,original_entities_unchanged=True,design_accepted=False,pending=['manufacturer shape fidelity','ports/system connectivity','physical clashes and installation','visual BIM review','ADPI and complete engineering acceptance'])
    (out/'terminal-ifc.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected IFC workspace required')
    result=read_json(folder/'terminal-ifc.json')
    if set(result)!={'performance','basis','source_ifc','inputs','ifc_sha256','terminals','original_entities_unchanged','design_accepted','pending'}:raise ValueError('Exact terminal IFC report required')
    path=Path(result['performance']);basis=Path(result['basis'])
    if not all(allowed(p) for p in (path,basis)) or result.get('design_accepted') is not False:raise ValueError('Selected unaccepted IFC source required')
    source,rows,pins=prepare(path,basis);target=folder/'Terminal Envelope Study.ifc'
    if result['inputs']!=pins or result['source_ifc']!=str(source) or result['ifc_sha256']!=digest(target) or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Terminal IFC source/output pins differ')
    if inspect(source,target,rows)!=result['terminals'] or result['original_entities_unchanged'] is not True:raise ValueError('Terminal IFC native replay differs')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('performance');parser.add_argument('--basis',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.performance,args.basis,args.out)
