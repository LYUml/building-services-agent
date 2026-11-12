"""Compile searched planar pipe candidates into existing IFC/pressure inputs."""
import argparse
import copy
import json
import math
from pathlib import Path

from . import circular_elbow as elbow
from .bim import validate
from .cli import digest
from .engine import ProjectError
from .network_binding import prepare, run as bind_run
from .route_search import search


def plane(settings):
    """Cardinal metre frame only; arbitrary rotations/scales remain unsupported."""
    frame=settings.get('plane_frame')
    if 'plane_frame' not in settings:
        z=settings.get('elevation_m')
        if type(z) not in (int,float) or not math.isfinite(z):raise ProjectError('Finite sourced elevation required')
        return [0.,0.,z],[1,0,0],[0,1,0],[0,0,1]
    if 'elevation_m' in settings or not isinstance(frame,dict) or set(frame)!={'origin_m','u_axis','v_axis','source','classification'}:raise ProjectError('Explicit plane frame must not repeat elevation')
    if not isinstance(frame['source'],str) or not frame['source'].strip() or frame['classification'] not in ('given','measured','assumed','secondary_transcription','design_choice','geometry-derived'):raise ProjectError('Source-classified routing plane required')
    origin=frame['origin_m'];axes=[frame['u_axis'],frame['v_axis']]
    if not isinstance(origin,list) or len(origin)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or math.ulp(v)>1e-9 for v in origin):raise ProjectError('Finite supported-precision metre plane origin required')
    cardinal=list(elbow.AXES.values())
    if any(not isinstance(a,list) or len(a)!=3 or any(type(v) not in (int,float) for v in a) or a not in cardinal for a in axes) or sum(a*b for a,b in zip(*axes))!=0:raise ProjectError('Perpendicular signed cardinal plane axes required')
    u,v=axes;normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    return origin,u,v,normal


def endpoint_frames(ifc,binding,network,routing,settings):
    """Compare requested travel tangents with actual saved native port frames."""
    import ifcopenshell
    import ifcopenshell.util.placement as placement
    import ifcopenshell.util.system as system
    import ifcopenshell.util.unit as unit
    origin,u,v,_=plane(settings);model=ifcopenshell.open(str(ifc))
    if not math.isclose(unit.calculate_unit_scale(model),1,rel_tol=0,abs_tol=1e-12):raise ProjectError('Saved route metre units required')
    devices={d.Name:d for d in model.by_type('IfcDistributionElement')}
    if len(devices)!=len(model.by_type('IfcDistributionElement')):raise ProjectError('Duplicate saved route identity')
    segment=network['segments'][0];rows={}
    for role,node,flow,sign in [('start',segment['from'],'SINK',-1),('end',segment['to'],'SOURCE',1)]:
        basis=routing.get('endpoint_directions',{}).get(role)
        if basis is None:continue
        owner,_,name=binding['nodes'][node].rpartition('.');obj=devices[owner];ports=[p for p in system.get_ports(obj) if p.Name==name]
        if len(ports)!=1 or ports[0].FlowDirection!=flow:raise ProjectError('Saved route endpoint ownership/direction differs')
        port=ports[0];matrix=placement.get_local_placement(port.ObjectPlacement);actual=[sign*float(x) for x in matrix[:3,2]];expected=[basis['axis'][0]*u[i]+basis['axis'][1]*v[i] for i in range(3)]
        if any(not math.isfinite(float(x)) for x in matrix.flatten()) or any(not math.isclose(sum(float(matrix[k,i]*matrix[k,j]) for k in range(3)),1. if i==j else 0.,abs_tol=1e-8,rel_tol=0) for i in range(3) for j in range(3)):raise ProjectError('Finite orthonormal saved endpoint frame required')
        point=[origin[i]+routing[role+'_m'][0]*u[i]+routing[role+'_m'][1]*v[i] for i in range(3)]
        if math.dist(matrix[:3,3],point)>1e-8:raise ProjectError('Saved endpoint position differs from route source')
        if math.dist(actual,expected)>1e-8:raise ProjectError('Saved native endpoint travel tangent differs')
        rows[role]=dict(owner_guid=obj.GlobalId,port_guid=port.GlobalId,point_m=matrix[:3,3].tolist(),outward_axis=matrix[:3,2].tolist(),travel_direction=actual,expected_travel_direction=expected,basis=basis,native_frame_match=True)
    return rows


