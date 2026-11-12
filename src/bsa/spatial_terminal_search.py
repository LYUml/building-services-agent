"""Bounded automatic terminal candidate search using existing allocation/catalogue engines."""
import argparse
import json
import os
from pathlib import Path
from shapely.geometry import Polygon,box,mapping
from .cli import digest
from .module_contract import read_json
from .modules import verify_result
from .workspace import allowed
from . import spatial_terminal_performance as performance
from . import spatial_air_allocation as allocation
from . import air_allocation,terminal_performance,spatial_terminal_revision as revision


def prepare(balance,producer,old,selected,policy):
    if not isinstance(policy,dict) or set(policy)!={'grids','objective','product_from_terminal'}:raise ValueError('Exact grid search policy required')
    for key in ('grids','objective'):
        row=policy[key]
        if not isinstance(row,dict) or set(row)!={'value','source','classification'} or not isinstance(row['source'],str) or not row['source'].strip() or row['classification']!='design_choice':raise ValueError('Explicit source-classified search design choices required')
    if policy['objective']['value']!='fewest_terminals_with_catalogue_coverage':raise ValueError('Supported explicit search objective required')
    grids=policy['grids']['value']
    if not isinstance(grids,list) or not grids or len(grids)>32 or any(not isinstance(g,list) or len(g)!=2 or any(type(v) is not int or v<1 for v in g) or g[0]*g[1]>16 for g in grids) or len({tuple(g) for g in grids})!=len(grids):raise ValueError('Unique bounded positive grid shapes required')
    rooms=balance['calculation']['room_balances'];spaces={s['id']:s for s in producer['payload']['spaces']}
    if set(rooms)!=set(spaces) or not isinstance(policy['product_from_terminal'],dict) or set(policy['product_from_terminal'])!=set(rooms):raise ValueError('Exact source-room product mapping required')
    trials={};basis={};products={};all_feasible=True
    for guid in sorted(rooms):
        previous=old['calculation']['rooms'][guid];old_ids={t['id'] for t in previous['allocation']['terminals']};chosen=policy['product_from_terminal'][guid]
        if chosen not in old_ids or chosen not in selected:raise ValueError('Product must inherit an original terminal in the same room')
        product=selected[chosen];space=spaces[guid]
        boundary=Polygon(space['boundary_vertices']) if producer['payload_schema']=='bsa.spatial-polygons/1' else box(space['origin_m'][0],space['origin_m'][1],space['origin_m'][0]+space['size_m'][0],space['origin_m'][1]+space['size_m'][1])
        boundary=boundary.normalize();x0,y0,x1,y1=boundary.bounds;attempts=[];feasible=[]
        for index,(nx,ny) in enumerate(grids):
            points=[];reason=None
            for ix in range(nx):
                for iy in range(ny):
                    cell=boundary.intersection(box(x0+(x1-x0)*ix/nx,y0+(y1-y0)*iy/ny,x0+(x1-x0)*(ix+1)/nx,y0+(y1-y0)*(iy+1)/ny))
                    if cell.is_empty or cell.area<=0:reason='empty_grid_cell';break
                    point=cell.representative_point();points.append(dict(id=guid+'_grid'+str(index+1)+'_'+str(len(points)+1),center_m=[point.x,point.y]))
                if reason:break
            attempt=dict(grid=[nx,ny],terminal_count=nx*ny,status='rejected',reason=reason,cases=[])
            if not reason:
                assigned=air_allocation.prepare(mapping(boundary),points,rooms[guid]['inputs'],previous['design_basis']['turndown']['value'])
                if assigned['load']!=rooms[guid]:raise ValueError('Search changed inherited load inputs')
                for terminal in assigned['terminals']:
                    for condition,key in [('maximum','maximum_flow_L_s'),('minimum','minimum_flow_L_s')]:
                        calculated=terminal_performance.calculate(product['catalogue']['rows'],terminal[key]);attempt['cases'].append(dict(terminal=terminal['id'],condition=condition,**calculated))
                outside=sum(c['status']=='outside_catalogue' for c in attempt['cases']);attempt['outside_catalogue_cases']=outside
                if not outside:
                    attempt.update(status='catalogue_covered',reason=None);feasible.append((nx*ny,index,points))
                else:attempt['reason']='operating_flow_outside_catalogue'
            attempts.append(attempt)
        trials[guid]=dict(product_from_terminal=chosen,attempts=attempts,selected_grid_index=None)
        if not feasible:all_feasible=False;continue
        _,index,points=min(feasible,key=lambda row:(row[0],row[1]));trials[guid]['selected_grid_index']=index
        basis[guid]=dict(turndown=previous['design_basis']['turndown'],terminals=[dict(p,unit='m',classification='design_choice',source='Bounded source-polygon grid representative point; '+policy['grids']['source']+'; not installed position or air-coverage validation') for p in points])
        for p in points:products[p['id']]=chosen
    return dict(rooms=trials,status='candidate_available' if all_feasible else 'no_feasible_candidate',basis=basis if all_feasible else None,product_inheritance=products if all_feasible else None,design_accepted=False,
        scope='Fewest terminals only within declared sampled grids and inherited catalogue flow ranges; ties follow declared grid order. Not global optimization,ADPI,acoustics,physical fit,routing or engineering acceptance')


