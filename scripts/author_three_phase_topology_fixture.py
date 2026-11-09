"""Add explicitly synthetic ideal-node boards through pinned upstream IFC APIs."""
import argparse
import json
from pathlib import Path
import shutil
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.validate
from ifcopenshell.util.shape_builder import ShapeBuilder
import numpy as np
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase import prepare,fields,ROOT
from bsa.three_phase_ifc import inspect
from bsa.three_phase_topology import inspect as inspect_topology
from bsa.tee_geometry import stable_guid


def run(project,ifc,binding,basis,out):
    project,ifc,binding,basis,out=[Path(v).resolve() for v in (project,ifc,binding,basis,out)]
    checked=inspect(project,ifc,binding);p,_=prepare(project)
    if checked['ifc_unit_to_m']!=1:raise ProjectError('synthetic fixture author requires metre IFC units')
    data=json.loads(basis.read_text(encoding='utf-8-sig'))
    fields(data,'scope project_uuid board_envelope_size_m internal_bus_model')
    if not isinstance(data['scope'],str) or not data['scope'].startswith('Synthetic') or data['internal_bus_model']!='ideal common electrical node':raise ProjectError('explicit synthetic common-node fixture required')
    size=np.array(data['board_envelope_size_m'],dtype=float)
    if size.shape!=(3,) or not np.isfinite(size).all() or np.any(size<=0):raise ProjectError('positive explicit board envelope dimensions required')
    before={**checked['inputs'],str(basis):digest(basis),str(Path(__file__).resolve()):digest(Path(__file__))}
    if not out.is_relative_to(ROOT) or out.exists() or any(out==Path(f) or out in Path(f).parents for f in before):raise ProjectError('new separate repository fixture output required')
    b=json.loads(binding.read_text(encoding='utf-8-sig'));model=ifcopenshell.open(str(ifc))
    selected=model.by_guid(b['system_guid']);storeys=model.by_type('IfcBuildingStorey')
    contexts=[c for c in model.by_type('IfcGeometricRepresentationSubContext') if c.ContextIdentifier=='Body']
    if len(storeys)!=1 or len(contexts)!=1:raise ProjectError('fixture requires one storey and Body context')
    builder=ShapeBuilder(model);buses={}
    for bus in p['buses']:
        name=bus['id'];anchor=np.array(b['buses'][name],dtype=float)
        board=api.run('root.create_entity',model,ifc_class='IfcElectricDistributionBoard',predefined_type='DISTRIBUTIONBOARD',name='Synthetic ideal bus '+name)
        board.GlobalId=stable_guid(data,'IfcElectricDistributionBoard',name);board.Tag=name
        api.run('spatial.assign_container',model,products=[board],relating_structure=storeys[0])
        api.run('system.assign_system',model,products=[board],system=selected)
        frame=np.eye(4);frame[:3,3]=anchor-size/2
        api.run('geometry.edit_object_placement',model,product=board,matrix=frame,is_si=True)
        solid=builder.block(x_length=float(size[0]),y_length=float(size[1]),z_length=float(size[2]))
        api.run('geometry.assign_representation',model,product=board,representation=builder.get_representation(contexts[0],solid))
        ps=api.run('pset.add_pset',model,product=board,name='BSA_DesignInputs')
        api.run('pset.edit_pset',model,pset=ps,properties=dict(GeometryScope=data['scope'],InternalBusModel=data['internal_bus_model'],SourceSHA256=before[str(basis)]))
        ports={}
        for line in p['lines']:
            if name not in (line['from'],line['to']):continue
            port=api.run('system.add_port',model,element=board)
            port.GlobalId=stable_guid(data,'IfcDistributionPort','board',name,line['id']);port.Name=line['id']
            port.PredefinedType='CABLE';port.SystemType='ELECTRICAL';port.FlowDirection='SOURCEANDSINK'
            frame=np.eye(4);frame[:3,3]=anchor
            api.run('geometry.edit_object_placement',model,product=port,matrix=frame,is_si=True)
            cable=model.by_guid(b['lines'][line['id']]['from_port_guid' if line['from']==name else 'to_port_guid'])
            api.run('system.connect_port',model,port1=cable,port2=port,direction='SOURCEANDSINK')
            ports[line['id']]=port.GlobalId
        buses[name]=dict(element_guid=board.GlobalId,ports=ports)
    out.mkdir(parents=True);saved=out/'connected-cables.ifc';model.write(str(saved))
    logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(ifcopenshell.open(str(saved)),logger)
    if logger.statements:raise ProjectError('connected fixture schema validation failed: '+str(logger.statements[:2]))
    shutil.copyfile(binding.parent/b['source']['path'],out/'geometry-source.json')
    b['source']['path']='geometry-source.json';b['ifc_sha256']=digest(saved)
    (out/'binding.json').write_text(json.dumps(b,indent=2),encoding='utf-8')
    shutil.copyfile(basis,out/'topology-source.json')
    t=dict(version=1,ifc_sha256=digest(saved),internal_bus_model=data['internal_bus_model'],
           source=dict(path='topology-source.json',sha256=before[str(basis)],kind='assumption',locator='Synthetic common-node board envelopes and ideal bus model'),buses=buses)
    (out/'topology-binding.json').write_text(json.dumps(t,indent=2),encoding='utf-8')
    result=inspect_topology(project,saved,out/'binding.json',out/'topology-binding.json')
    if any(digest(Path(f))!=sha for f,sha in before.items()):raise ProjectError('fixture source changed')
    (out/'authoring.json').write_text(json.dumps(dict(original_inputs=before,schema_checks_pass=True,logical_graph_correspondence_pass=result['logical_graph_correspondence_pass'],design_accepted=False),indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path)
    for name in ('ifc','binding','basis','out'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();r=run(a.project,a.ifc,a.binding,a.basis,a.out)
    print(json.dumps({k:r[k] for k in ('logical_graph_correspondence_pass','bus_count','cable_count','directed_relationship_count','design_accepted')}))
