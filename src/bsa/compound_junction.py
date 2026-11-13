"""Explicit tapered rectangular trunk with separated side takeoffs; native CSG QA."""
import argparse
from collections import Counter
import importlib.metadata
import json
import math
from pathlib import Path
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.validate
import ifcopenshell.util.placement as placement
import ifcopenshell.util.system as system
import ifcopenshell.util.element as element
from ifcopenshell.util.shape_builder import ShapeBuilder
import manifold3d as m
import numpy as np
from .tee_geometry import project_namespace,placement_matrix,stable_guid
from .solid_clash import from_mesh
from .cad_ifc import mesh_properties
from .cli import digest
from .workspace import allowed

KEY='COMPOUND-RECTANGULAR-JUNCTION'


def validate(data):
    fields={'project_uuid','source','classification','placement','wall_thickness_m','stations','branches','port_directions'}
    if not isinstance(data,dict) or set(data)!=fields:raise ValueError('Exact sourced compound junction fields required')
    project_namespace(data);placement_matrix(data)
    if not isinstance(data['source'],str) or not data['source'].strip() or data['classification'] not in ('given','assumed','secondary_transcription'):raise ValueError('Classified compound construction required')
    t=data['wall_thickness_m']
    if type(t) not in (int,float) or not math.isfinite(t) or t<=0:raise ValueError('Positive explicit wall offset required')
    stations=data['stations'];branches=data['branches']
    if not isinstance(stations,list) or not 2<=len(stations)<=20 or not isinstance(branches,list) or not 1<=len(branches)<=8:raise ValueError('Bounded explicit trunk stations and takeoffs required')
    for row in stations:
        if not isinstance(row,dict) or set(row)!={'y_m','width_m','height_m'} or any(type(v) not in (int,float) or not math.isfinite(v) for v in row.values()) or min(row['width_m'],row['height_m'])<=0:raise ValueError('Finite sourced station dimensions required')
    if any(b['y_m']-a['y_m']<=1e-8 for a,b in zip(stations,stations[1:])):raise ValueError('Strictly increasing trunk stations required')
    names=set()
    for b in branches:
        if not isinstance(b,dict) or set(b)!={'id','y_m','side','width_m','height_m','reach_m'} or not isinstance(b['id'],str) or not b['id'].strip() or b['id'] in names|{'lower','upper'} or type(b['side']) is not int or b['side'] not in (-1,1):raise ValueError('Unique explicit signed side takeoffs required')
        names.add(b['id'])
        if any(type(b[k]) not in (int,float) or not math.isfinite(b[k]) for k in ('y_m','width_m','height_m','reach_m')) or min(b[k] for k in ('width_m','height_m','reach_m'))<=0:raise ValueError('Positive finite takeoff dimensions required')
        if b['y_m']-b['width_m']/2-t<=stations[0]['y_m'] or b['y_m']+b['width_m']/2+t>=stations[-1]['y_m'] or b['reach_m']<=max(s['width_m']/2+t for s in stations):raise ValueError('Takeoffs must stay inside trunk caps and extend beyond trunk wall')
        # Keep this construction analytically bounded: side bores never exceed trunk height.
        if b['height_m']>min(s['height_m'] for s in stations):raise ValueError('Side takeoff height must not exceed trunk clear height')
    for a,b in __import__('itertools').combinations(branches,2):
        if a['side']==b['side'] and abs(a['y_m']-b['y_m'])<=(a['width_m']+b['width_m'])/2+2*t:raise ValueError('Same-side takeoffs must be separated including wall offsets')
    directions=data['port_directions']
    if not isinstance(directions,dict) or set(directions)!=names|{'lower','upper'} or set(directions.values())!={'SOURCE','SINK'} or sum(v=='SINK' for v in directions.values())!=1:raise ValueError('Explicit one-inlet split directions required')
    return stations,branches,t


def station_points(data,outer):
    stations,_,t=validate(data);offset=t if outer else 0
    return np.array([(x*(s['width_m']/2+offset),s['y_m'],z*(s['height_m']/2+offset)) for s in stations for x,z in [(-1,-1),(1,-1),(1,1),(-1,1)]])