def source(original,policy):
    if original.name!='terminal-performance.json' or not allowed(original) or not allowed(policy):raise ValueError('Exact selected original performance and policy required')
    before=performance.verify(original.parent);old=allocation.verify(Path(before['allocation_result']).parent)
    from . import spatial_air_balance
    balance=spatial_air_balance.verify(Path(old['balance_result']).parent);producer=verify_result(balance['producer_result'])
    selected,pins=performance.selections(Path(before['basis']));pins.update(before['inputs']);pins[str(original)]=digest(original);pins[str(policy)]=digest(policy);pins[str(Path(__file__).resolve())]=digest(Path(__file__))
    return before,old,balance,producer,selected,pins


def product_basis(before,selected,proposal,out):
    products={}
    for terminal,ancestor in proposal['product_inheritance'].items():
        row=selected[ancestor]['selection'];setting=(Path(before['basis']).parent/row['settings']).resolve()
        products[terminal]=dict(row,settings=os.path.relpath(setting,out))
    return products


def run(original,policy,out,drawing_settings=None):
    original,policy,out=[Path(p).resolve() for p in (original,policy,out)]
    if not all(allowed(p) for p in (original,policy,out)) or original.name!='terminal-performance.json' or out.exists():raise ValueError('Verified original sources and fresh selected search output required')
    before,old,balance,producer,selected,pins=source(original,policy);proposal=prepare(balance,producer,old,selected,read_json(policy))
    if any(out==Path(p) or out in Path(p).parents for p in pins):raise ValueError('Search output overlaps source')
    if drawing_settings is not None:
        drawing_settings=Path(drawing_settings).resolve()
        if not allowed(drawing_settings):raise ValueError('Selected drawing settings required')
        pins[str(drawing_settings)]=digest(drawing_settings)
    out.mkdir(parents=True)
    if proposal['status']=='candidate_available':
        basis=out/'terminal-basis.json';basis.write_text(json.dumps(proposal['basis'],indent=2),encoding='utf-8')
        path=out/'products.json';path.write_text(json.dumps(product_basis(before,selected,proposal,out),indent=2),encoding='utf-8')
        revision.run(original,basis,path,out/'candidate')
        if drawing_settings is not None:
            from . import spatial_terminal_drawing
            spatial_terminal_drawing.run(out/'candidate/allocation/terminal-allocation.json',drawing_settings,out/'drawing')
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Search source changed')
    result=dict(original=str(original),policy=str(policy),inputs=pins,proposal=proposal,drawing_settings=str(drawing_settings) if drawing_settings else None,design_accepted=False)
    result['artifacts']={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'search.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected search workspace required')
    result=read_json(folder/'search.json');original=Path(result['original']);policy=Path(result['policy'])
    if not allowed(original) or not allowed(policy):raise ValueError('Selected search sources required')
    before,old,balance,producer,selected,pins=source(original,policy)
    if result['drawing_settings'] is not None:
        if not allowed(Path(result['drawing_settings'])):raise ValueError('Selected drawing settings required')
        pins[result['drawing_settings']]=digest(Path(result['drawing_settings']))
    expected=prepare(balance,producer,old,selected,read_json(policy));artifacts={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file() and p!=folder/'search.json'}
    if set(result)!={'original','policy','inputs','proposal','drawing_settings','design_accepted','artifacts'} or result['design_accepted'] is not False or result['proposal']!=expected or result['inputs']!=pins or result['artifacts']!=artifacts or any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Search source/proposal/artifact replay differs')
    if expected['status']=='candidate_available':
        candidate=revision.verify(folder/'candidate')
        if candidate['original']!=str(original) or candidate['basis']!=str(folder/'terminal-basis.json') or candidate['products']!=str(folder/'products.json'):raise ValueError('Search candidate replaced source bindings')
        if read_json(folder/'products.json')!=product_basis(before,selected,expected,folder):raise ValueError('Search replaced inherited product selection')
        if read_json(folder/'terminal-basis.json')!=expected['basis']:raise ValueError('Search replaced proposed terminal basis')
        if result['drawing_settings'] is not None:
            from . import spatial_terminal_drawing
            drawing=spatial_terminal_drawing.verify(folder/'drawing')
            if drawing['allocation']!=str(folder/'candidate/allocation/terminal-allocation.json') or drawing['settings']!=result['drawing_settings']:raise ValueError('Search drawing replaced selected allocation/settings')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('original');parser.add_argument('--policy',required=True);parser.add_argument('--out',required=True);parser.add_argument('--drawing-settings');a=parser.parse_args();r=run(a.original,a.policy,a.out,a.drawing_settings);print(r['proposal']['status'],'design acceptance pending')
