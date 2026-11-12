"""Author explicit straight hollow inlet stubs using existing circular-wall geometry."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.validate
import ifcopenshell.util.element as element
import ifcopenshell.util.system as system
import ifcopenshell.util.placement as placement
import ifcopenshell.util.unit as unit
from .cli import digest
from .module_contract import read_json
from .workspace import allowed
from . import spatial_terminal_inlets as inlets,circular_geometry as circular


def prepare(source,basis):
    before=digest(source);report=inlets.verify(source.parent)
    if source.name!='terminal-inlets.json':raise ValueError('Exact verified inlet report required')
    target=source.parent/'Terminal Inlet Study.ifc';model=ifcopenshell.open(str(target))
    if not math.isclose(unit.calculate_unit_scale(model),1,rel_tol=0,abs_tol=1e-12):raise ValueError('Existing circular authoring requires a metre-unit source')
    bases=read_json(basis);records={r['terminal']:r for r in report['inlets']}
    if not isinstance(bases,dict) or set(bases)!=set(records):raise ValueError('Complete explicit inlet-stub basis required')
    rows=[]
    for name,record in records.items():
        basis_row=bases[name]
        if not isinstance(basis_row,dict) or set(basis_row)!={'length_m','internal_diameter_m','wall_thickness_m'}:raise ValueError('Explicit stub length,bore and wall basis required;no route override')
        values={}
        for key,row in basis_row.items():
            if not isinstance(row,dict) or set(row)!={'value','unit','source','classification'} or row['unit']!='m' or not isinstance(row['source'],str) or not row['source'].strip() or row['classification'] not in ('given','measured','assumed','secondary_transcription','design_choice'):raise ValueError('Source-classified metre stub dimensions required')
            value=row['value']
            if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError('Positive finite stub dimensions required')
            values[key]=value
        if not math.isclose(values['internal_diameter_m'],record['diameter_m'],rel_tol=0,abs_tol=1e-8):raise ValueError('Direct stub bore must match nominal inlet;physical bore applicability remains unverified')
        port=model.by_guid(record['port_guid']);matrix=placement.get_local_placement(port.ObjectPlacement);start=matrix[:3,3];normal=matrix[:3,2]
        axis=int(np.argmax(abs(normal)))
        if not np.allclose(abs(normal),np.eye(3)[axis],atol=1e-8,rtol=0) or port.FlowDirection!='SINK' or port.ConnectedTo or port.ConnectedFrom:raise ValueError('Unconnected cardinal SINK inlet required')
        end=start+normal*values['length_m'];outer=values['internal_diameter_m']+2*values['wall_thickness_m'];origin=start.copy()-outer/2;origin[axis]=min(start[axis],end[axis]);size=[outer]*3;size[axis]=values['length_m']
        near=[outer/2]*3;far=[outer/2]*3;near[axis]=0 if normal[axis]>0 else values['length_m'];far[axis]=values['length_m']-near[axis]
        device=dict(ifc_class='IfcDuctSegment',origin_m=origin.tolist(),size_m=size,properties=dict(InternalDiameter_m=values['internal_diameter_m'],OutsideDiameter_m=outer),ports=[dict(id='terminal',direction='SOURCE',offset_m=near),dict(id='upstream',direction='SINK',offset_m=far)])
        circular.specification(device)
        terminal=model.by_guid(record['terminal_guid']);container=element.get_container(terminal);flow=element.get_psets(terminal)['BSA_SpatialTerminal']
        rows.append(dict(id=name,terminal_guid=terminal.GlobalId,inlet_guid=port.GlobalId,system_guid=record['system_guid'],system_type=port.SystemType,space_guid=container.GlobalId,device=device,basis=basis_row,maximum_flow_L_s=flow['MaximumFlow_L_s'],minimum_flow_L_s=flow['MinimumFlow_L_s']))
    pins=dict(report['inputs']);pins[str(source)]=before;pins[str(target)]=report['ifc_sha256'];pins[str(basis)]=digest(basis)
    for module in (inlets,circular):pins[str(Path(module.__file__).resolve())]=digest(Path(module.__file__))
    pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    if digest(source)!=before:raise ValueError('Inlet producer changed')
    return target,rows,pins


def inspect(source,target,rows):
    original=ifcopenshell.open(str(source));model=ifcopenshell.open(str(target))
    for obj in original:
        if model.by_id(obj.id()).to_string()!=obj.to_string():raise ValueError('Original inlet/model entity changed')
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(model,logger,express_rules=True)
    if logger.statements:raise ValueError('Stub IFC schema/EXPRESS validation failed')
    if len(model.by_type('IfcDuctSegment'))!=len(original.by_type('IfcDuctSegment'))+len(rows) or len(model.by_type('IfcDistributionPort'))!=len(original.by_type('IfcDistributionPort'))+2*len(rows):raise ValueError('Unexpected stub/port coverage')
    if len(model.by_type('IfcElement'))!=len(original.by_type('IfcElement'))+len(rows) or len(model.by_type('IfcDistributionSystem'))!=len(original.by_type('IfcDistributionSystem')):raise ValueError('Unexpected added physical elements or systems')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);circular.configure(settings);records=[];expected_links=set()
    for row in rows:
        obj=model.by_guid(inlets.stable(source,'stub',row['id']));shape=ifcopenshell.geom.create_shape(settings,obj);geometry=circular.verify(obj,row['device'],shape)
        vertices=np.array(shape.geometry.verts).reshape(-1,3);origin=np.array(row['device']['origin_m']);end=origin+row['device']['size_m']
        if not np.allclose(vertices.min(axis=0),origin,atol=circular.BOUNDS_TOLERANCE_M,rtol=0) or not np.allclose(vertices.max(axis=0),end,atol=circular.BOUNDS_TOLERANCE_M,rtol=0):raise ValueError('Saved stub body bounds differ from inlet-derived stations')
        if not obj.is_a('IfcDuctSegment') or obj.PredefinedType!='RIGIDSEGMENT' or element.get_container(obj).GlobalId!=row['space_guid'] or {s.GlobalId for s in system.get_element_systems(obj)}!={row['system_guid']}:raise ValueError('Saved stub space/system differs')
        props=element.get_psets(obj)['BSA_DesignInputs']
        if props.get('StubBasisJSON')!=json.dumps(row['basis'],sort_keys=True) or props.get('MaximumFlow_L_s')!=row['maximum_flow_L_s'] or props.get('MinimumFlow_L_s')!=row['minimum_flow_L_s'] or props.get('InputPortGUID')!=row['inlet_guid']:raise ValueError('Saved stub source/flow properties differ')
        ports=system.get_ports(obj)
        if len(ports)!=2:raise ValueError('Exactly two saved stub ports required')
        for declared in row['device']['ports']:
            guid=inlets.stable(source,'stub-'+declared['id'],row['id']);port=model.by_guid(guid)
            if port not in ports or port.FlowDirection!=declared['direction'] or port.PredefinedType!='DUCT' or port.SystemType!=row['system_type']:raise ValueError('Saved stub port identity/direction/type differs')
            matrix=placement.get_local_placement(port.ObjectPlacement);point=np.array(row['device']['origin_m'])+declared['offset_m'];normal=circular.specification(row['device'])['normals'][declared['id']]
            if not np.allclose(matrix[:3,3],point,atol=1e-8,rtol=0) or not np.allclose(matrix[:3,2],normal,atol=1e-8,rtol=0):raise ValueError('Saved stub port point/axis differs')
            if declared['id']=='terminal':
                expected_links.add((port.GlobalId,row['inlet_guid']));inlet=model.by_guid(row['inlet_guid']);im=placement.get_local_placement(inlet.ObjectPlacement)
                if not np.allclose(im[:3,3],matrix[:3,3],atol=1e-8,rtol=0) or not np.allclose(im[:3,2],-matrix[:3,2],atol=1e-8,rtol=0):raise ValueError('Stub/inlet faces do not coincide and oppose')
            elif port.ConnectedTo or port.ConnectedFrom:raise ValueError('Upstream stub boundary must remain explicitly open')
        records.append(dict(terminal=row['id'],stub_guid=obj.GlobalId,inlet_guid=row['inlet_guid'],geometry=geometry,maximum_flow_L_s=row['maximum_flow_L_s'],minimum_flow_L_s=row['minimum_flow_L_s']))
    links=lambda f:{(r.RelatingPort.GlobalId,r.RelatedPort.GlobalId) for r in f.by_type('IfcRelConnectsPorts')}
    if links(model)!=links(original)|expected_links or len(model.by_type('IfcRelConnectsPorts'))!=len(original.by_type('IfcRelConnectsPorts'))+len(rows):raise ValueError('Saved directed stub/inlet links differ')
    return records


def run(source,basis,out):
    source,basis,out=[Path(p).resolve() for p in (source,basis,out)]
    if not all(allowed(p) for p in (source,basis,out)) or out.exists():raise ValueError('Selected inlet source,basis and fresh output required')
    target,rows,pins=prepare(source,basis)
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Stub output overlaps source inputs')
    model=ifcopenshell.open(str(target));body=next(c for c in model.by_type('IfcGeometricRepresentationSubContext') if c.ContextIdentifier=='Body')
    guids=[inlets.stable(target,role,row['id']) for row in rows for role in ('stub','stub-terminal','stub-upstream')]
    if set(guids)&{obj.GlobalId for obj in model.by_type('IfcRoot')}:raise ValueError('Stub GUID collision')
    for row in rows:
        obj=model.create_entity('IfcDuctSegment',GlobalId=inlets.stable(target,'stub',row['id']),Name=row['id']+'_stub',PredefinedType='RIGIDSEGMENT');circular.author(model,body,obj,row['device'])
        model.create_entity('IfcRelContainedInSpatialStructure',GlobalId=ifcopenshell.guid.new(),RelatedElements=[obj],RelatingStructure=model.by_guid(row['space_guid']))
        model.create_entity('IfcRelAssignsToGroup',GlobalId=ifcopenshell.guid.new(),RelatedObjects=[obj],RelatingGroup=model.by_guid(row['system_guid']))
        pset=api.run('pset.add_pset',model,product=obj,name='BSA_DesignInputs');api.run('pset.edit_pset',model,pset=pset,properties=dict(row['device']['properties'],StubBasisJSON=json.dumps(row['basis'],sort_keys=True),InputPortGUID=row['inlet_guid'],MaximumFlow_L_s=row['maximum_flow_L_s'],MinimumFlow_L_s=row['minimum_flow_L_s']))
        for declared in row['device']['ports']:
            port=api.run('system.add_port',model,element=obj);port.GlobalId=inlets.stable(target,'stub-'+declared['id'],row['id']);port.Name=declared['id'];port.FlowDirection=declared['direction'];port.PredefinedType='DUCT';port.SystemType=row['system_type']
            matrix=circular.frame(circular.specification(row['device'])['normals'][declared['id']]);matrix[:3,3]=np.array(row['device']['origin_m'])+declared['offset_m'];api.run('geometry.edit_object_placement',model,product=port,matrix=matrix,is_si=True)
            if declared['id']=='terminal':api.run('system.connect_port',model,port1=port,port2=model.by_guid(row['inlet_guid']),direction='SOURCE')
    out.mkdir(parents=True);output=out/'Terminal Stub Study.ifc';model.write(str(output));records=inspect(target,output,rows)
    inlets.verify(source.parent)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Stub source/method changed')
    result=dict(inlets=str(source),basis=str(basis),inputs=pins,ifc_sha256=digest(output),stubs=records,original_entities_unchanged=True,network_continuity_verified=False,design_accepted=False,
        scope='Explicit straight hollow short ducts and directed coincident inlet links only;upstream ends remain open. Terminal envelopes retain closed bodies,no physical neck/opening or whole-network airflow continuity is proven')
    (out/'terminal-stubs.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected stub workspace required')
    result=read_json(folder/'terminal-stubs.json')
    if set(result)!={'inlets','basis','inputs','ifc_sha256','stubs','original_entities_unchanged','network_continuity_verified','design_accepted','scope'} or result['design_accepted'] is not False or result['network_continuity_verified'] is not False:raise ValueError('Exact unaccepted stub report required')
    source=Path(result['inlets']);basis=Path(result['basis'])
    if not allowed(source) or not allowed(basis):raise ValueError('Selected original stub sources required')
    target,rows,pins=prepare(source,basis);output=folder/'Terminal Stub Study.ifc'
    if result['inputs']!=pins or result['ifc_sha256']!=digest(output) or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Stub source/output pins differ')
    if inspect(target,output,rows)!=result['stubs'] or result['original_entities_unchanged'] is not True:raise ValueError('Stub native replay differs')
    return result


def verify_workflow(tasks,root,plan_root,record):
    for task in tasks:
        if task['kind']!='spatial_terminal_stubs':continue
        folder=Path(root)/task['id']
        if not (folder/'terminal-stubs.json').is_file():
            if record[task['id']]['status']=='pass':raise ValueError('Passing stub task lacks report')
            continue
        report=verify(folder)
        if Path(report['inlets'])!=(Path(root)/task['depends_on']/'terminal-inlets.json').resolve() or Path(report['basis'])!=(Path(plan_root)/task['basis']).resolve():raise ValueError('Stub task replaced declared inlet/basis')
        if record[task['id']]['status']!='pass' or record[task['depends_on']]['status']!='pass':raise ValueError('Stub task execution dependency differs')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source');parser.add_argument('--basis',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();run(args.source,args.basis,args.out)