def compile_route(routing, settings, network):
    route=search(routing)
    if not route['route_found']:raise ProjectError('no searched route to compile')
    for name in ('source','name','project_uuid'):
        if not isinstance(settings.get(name),str) or not settings[name].strip():raise ProjectError(f'explicit {name} required')
    origin,plane_u,plane_v,normal=plane(settings)
    if ('plane_frame' in settings)!=(routing.get('coordinate_plane','world-xy')=='declared-local-frame'):raise ProjectError('Routing coordinate plane and declared frame must correspond')
    for name in ('inside_diameter_m','elbow_excess_k','straight_excess_k'):
        value=settings.get(name)
        if type(value) not in (int,float) or not math.isfinite(value):raise ProjectError(f'finite sourced {name} required')
    inner=settings['inside_diameter_m'];outer=routing['outside_diameter_m'];radius=routing['bend_radius_m'];ro=outer/2
    if not 0<inner<outer or min(settings['elbow_excess_k'],settings['straight_excess_k'])<0:raise ProjectError('valid bore/OD and nonnegative explicit excess K required')
    if settings.get('loss_basis')!=elbow.LOSS_BASIS:raise ProjectError('explicit excess-over-centreline-friction loss basis required')
    room=copy.deepcopy(settings.get('space'));system=copy.deepcopy(settings.get('system'))
    if not isinstance(room,dict) or not isinstance(system,dict):raise ProjectError('explicit containing space and system required')
    family=settings.get('element_family','pipe')
    if family not in ('pipe','duct') or family=='duct' and system.get('predefined_type') not in ('AIRCONDITIONING','VENTILATION'):raise ProjectError('Supported pipe or explicitly air-system duct family required')
    room['source']=system['source']='design'
    model=dict(name=settings['name'],project_uuid=settings['project_uuid'],geometry_scope=elbow.SCOPE,
               sources={'design':settings['source'],'route':routing['source']},spaces=[room],systems=[system],devices=[],connections=[])
    def world(p):return [origin[i]+p[0]*plane_u[i]+p[1]*plane_v[i] for i in range(3)]
    def signed(v):
        axis=next(i for i,x in enumerate(v) if abs(x)>.5)
        return ('+' if v[axis]>0 else '-')+'XYZ'[axis]
    for index,piece in enumerate(route['pieces']):
        a,b=world(piece['start_m']),world(piece['end_m']);name=f'ROUTE_{index+1:03d}'
        is_bend=piece['kind']=='elbow'
        properties=dict(InternalDiameter_m=inner,OutsideDiameter_m=outer,
                        LocalLossCoefficient=settings['elbow_excess_k' if is_bend else 'straight_excess_k'],LocalLossBasis=elbow.LOSS_BASIS)
        device=dict(id=name,ifc_class=('IfcDuctFitting' if is_bend else 'IfcDuctSegment') if family=='duct' else ('IfcPipeFitting' if is_bend else 'IfcPipeSegment'),space=room['id'],system=system['id'],source='design',
                    body_shape=elbow.WALL if is_bend else 'straight circular wall',properties=properties)
        if is_bend:
            centre=world(piece['centre_m']);u=[(a[i]-centre[i])/radius for i in range(3)];v=[(b[i]-centre[i])/radius for i in range(3)]
            lo=[centre[i]+min(0,u[i]*(radius+ro))+min(0,v[i]*(radius+ro))-abs(normal[i])*ro for i in range(3)]
            hi=[centre[i]+max(0,u[i]*(radius+ro))+max(0,v[i]*(radius+ro))+abs(normal[i])*ro for i in range(3)]
            device.update(arc_center_m=centre,bend_axes=[signed(u),signed(v)])
            properties['CenterlineRadius_m']=radius
        else:
            axis=next(i for i in range(3) if abs(a[i]-b[i])>1e-9)
            lo=[min(a[i],b[i])-(ro if i!=axis else 0) for i in range(3)]
            hi=[max(a[i],b[i])+(ro if i!=axis else 0) for i in range(3)]
        device.update(origin_m=lo,size_m=[hi[i]-lo[i] for i in range(3)],ports=[
            dict(id=port,direction=direction,offset_m=[p[i]-lo[i] for i in range(3)],source='design')
            for port,direction,p in [('in','SINK',a),('out','SOURCE',b)]])
        model['devices'].append(device)
        if index:model['connections'].append(dict(source='design',**{'from':model['devices'][-2]['id']+'.out','to':name+'.in'}))
    validate(model)
    hydraulic=copy.deepcopy(network)
    if len(hydraulic.get('segments',[]))!=1:raise ProjectError('one explicit hydraulic segment required for this route compiler')
    segment=hydraulic['segments'][0]
    if any(k in segment for k in ('length_m','diameter_m','minor_k')):raise ProjectError('do not duplicate generated length, bore or loss coefficients')
    if not route['bend_count']:segment['minor_k']=len(route['pieces'])*settings['straight_excess_k']
    binding=dict(source=settings['source']+'; searched geometry: '+routing['source'],nodes={segment['from']:model['devices'][0]['id']+'.in',segment['to']:model['devices'][-1]['id']+'.out'},segments={segment['id']:[d['id'] for d in model['devices']]})
    derived,_=prepare(hydraulic,model,binding)
    if not math.isclose(derived['segments'][0]['length_m'],route['length_m'],abs_tol=1e-8):raise ProjectError('compiled route length differs from search')
    return route,model,binding,hydraulic