def port_frames(data):
    stations,branches,t=validate(data);world=placement_matrix(data);frames={}
    definitions=[('lower',(0,stations[0]['y_m'],0),(0,-1,0),(1,0,0)),('upper',(0,stations[-1]['y_m'],0),(0,1,0),(1,0,0))]
    definitions += [(b['id'],(b['side']*b['reach_m'],b['y_m'],0),(b['side'],0,0),(0,1,0)) for b in branches]
    for name,point,normal,width in definitions:
        f=np.eye(4);f[:3,:3]=np.column_stack((width,np.cross(normal,width),normal));f[:3,3]=point;frames[name]=world@f
    return frames


def integral(data,outer):
    """Independent exact cubic quadrature of trunk/side-prism union moments."""
    stations,branches,t=validate(data);offset=t if outer else 0
    def integrate(fun,a,b):
        # Simpson is exact here: every piece has polynomial degree at most three.
        return (b-a)*(np.array(fun(a))+4*np.array(fun((a+b)/2))+np.array(fun(b)))/6
    result=np.zeros(4)  # volume, x first moment, y first moment, z first moment
    for a,b in zip(stations,stations[1:]):
        lo,hi=a['y_m'],b['y_m']
        def dims(y):
            f=(y-lo)/(hi-lo);return np.array([a['width_m'],a['height_m']])*(1-f)+np.array([b['width_m'],b['height_m']])*f+2*offset
        result+=integrate(lambda y: [np.prod(dims(y)),0,y*np.prod(dims(y)),0],lo,hi)
    for branch in branches:
        w=branch['width_m']+2*offset;h=branch['height_m']+2*offset;B=branch['reach_m'];side=branch['side'];centre=branch['y_m'];volume=w*h*B
        result+=np.array([volume,side*B/2*volume,centre*volume,0])
        # Opposite half-space branches have zero common volume. Same-side Y intervals are disjoint.
        for a,b in zip(stations,stations[1:]):
            lo=max(a['y_m'],centre-w/2);hi=min(b['y_m'],centre+w/2)
            if hi<=lo:continue
            def dims(y):
                f=(y-a['y_m'])/(b['y_m']-a['y_m']);return np.array([a['width_m'],a['height_m']])*(1-f)+np.array([b['width_m'],b['height_m']])*f+2*offset
            # Validation guarantees full side height and reach beyond the complete trunk width.
            def cut(y):
                width=dims(y)[0]/2;area=width*h;return [area,side*width/2*area,y*area,0]
            result-=integrate(cut,lo,hi)
    return result


def native_union(model,builder,data,outer):
    stations,branches,t=validate(data);points=station_points(data,outer);n=len(stations);faces=[[0,1,2,3],[4*n-1,4*n-2,4*n-3,4*n-4]]
    faces += [[4*s+i,4*(s+1)+i,4*(s+1)+(i+1)%4,4*s+(i+1)%4] for s in range(n-1) for i in range(4)]
    trunk=builder.faceted_brep(points.tolist(),faces);offset=t if outer else 0;operands=[]
    for b in branches:
        p=model.create_entity('IfcRectangleProfileDef',ProfileType='AREA',XDim=float(b['width_m']+2*offset),YDim=float(b['height_m']+2*offset))
        operands.append(builder.extrude(p,magnitude=b['reach_m'],position=(0.,b['y_m'],0.),position_z_axis=(float(b['side']),0.,0.),position_x_axis=(0.,1.,0.)))
    return api.run('geometry.add_boolean',model,first_item=trunk,second_items=operands,operator='UNION')[-1]


