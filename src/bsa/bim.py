"""Source-backed IFC4 MEP envelopes and explicit straight circular wall solids."""
import argparse
import json
import math
import uuid
from pathlib import Path
from .cli import digest
from .engine import ProjectError
from . import circular_geometry as circular
from . import circular_elbow as elbow
from . import rectangular_geometry as rectangular
from . import rectangular_elbow

CLASSES={'IfcLightFixture','IfcOutlet','IfcElectricDistributionBoard','IfcAirTerminal',
         'IfcFan','IfcPump','IfcPipeSegment','IfcDuctSegment','IfcSensor',
         'IfcUnitaryEquipment','IfcPipeFitting','IfcDuctFitting','IfcFireSuppressionTerminal','IfcSanitaryTerminal'}


def validate(p):
    if not isinstance(p,dict) or p.get('geometry_scope') not in ('axis-aligned bounding envelopes',circular.MIXED_SCOPE,elbow.SCOPE,rectangular.SCOPE,rectangular_elbow.SCOPE):
        raise ProjectError('explicit bounding-envelope geometry scope required')
    if not isinstance(p.get('name'),str) or not p['name'].strip():raise ProjectError('name required')
    if 'project_uuid' in p:
        try:
            if not isinstance(p['project_uuid'],str) or str(uuid.UUID(p['project_uuid']))!=p['project_uuid']:raise ValueError()
        except (ValueError,AttributeError):raise ProjectError('project_uuid must be a canonical project namespace UUID')
    sources=p.get('sources')
    if not isinstance(sources,dict) or not sources or any(not isinstance(v,str) or not v.strip() for v in sources.values()):
        raise ProjectError('source descriptions required')
    def sourced(row):
        if not isinstance(row,dict) or not isinstance(row.get('source'),str) or row['source'] not in sources:
            raise ProjectError('every space/system/device/port/connection needs a known source')
        properties=row.get('properties',{})
        if not isinstance(properties,dict):raise ProjectError('additional properties must be a dictionary')
        for key,value in properties.items():
            if not isinstance(key,str) or not key or key in ('Source','InputID','GeometryScope','BodyShape','ElectricalInput_kW'):
                raise ProjectError('invalid or reserved property name')
            if type(value) not in (str,int,float,bool) or (type(value) in (int,float) and not math.isfinite(value)):
                raise ProjectError('properties must be finite scalar values')
    def vector(row,key,positive=False):
        v=row.get(key)
        if not isinstance(v,list) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or (positive and x<=0) for x in v):
            raise ProjectError(f'{key}: three finite SI coordinates/dimensions required')
    def collection(key):
        rows=p.get(key)
        if not isinstance(rows,list) or not rows:raise ProjectError(f'nonempty {key} required')
        ids=set()
        for r in rows:
            sourced(r)
            if not isinstance(r.get('id'),str) or not r['id'].strip() or r['id'] in ids:
                raise ProjectError(f'unique {key} IDs required')
            ids.add(r['id'])
        return {r['id']:r for r in rows}
    spaces,systems,devices=(collection(k) for k in ('spaces','systems','devices'))
    for row in spaces.values():vector(row,'origin_m');vector(row,'size_m',True)
    for row in systems.values():
        if row.get('predefined_type') not in ('ELECTRICAL','LIGHTING','VENTILATION','AIRCONDITIONING','CHILLEDWATER','CONDENSERWATER','HEATING','DOMESTICCOLDWATER','DOMESTICHOTWATER','DRAINAGE','FIREPROTECTION'):
            raise ProjectError('unsupported distribution system type')
    ports={}
    for d in devices.values():
        if not isinstance(d.get('ifc_class'),str) or d['ifc_class'] not in CLASSES:raise ProjectError('unsupported MEP device class')
        if not isinstance(d.get('space'),str) or not isinstance(d.get('system'),str) or d['space'] not in spaces or d['system'] not in systems:raise ProjectError('unknown space or system')
        if 'rotation' in d:raise ProjectError('rotation is not supported by this envelope adapter')
        vector(d,'origin_m');vector(d,'size_m',True)
        space=spaces[d['space']]
        for o,size,so,ss in zip(d['origin_m'],d['size_m'],space['origin_m'],space['size_m']):
            if o<so-1e-8 or o+size>so+ss+1e-8:raise ProjectError(f'device {d["id"]} lies outside its space')
        if 'electrical_kw' in d and (type(d['electrical_kw']) not in (int,float) or not math.isfinite(d['electrical_kw']) or d['electrical_kw']<0):
            raise ProjectError('electrical_kw must be finite and nonnegative')
        ps=d.get('ports',[])
        if not isinstance(ps,list):raise ProjectError('ports must be a list')
        for port in ps:
            sourced(port);vector(port,'offset_m')
            if not isinstance(port.get('id'),str) or not port['id'] or '.' in port['id']:raise ProjectError('port id required without dot')
            key=d['id']+'.'+port['id']
            if key in ports or port.get('direction') not in ('SOURCE','SINK','SOURCEANDSINK'):raise ProjectError('unique directed or explicit bidirectional ports required')
            ports[key]=(d,port)
        shape=d.get('body_shape','bounding envelope')
        if shape not in ('bounding envelope',circular.WALL,elbow.WALL,rectangular.WALL,rectangular_elbow.WALL):raise ProjectError('unsupported explicit body_shape')
        if shape==rectangular_elbow.WALL:
            if p['geometry_scope']!=rectangular_elbow.SCOPE:raise ProjectError('rectangular bends require explicit geometry scope')
            rectangular_elbow.specification(d)
        if shape==rectangular.WALL:
            if p['geometry_scope'] not in (rectangular.SCOPE,rectangular_elbow.SCOPE):raise ProjectError('rectangular walls require explicit geometry scope')
            rectangular.specification(d)
        if shape==circular.WALL:
            if p['geometry_scope'] not in (circular.MIXED_SCOPE,elbow.SCOPE):raise ProjectError('circular bodies require explicit mixed geometry scope')
            circular.specification(d)
        if shape==elbow.WALL:
            if p['geometry_scope']!=elbow.SCOPE:raise ProjectError('elbows require explicit fitting geometry scope')
            elbow.specification(d)
    connections=p.get('connections',[])
    if not isinstance(connections,list):raise ProjectError('connections must be list')
    used=set()
    for c in connections:
        sourced(c)
        if not isinstance(c.get('from'),str) or not isinstance(c.get('to'),str) or c['from'] not in ports or c['to'] not in ports:raise ProjectError('unknown connection endpoint')
        a,ap=ports[c['from']];b,bp=ports[c['to']]
        if a['id']==b['id'] or a['system']!=b['system'] or (ap['direction'],bp['direction']) not in (('SOURCE','SINK'),('SOURCEANDSINK','SOURCEANDSINK')):
            raise ProjectError('connections require source-to-sink or two bidirectional ports between distinct devices in the same system')
        if c['from'] in used or c['to'] in used:raise ProjectError('port connected more than once')
        used.update((c['from'],c['to']))
    return p