def run(routing,settings,network,out):
    import importlib.metadata
    from . import bim,network_binding,circular_geometry,network as pressure
    import fluids.core
    import fluids.friction
    paths=[Path(p).resolve() for p in (routing,settings,network)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain source inputs')
    before={str(p):digest(p) for p in paths}
    methods={str(Path(p).resolve()):digest(Path(p)) for p in (__file__,search.__code__.co_filename,bim.__file__,network_binding.__file__,elbow.__file__,circular_geometry.__file__,pressure.__file__,fluids.core.__file__,fluids.friction.__file__)}
    versions={name:importlib.metadata.version(name) for name in ('ifcopenshell','fluids','numpy')}
    if versions!={'ifcopenshell':'0.8.5','fluids':'1.3.1','numpy':'2.5.4'}:raise ProjectError('Pinned native route runtimes required')
    routing_data,settings_data,network_data=[json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
    route,model,binding,hydraulic=compile_route(routing_data,settings_data,network_data)
    out.mkdir(parents=True,exist_ok=False)
    for name,data in [('route',route),('model-input',model),('binding-input',binding),('network-source',hydraulic)]:
        (out/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
    result=bind_run(out/'network-source.json',out/'model-input.json',out/'binding-input.json',out/'bound')
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('routing sources changed')
    report=dict(inputs=before,inputs_unchanged=True,route_length_m=route['length_m'],bend_count=route['bend_count'],
                saved_ifc_geometry_match=result['saved_ifc_geometry_match'],calculated_checks_pass=result['calculated_checks_pass'],design_accepted=False,
                pending=['saved-model clash and route self-clearance','obstacle IFC correspondence','hydraulic route optimisation','native drawing and visual review','product and engineering acceptance'])
    if routing_data.get('endpoint_directions'):
        report['endpoint_frames']=endpoint_frames(out/'bound/bim/model.ifc',binding,hydraulic,routing_data,settings_data)
    if settings_data.get('plane_frame') is not None:report['plane_frame']=settings_data['plane_frame']
    report['element_family']=settings_data.get('element_family','pipe');report['method_inputs']=methods;report['runtime_versions']=versions
    if any(digest(Path(p))!=h for p,h in {**before,**methods}.items()):raise ProjectError('Route source or method changed during native checks')
    (out/'route-model.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('routing',type=Path)
    for key in ('settings','network','out'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();result=run(args.routing,args.settings,args.network,args.out)
    print(json.dumps(result,indent=2));return 0 if result['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
