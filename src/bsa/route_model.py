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


def compile_route(routing, settings, network):
    route=search(routing)
    if not route['route_found']:raise ProjectError('no searched route to compile')
    for name in ('source','name','project_uuid'):
        if not isinstance(settings.get(name),str) or not settings[name].strip():raise ProjectError(f'explicit {name} required')
    for name in ('elevation_m','inside_diameter_m','elbow_excess_k','straight_excess_k'):
        value=settings.get(name)
        if type(value) not in (int,float) or not math.isfinite(value):raise ProjectError(f'finite sourced {name} required')
    inner=settings['inside_diameter_m'];outer=routing['outside_diameter_m'];radius=routing['bend_radius_m'];ro=outer/2
    if not 0<inner<outer or min(settings['elbow_excess_k'],settings['straight_excess_k'])<0:raise ProjectError('valid bore/OD and nonnegative explicit excess K required')
    if settings.get('loss_basis')!=elbow.LOSS_BASIS:raise ProjectError('explicit excess-over-centreline-friction loss basis required')
    room=copy.deepcopy(settings.get('space'));system=copy.deepcopy(settings.get('system'))
    if not isinstance(room,dict) or not isinstance(system,dict):raise ProjectError('explicit containing space and system required')
    room['source']=system['source']='design'
    model=dict(name=settings['name'],project_uuid=settings['project_uuid'],geometry_scope=elbow.SCOPE,
               sources={'design':settings['source'],'route':routing['source']},spaces=[room],systems=[system],devices=[],connections=[])
    def world(p):return [*p,settings['elevation_m']]
    def signed(v):
        axis=next(i for i,x in enumerate(v) if abs(x)>.5)
        return ('+' if v[axis]>0 else '-')+'XYZ'[axis]
    for index,piece in enumerate(route['pieces']):
        a,b=world(piece['start_m']),world(piece['end_m']);name=f'ROUTE_{index+1:03d}'
        is_bend=piece['kind']=='elbow'
        properties=dict(InternalDiameter_m=inner,OutsideDiameter_m=outer,
                        LocalLossCoefficient=settings['elbow_excess_k' if is_bend else 'straight_excess_k'],LocalLossBasis=elbow.LOSS_BASIS)
        device=dict(id=name,ifc_class='IfcPipeFitting' if is_bend else 'IfcPipeSegment',space=room['id'],system=system['id'],source='design',
                    body_shape=elbow.WALL if is_bend else 'straight circular wall',properties=properties)
        if is_bend:
            centre=world(piece['centre_m']);u=[(a[i]-centre[i])/radius for i in range(3)];v=[(b[i]-centre[i])/radius for i in range(3)]
            lo=[centre[i]+min(0,u[i]*(radius+ro))+min(0,v[i]*(radius+ro))-(ro if i==2 else 0) for i in range(3)]
            hi=[centre[i]+max(0,u[i]*(radius+ro))+max(0,v[i]*(radius+ro))+(ro if i==2 else 0) for i in range(3)]
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
    paths=[Path(p).resolve() for p in (routing,settings,network)];out=Path(out).resolve()
    if any(out==p or out in p.parents for p in paths):raise ProjectError('output must not contain source inputs')
    before={str(p):digest(p) for p in paths}
    route,model,binding,hydraulic=compile_route(*(json.loads(p.read_text(encoding='utf-8-sig')) for p in paths))
    out.mkdir(parents=True,exist_ok=False)
    for name,data in [('route',route),('model-input',model),('binding-input',binding),('network-source',hydraulic)]:
        (out/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
    result=bind_run(out/'network-source.json',out/'model-input.json',out/'binding-input.json',out/'bound')
    if any(digest(Path(p))!=h for p,h in before.items()):raise ProjectError('routing sources changed')
    report=dict(inputs=before,inputs_unchanged=True,route_length_m=route['length_m'],bend_count=route['bend_count'],
                saved_ifc_geometry_match=result['saved_ifc_geometry_match'],calculated_checks_pass=result['calculated_checks_pass'],design_accepted=False,
                pending=['saved-model clash and route self-clearance','obstacle IFC correspondence','hydraulic route optimisation','native drawing and visual review','product and engineering acceptance'])
    (out/'route-model.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('routing',type=Path)
    for key in ('settings','network','out'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();result=run(args.routing,args.settings,args.network,args.out)
    print(json.dumps(result,indent=2));return 0 if result['calculated_checks_pass'] else 2


if __name__=='__main__':raise SystemExit(main())
