"""Create an explicitly synthetic cable fixture with upstream IFC APIs.

This is a reproducible test author, not an installation-design generator.
"""
import argparse
import json
import math
from pathlib import Path
import shutil
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.validate
from ifcopenshell.util.shape_builder import ShapeBuilder
from bsa.cli import digest
from bsa.engine import ProjectError
from bsa.three_phase import prepare,ROOT
from bsa.tee_geometry import stable_guid


def run(project,geometry,out,body_kind='swept-disk'):
    if body_kind not in ('swept-disk','extrusion','mixed-revolution'):raise ProjectError('unsupported fixture body kind')
    project,geometry,out=[Path(v).resolve() for v in (project,geometry,out)]
    p,files=prepare(project);data=json.loads(geometry.read_text(encoding='utf-8-sig'))
    if not out.is_relative_to(ROOT) or out.exists() or any(out==f or out in f.parents for f in files|{geometry}):raise ProjectError('new separate repository fixture output required')
    expected={'scope','project_uuid','envelope_radius_m','buses_m'}|({'quarter_bends'} if body_kind=='mixed-revolution' else set())
    if set(data)!=expected or not isinstance(data['scope'],str) or not data['scope'].startswith('Synthetic'):raise ProjectError('explicit synthetic fixture scope required')
    radius=data['envelope_radius_m'];anchors=data['buses_m']
    if type(radius) not in (int,float) or not math.isfinite(radius) or radius<=0 or set(anchors)!={b['id'] for b in p['buses']}:raise ProjectError('positive radius and exact bus anchors required')
    for xyz in anchors.values():
        if not isinstance(xyz,list) or len(xyz)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in xyz):raise ProjectError('finite fixture anchors required')
    bends=data.get('quarter_bends',{});helpers=set()
    if not isinstance(bends,dict) or (body_kind=='mixed-revolution' and not bends) or not set(bends).issubset({line['id'] for line in p['lines']}):raise ProjectError('explicit nonempty known quarter-bend line map required')
    if bends:
        import bsa.quarter_cable as quarter
        helpers.add(Path(quarter.__file__).resolve())
    for line in p['lines']:
        if line['id'] in bends:
            bend_radius,_,axis_points=quarter.source_geometry(bends[line['id']],radius)
            if not np.allclose(axis_points[[0,-1]],[anchors[line['from']],anchors[line['to']]],atol=1e-8,rtol=0):raise ProjectError('quarter-bend source endpoints differ from bus anchors')
            length=bend_radius*math.pi/2
        else:length=math.dist(anchors[line['from']],anchors[line['to']])
        if not math.isclose(length,line['length_m'],abs_tol=1e-8,rel_tol=0):raise ProjectError('fixture coordinates do not match supplied route length')
    before={str(f):digest(f) for f in files|helpers|{geometry,Path(__file__).resolve()}}
    model=api.run('project.create_file',version='IFC4')
    def create(cls,name,**kwargs):
        obj=api.run('root.create_entity',model,ifc_class=cls,name=name,**kwargs);obj.GlobalId=stable_guid(data,cls,name);return obj
    pr=create('IfcProject','Synthetic cable geometry fixture')
    metre=api.run('unit.add_si_unit',model,unit_type='LENGTHUNIT')
    units=[metre]+([api.run('unit.add_si_unit',model,unit_type='PLANEANGLEUNIT')] if bends else [])
    api.run('unit.assign_unit',model,units=units)
    ctx=api.run('context.add_context',model,context_type='Model')
    body=api.run('context.add_context',model,context_type='Model',context_identifier='Body',target_view='MODEL_VIEW',parent=ctx)
    axis=api.run('context.add_context',model,context_type='Model',context_identifier='Axis',target_view='GRAPH_VIEW',parent=ctx)
    site=create('IfcSite','Fixture site');building=create('IfcBuilding','Fixture building');storey=create('IfcBuildingStorey','Fixture storey')
    for parent,child in ((pr,site),(site,building),(building,storey)):api.run('aggregate.assign_object',model,products=[child],relating_object=parent)
    system=create('IfcDistributionSystem','Synthetic electrical cable geometry',predefined_type='ELECTRICAL')
    builder=ShapeBuilder(model);roles={}
    for line in p['lines']:
        obj=create('IfcCableSegment',line['id'],predefined_type='CABLESEGMENT');obj.Tag=line['id']
        api.run('spatial.assign_container',model,products=[obj],relating_structure=storey)
        api.run('system.assign_system',model,products=[obj],system=system)
        api.run('geometry.edit_object_placement',model,product=obj,matrix=np.eye(4),is_si=True)
        points=[[float(v) for v in anchors[id]] for id in (line['from'],line['to'])]
        curve=builder.polyline(points);directrix=builder.polyline(points)
        if line['id'] in bends:
            solid,curve=quarter.author(model,builder,bends[line['id']],radius)
        elif body_kind=='swept-disk':
            solid=builder.create_swept_disk_solid(directrix,radius)
        else:
            direction=np.array(points[1])-points[0];length=float(np.linalg.norm(direction));direction/=length
            reference=np.array([1.,0.,0.]) if abs(direction[0])<.9 else np.array([0.,1.,0.])
            x=reference-direction*np.dot(reference,direction);x/=np.linalg.norm(x)
            profile=model.create_entity('IfcCircleProfileDef',ProfileType='AREA',Radius=float(radius))
            solid=builder.extrude(profile,magnitude=length,position=points[0],position_z_axis=direction,position_x_axis=x)
        api.run('geometry.assign_representation',model,product=obj,representation=builder.get_representation(body,solid))
        api.run('geometry.assign_representation',model,product=obj,representation=builder.get_representation(axis,curve,representation_type='Curve3D'))
        ps=api.run('pset.add_pset',model,product=obj,name='BSA_DesignInputs')
        api.run('pset.edit_pset',model,pset=ps,properties=dict(SourceSHA256=before[str(geometry)],GeometryScope=data['scope'],InputID=line['id']))
        ports=[]
        for port_index,(name,point) in enumerate(zip(('from','to'),points)):
            port=api.run('system.add_port',model,element=obj);port.Name=name;port.GlobalId=stable_guid(data,'IfcDistributionPort',line['id'],name)
            port.FlowDirection='SOURCEANDSINK';port.PredefinedType='CABLE';port.SystemType='ELECTRICAL'
            matrix=quarter.port_frames(bends[line['id']],radius)[port_index] if line['id'] in bends else np.eye(4)
            matrix[:3,3]=point;api.run('geometry.edit_object_placement',model,product=port,matrix=matrix,is_si=True);ports.append(port)
        roles[line['id']]=dict(element_guid=obj.GlobalId,from_port_guid=ports[0].GlobalId,to_port_guid=ports[1].GlobalId)
    out.mkdir(parents=True);ifc=out/'cables.ifc';model.write(str(ifc))
    reopened=ifcopenshell.open(str(ifc));logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(reopened,logger)
    if logger.statements:raise ProjectError('saved IFC schema validation issues: '+str(logger.statements[:2]))
    shutil.copyfile(geometry,out/'geometry-source.json')
    binding=dict(version=1,ifc_sha256=digest(ifc),project_guid=pr.GlobalId,system_guid=system.GlobalId,
        source=dict(path='geometry-source.json',sha256=before[str(geometry)],locator='Synthetic radius and bus coordinates; no real-world survey or equipment claim',kind='assumption'),
        buses=anchors,lines=roles)
    (out/'binding.json').write_text(json.dumps(binding,indent=2),encoding='utf-8')
    if any(digest(Path(f))!=h for f,h in before.items()):raise ProjectError('fixture inputs changed')
    (out/'authoring.json').write_text(json.dumps(dict(inputs=before,ifc_sha256=digest(ifc),schema_checks_pass=True,
        body_kind=body_kind,geometry_scope=data['scope'],native_electrical_connectivity_verified=False,design_accepted=False),indent=2),encoding='utf-8')
    return binding


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
    p.add_argument('--geometry',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--body-kind',choices=['swept-disk','extrusion','mixed-revolution'],default='swept-disk')
    a=p.parse_args();run(a.project,a.geometry,a.out,a.body_kind)