def run(project,out):
    import ifcopenshell
    import ifcopenshell.api as api
    import ifcopenshell.geom
    import ifcopenshell.validate
    import ifcopenshell.util.element as element
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system_util
    import ifcopenshell.util.unit as unit_util
    import numpy as np
    project,out=project.resolve(),out.resolve()
    if out==project or out in project.parents:raise ProjectError('output must not contain input')
    before=digest(project);p=validate(json.loads(project.read_text(encoding='utf-8-sig')))
    out.mkdir(parents=True,exist_ok=False)
    model=api.run('project.create_file',version='IFC4')
    namespace=uuid.UUID(p['project_uuid']) if p.get('project_uuid') else None
    def stable_guid(cls,*keys):
        return ifcopenshell.guid.compress(uuid.uuid5(namespace,json.dumps([cls,*keys],ensure_ascii=False,separators=(',',':'))).hex)
    def create(cls,name,**kw):
        obj=api.run('root.create_entity',model,ifc_class=cls,name=name,**kw)
        if namespace:obj.GlobalId=stable_guid(cls,'Project' if cls=='IfcProject' else name)
        return obj
    pr=create('IfcProject',p['name'])
    unit=api.run('unit.add_si_unit',model,unit_type='LENGTHUNIT')
    units=[unit]
    if any(d.get('body_shape')==rectangular_elbow.WALL for d in p['devices']):units.append(api.run('unit.add_si_unit',model,unit_type='PLANEANGLEUNIT'))
    api.run('unit.assign_unit',model,units=units)
    context=api.run('context.add_context',model,context_type='Model')
    body=api.run('context.add_context',model,context_type='Model',context_identifier='Body',target_view='MODEL_VIEW',parent=context)
    site=create('IfcSite','Site');building=create('IfcBuilding','Building');storey=create('IfcBuildingStorey','Storey')
    for parent,child in ((pr,site),(site,building),(building,storey)):
        api.run('aggregate.assign_object',model,products=[child],relating_object=parent)
    def props(obj,values):
        ps=api.run('pset.add_pset',model,product=obj,name='BSA_DesignInputs')
        api.run('pset.edit_pset',model,pset=ps,properties=values)
    def box(obj,origin,size):
        w,d,h=size
        vertices=[(0.,0.,0.),(w,0.,0.),(w,d,0.),(0.,d,0.),(0.,0.,h),(w,0.,h),(w,d,h),(0.,d,h)]
        faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        rep=api.run('geometry.add_mesh_representation',model,context=body,vertices=[vertices],faces=[faces])
        api.run('geometry.assign_representation',model,product=obj,representation=rep)
        matrix=np.eye(4);matrix[:3,3]=origin
        api.run('geometry.edit_object_placement',model,product=obj,matrix=matrix,is_si=True)
    spaces={};systems={};devices={};ports={}
    for s in p['spaces']:
        obj=create('IfcSpace',s['id']);spaces[s['id']]=obj
        api.run('aggregate.assign_object',model,products=[obj],relating_object=storey)
        box(obj,s['origin_m'],s['size_m'])
        props(obj,dict(Source=p['sources'][s['source']],GeometryScope=p['geometry_scope']))
    for s in p['systems']:
        obj=create('IfcDistributionSystem',s['id'],predefined_type=s['predefined_type']);systems[s['id']]=obj
        props(obj,dict(Source=p['sources'][s['source']],**s.get('properties',{})))
    for d in p['devices']:
        obj=create(d['ifc_class'],d['id']);obj.Tag=d['id'];devices[d['id']]=obj
        api.run('spatial.assign_container',model,products=[obj],relating_structure=spaces[d['space']])
        api.run('system.assign_system',model,products=[obj],system=systems[d['system']])
        if d.get('body_shape')==rectangular_elbow.WALL:rectangular_elbow.author(model,body,obj,d)
        elif d.get('body_shape')==rectangular.WALL:rectangular.author(model,body,obj,d)
        elif d.get('body_shape')==circular.WALL:circular.author(model,body,obj,d)
        elif d.get('body_shape')==elbow.WALL:elbow.author(model,body,obj,d)
        else:box(obj,d['origin_m'],d['size_m'])
        values=dict(Source=p['sources'][d['source']],GeometryScope=p['geometry_scope'],InputID=d['id'],BodyShape=d.get('body_shape','bounding envelope'))
        values.update(d.get('properties',{}))
        if 'electrical_kw' in d:values['ElectricalInput_kW']=float(d['electrical_kw'])
        props(obj,values)
        for port in d.get('ports',[]):
            objport=api.run('system.add_port',model,element=obj)
            objport.Name=port['id'];objport.FlowDirection=port['direction']
            if namespace:objport.GlobalId=stable_guid('IfcDistributionPort',d['id'],port['id'])
            module=rectangular_elbow if d.get('body_shape')==rectangular_elbow.WALL else rectangular if d.get('body_shape')==rectangular.WALL else elbow if d.get('body_shape')==elbow.WALL else circular
            matrix=circular.frame(module.specification(d)['normals'][port['id']]) if d.get('body_shape') in (circular.WALL,elbow.WALL,rectangular.WALL,rectangular_elbow.WALL) else np.eye(4)
            matrix[:3,3]=np.array(d['origin_m'])+np.array(port['offset_m'])
            api.run('geometry.edit_object_placement',model,product=objport,matrix=matrix,is_si=True)
            props(objport,dict(Source=p['sources'][port['source']]))
            ports[d['id']+'.'+port['id']]=objport
    for c in p.get('connections',[]):
        direction='SOURCEANDSINK' if ports[c['from']].FlowDirection=='SOURCEANDSINK' else 'SOURCE'
        api.run('system.connect_port',model,port1=ports[c['from']],port2=ports[c['to']],direction=direction)
        for port,other in ((ports[c['from']],ports[c['to']]),(ports[c['to']],ports[c['from']])):
            for relation in port.ConnectedTo:
                if relation.RelatedPort==other:relation.Description=p['sources'][c['source']]
    path=out/'model.ifc';model.write(str(path))
    reopened=ifcopenshell.open(path)
    logger=ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(reopened,logger,express_rules=True)
    (out/'schema-validation.json').write_text(json.dumps(logger.statements,default=str,indent=2),encoding='utf-8')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
    circular.configure(settings)
    records=[];native_ports={}
    for d in p['devices']:
        matches=[x for x in reopened.by_type(d['ifc_class']) if x.Name==d['id']]
        if len(matches)!=1:raise ProjectError('IFC device identity mismatch')
        obj=matches[0]
        if namespace and obj.GlobalId!=stable_guid(d['ifc_class'],d['id']):raise ProjectError('IFC stable device identity mismatch')
        shape=ifcopenshell.geom.create_shape(settings,obj)
        verts=np.array(shape.geometry.verts).reshape(-1,3)
        bounds=np.array([verts.min(axis=0),verts.max(axis=0)])
        expected=np.array([d['origin_m'],np.array(d['origin_m'])+np.array(d['size_m'])])
        container=element.get_container(obj)
        groups={r.RelatingGroup.Name for r in obj.HasAssignments if r.is_a('IfcRelAssignsToGroup')}
        bounds_tolerance=circular.BOUNDS_TOLERANCE_M if d.get('body_shape') in (circular.WALL,elbow.WALL,rectangular.WALL,rectangular_elbow.WALL) else 1e-7
        if not np.allclose(bounds,expected,atol=bounds_tolerance,rtol=0) or container.Name!=d['space'] or groups!={d['system']}:
            raise ProjectError('IFC geometry/space/system mismatch')
        properties=element.get_psets(obj)['BSA_DesignInputs']
        if properties.get('Source')!=p['sources'][d['source']] or properties.get('InputID')!=d['id']:
            raise ProjectError('IFC provenance mismatch')
        if properties.get('BodyShape')!=d.get('body_shape','bounding envelope'):raise ProjectError('IFC body-shape metadata mismatch')
        rectangular_checks=rectangular_elbow.verify(obj,d,shape) if d.get('body_shape')==rectangular_elbow.WALL else rectangular.verify(obj,d,shape) if d.get('body_shape')==rectangular.WALL else None
        circular_checks=circular.verify(obj,d,shape) if d.get('body_shape')==circular.WALL else elbow.verify(obj,d,shape) if d.get('body_shape')==elbow.WALL else None
        if 'electrical_kw' in d and not math.isclose(properties.get('ElectricalInput_kW',-1),d['electrical_kw']):
            raise ProjectError('IFC electrical input mismatch')
        actual_ports=system_util.get_ports(obj)
        if len(actual_ports)!=len(d.get('ports',[])):raise ProjectError('IFC port count mismatch')
        for port in d.get('ports',[]):
            matches=[x for x in actual_ports if x.Name==port['id']]
            if len(matches)!=1:raise ProjectError('IFC port identity mismatch')
            native=matches[0];native_ports[d['id']+'.'+port['id']]=native
            if namespace and native.GlobalId!=stable_guid('IfcDistributionPort',d['id'],port['id']):raise ProjectError('IFC stable port identity mismatch')
            origin=placement.get_local_placement(native.ObjectPlacement)[:3,3]
            if native.FlowDirection!=port['direction'] or not np.allclose(origin,np.array(d['origin_m'])+port['offset_m'],atol=1e-7,rtol=0):
                raise ProjectError('IFC port direction/coordinate mismatch')
            module=rectangular_elbow if d.get('body_shape')==rectangular_elbow.WALL else rectangular if d.get('body_shape')==rectangular.WALL else elbow if d.get('body_shape')==elbow.WALL else circular
            if d.get('body_shape') in (circular.WALL,elbow.WALL,rectangular.WALL,rectangular_elbow.WALL) and not np.allclose(placement.get_local_placement(native.ObjectPlacement)[:3,2],module.specification(d)['normals'][port['id']],atol=1e-8,rtol=0):
                raise ProjectError('IFC circular port outward axis mismatch')
        if circular_checks:circular_checks['outward_port_axes_pass']=True
        if rectangular_checks:rectangular_checks['outward_port_axes_pass']=True
        records.append(dict(id=d['id'],ifc_class=obj.is_a(),global_id=obj.GlobalId,space=container.Name,
                            systems=sorted(groups),bounds_m=bounds.tolist(),body_shape=d.get('body_shape','bounding envelope'),circular_checks=circular_checks,rectangular_checks=rectangular_checks))
    expected_links={(c['from'],c['to']) for c in p.get('connections',[])}
    expected_links.update((c['to'],c['from']) for c in p.get('connections',[]) if ports[c['from']].FlowDirection=='SOURCEANDSINK')
    actual_links=set()
    for relation in reopened.by_type('IfcRelConnectsPorts'):
        a,b=relation.RelatingPort,relation.RelatedPort
        actual_links.add((system_util.get_port_element(a).Name+'.'+a.Name,
                          system_util.get_port_element(b).Name+'.'+b.Name))
    checks=dict(schema_valid=not logger.statements,device_count_match=len(reopened.by_type('IfcDistributionElement'))==len(p['devices']),
                connection_count_match=len(reopened.by_type('IfcRelConnectsPorts'))==len(expected_links),
                connection_endpoints_match=actual_links==expected_links,
                metre_units=math.isclose(unit_util.calculate_unit_scale(reopened),1),
                space_count_match=len(reopened.by_type('IfcSpace'))==len(p['spaces']),
                source_unchanged=digest(project)==before)
    result=dict(ifcopenshell_version=ifcopenshell.version,input_sha256=before,ifc_sha256=digest(path),
                checks=checks,devices=records,model_checks_pass=all(checks.values()),design_accepted=False,
                geometry_scope=p['geometry_scope'],pending=['visual BIM review','manufacturer shape fidelity','physical route/clash checks','domain performance and code acceptance'])
    result['connection_scope']='logical topology only; no physical route is inferred between separated ports'
    result['identity_scope']='stable namespace/class/input-ID object and port GUIDs' if namespace else 'generated GUIDs; no stable namespace supplied'
    result['project_uuid']=p.get('project_uuid')
    (out/'bim-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if not result['model_checks_pass']:raise ProjectError('IFC verification failed; inspect run evidence')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=run(a.project,a.out)
    print(json.dumps(dict(checks=r['checks'],output=str(a.out),design_accepted=False),indent=2))

if __name__=='__main__':main()