def inspect(path,data):
    stations,branches,t=validate(data);world=placement_matrix(data);file=ifcopenshell.open(str(path));logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(file,logger,express_rules=True)
    if logger.statements:raise ValueError('Compound schema/EXPRESS issues')
    objects=file.by_type('IfcDistributionElement')
    if len(objects)!=1 or objects[0].GlobalId!=stable_guid(data,'IfcDuctFitting',KEY):raise ValueError('One stable compound fitting required')
    obj=objects[0]
    if obj.PredefinedType!='JUNCTION' or not np.allclose(placement.get_local_placement(obj.ObjectPlacement),world,atol=1e-9,rtol=0):raise ValueError('Compound native type/world placement differs')
    props=element.get_psets(obj).get('BSA_DesignInputs',{})
    if props.get('Source')!=data['source'] or props.get('Classification')!=data['classification']:raise ValueError('Compound source/classification differs')
    reps=obj.Representation.Representations
    if len(reps)!=1 or reps[0].RepresentationType!='CSG' or len(reps[0].Items)!=1:raise ValueError('Compound single native CSG body required')
    wall=reps[0].Items[0]
    if not wall.is_a('IfcBooleanResult') or wall.Operator!='DIFFERENCE':raise ValueError('Compound outer-minus-inner construction required')
    for outer,union in [(True,wall.FirstOperand),(False,wall.SecondOperand)]:
        operands=[];cursor=union
        while cursor.is_a('IfcBooleanResult'):
            if cursor.Operator!='UNION':raise ValueError('Compound union operators differ')
            operands.append(cursor.SecondOperand);cursor=cursor.FirstOperand
        if not cursor.is_a('IfcFacetedBrep') or len(operands)!=len(branches):raise ValueError('Compound station trunk and exact branch coverage required')
        faces=cursor.Outer.CfsFaces;points=[]
        if len(faces)!=2+4*(len(stations)-1):raise ValueError('Compound trunk face coverage differs')
        for face in faces:
            if len(face.Bounds)!=1 or not face.Bounds[0].is_a('IfcFaceOuterBound') or face.Bounds[0].Orientation is not True:raise ValueError('Compound native face boundaries differ')
            coords=np.array([p.Coordinates for p in face.Bounds[0].Bound.Polygon]);points.extend(coords)
            if len(coords)!=4 or np.linalg.matrix_rank(coords-coords[0],tol=1e-10)!=2:raise ValueError('Compound faces must be planar quadrilaterals')
        expected=station_points(data,outer);actual=np.unique(points,axis=0)
        if len(actual)!=len(expected) or any(np.min(np.linalg.norm(actual-p,axis=1))>1e-9 for p in expected):raise ValueError('Compound native source station corners differ')
        offset=t if outer else 0
        for solid,b in zip(reversed(operands),branches):
            frame=np.eye(4);normal=np.array([b['side'],0,0]);width=np.array([0,1,0]);frame[:3,:3]=np.column_stack((width,np.cross(normal,width),normal));frame[:3,3]=[0,b['y_m'],0]
            if not solid.is_a('IfcExtrudedAreaSolid') or not solid.SweptArea.is_a('IfcRectangleProfileDef') or solid.SweptArea.Position is not None or not np.allclose([solid.SweptArea.XDim,solid.SweptArea.YDim,solid.Depth],[b['width_m']+2*offset,b['height_m']+2*offset,b['reach_m']],atol=1e-10,rtol=0) or not np.allclose(placement.get_axis2placement(solid.Position),frame,atol=1e-10,rtol=0) or tuple(solid.ExtrudedDirection.DirectionRatios)!=(0.,0.,1.):raise ValueError('Compound branch literal geometry differs')
    ports=system.get_ports(obj);frames=port_frames(data)
    if len(ports)!=len(frames) or len(file.by_type('IfcDistributionPort'))!=len(frames) or {p.Name for p in ports}!=set(frames) or file.by_type('IfcRelConnectsPorts'):raise ValueError('Compound exact unlinked owned boundary ports required')
    for p in ports:
        if p.GlobalId!=stable_guid(data,'IfcDistributionPort',KEY,p.Name) or p.FlowDirection!=data['port_directions'][p.Name] or p.PredefinedType!='DUCT' or p.SystemType!='VENTILATION' or not np.allclose(placement.get_local_placement(p.ObjectPlacement),frames[p.Name],atol=1e-9,rtol=0):raise ValueError('Compound saved cap frame/identity/direction differs')
    settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);shape=ifcopenshell.geom.create_shape(settings,obj);v=np.array(shape.geometry.verts).reshape(-1,3);v=(v-world[:3,3])@world[:3,:3];f=np.array(shape.geometry.faces).reshape(-1,3);solid=from_mesh((v,f));moments=integral(data,True)-integral(data,False);mass=mesh_properties(v,f)
    if len(solid.decompose())!=1 or not math.isclose(solid.volume(),moments[0],rel_tol=1e-8,abs_tol=1e-10) or not np.allclose(mass['centroid'],moments[1:]/moments[0],atol=1e-7,rtol=0):raise ValueError('Compound independent material volume/centroid or connectivity differs')
    edges=Counter(tuple(sorted((int(a),int(b)))) for face in f for a,b in zip(face,[face[1],face[2],face[0]]));euler=len(v)-len(edges)+len(f);expected_euler=2-2*(len(frames)-1)
    if any(n!=2 for n in edges.values()) or euler!=expected_euler:raise ValueError('Compound closed multiport bore topology differs')
    probes=[m.Manifold.cube((min(s['width_m'] for s in stations)*.5,stations[-1]['y_m']-stations[0]['y_m']+.2,min(s['height_m'] for s in stations)*.5),center=True).translate((0,(stations[0]['y_m']+stations[-1]['y_m'])/2,0))]
    probes += [m.Manifold.cube((b['reach_m']+.1,b['width_m']*.5,b['height_m']*.5),center=True).translate((b['side']*(b['reach_m']+.1)/2,b['y_m'],0)) for b in branches]
    for p in probes:
        overlap=solid^p
        if overlap.status()!=m.Error.NoError or abs(overlap.volume())>1e-12:raise ValueError('Compound trunk/takeoff air path blocked')
    return dict(ports=len(frames),one_connected_closed_material=True,euler_characteristic=euler,independent_material_volume_m3=float(moments[0]),native_material_volume_m3=solid.volume(),independent_centroid_m=(moments[1:]/moments[0]).tolist(),all_centre_bores_open=True,schema_express_pass=True,design_accepted=False)


def run(project,out):
    project,out=Path(project).resolve(),Path(out).resolve();data=json.loads(project.read_text());validate(data)
    if out.exists() or not all(allowed(p) for p in (project,out)) or out==project or out in project.parents:raise ValueError('Fresh selected workspace output outside source required')
    versions={n:importlib.metadata.version(n) for n in ('ifcopenshell','manifold3d')}
    if versions!={'ifcopenshell':'0.8.5','manifold3d':'3.5.4'}:raise ValueError('Pinned compound native runtimes required')
    before=digest(project);out.mkdir(parents=True);file=api.run('project.create_file',version='IFC4');api.run('root.create_entity',file,ifc_class='IfcProject',name='Declared compound rectangular junction');unit=api.run('unit.add_si_unit',file,unit_type='LENGTHUNIT');api.run('unit.assign_unit',file,units=[unit]);context=api.run('context.add_context',file,context_type='Model');body=api.run('context.add_context',file,context_type='Model',context_identifier='Body',target_view='MODEL_VIEW',parent=context);builder=ShapeBuilder(file)
    obj=api.run('root.create_entity',file,ifc_class='IfcDuctFitting',predefined_type='JUNCTION',name=KEY);obj.GlobalId=stable_guid(data,'IfcDuctFitting',KEY)
    wall=api.run('geometry.add_boolean',file,first_item=native_union(file,builder,data,True),second_items=[native_union(file,builder,data,False)],operator='DIFFERENCE')[-1];api.run('geometry.assign_representation',file,product=obj,representation=builder.get_representation(body,[wall],representation_type='CSG'));api.run('geometry.edit_object_placement',file,product=obj,matrix=placement_matrix(data),is_si=True)
    for name,frame in port_frames(data).items():
        p=api.run('system.add_port',file,element=obj);p.Name=name;p.GlobalId=stable_guid(data,'IfcDistributionPort',KEY,name);p.FlowDirection=data['port_directions'][name];p.PredefinedType='DUCT';p.SystemType='VENTILATION';api.run('geometry.edit_object_placement',file,product=p,matrix=frame,is_si=True)
    pset=api.run('pset.add_pset',file,product=obj,name='BSA_DesignInputs');api.run('pset.edit_pset',file,pset=pset,properties=dict(Source=data['source'],Classification=data['classification'],Scope='Explicit compound station/side-prism construction; no product, pressure loss or installation acceptance'))
    target=out/'junction.ifc';file.write(str(target));check=inspect(target,data)
    if digest(project)!=before:raise ValueError('Compound source changed')
    result=dict(inputs={str(project):before},versions=versions,generator_sha256=digest(Path(__file__)),ifc_sha256=digest(target),checks=check,design_accepted=False);(out/'junction.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project');p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(run(a.project,a.out)['checks'],indent=2));raise SystemExit(2)
