"""Finite-grid planar routing with explicit 90-degree bends and conservative bounds."""
import argparse
import heapq
import json
import math
from pathlib import Path

from .cli import digest
from .engine import ProjectError


def search(data):
    def number(value):
        return type(value) in (int,float) and math.isfinite(value)
    def point(value):
        return isinstance(value,list) and len(value)==2 and all(number(v) for v in value)
    if not isinstance(data.get('source'),str) or not data['source'].strip():
        raise ProjectError('routing input provenance required')
    if data.get('units')!='m':raise ProjectError('routing uses explicit metre units')
    if data.get('coordinate_plane','world-xy') not in ('world-xy','declared-local-frame'):raise ProjectError('Supported routing coordinate-plane declaration required')
    start,end=data.get('start_m'),data.get('end_m')
    origin=data.get('grid_origin_m');counts=data.get('grid_counts')
    step=data.get('grid_step_m');radius=data.get('bend_radius_m')
    outer=data.get('outside_diameter_m');clearance=data.get('clearance_m')
    penalty=data.get('bend_penalty_m',0.)
    if not number(penalty) or penalty<0 or ('bend_penalty_m' in data and (not isinstance(data.get('objective_source'),str) or not data['objective_source'].strip())):
        raise ProjectError('nonnegative bend penalty and explicit objective provenance required')
    if not all(point(v) for v in (start,end,origin)) or not isinstance(counts,list) or len(counts)!=2 or any(type(v)!=int or v<2 for v in counts):
        raise ProjectError('finite planar endpoints/origin and integer grid counts required')
    if not all(number(v) for v in (step,radius,outer,clearance)) or not 0<outer/2<radius or step<=2*radius or clearance<0:
        raise ProjectError('require positive OD, radius > OD/2, step > 2 radius and nonnegative clearance')
    if counts[0]*counts[1]>50000:raise ProjectError('routing grid exceeds 50000-node search budget')
    if any(math.ulp(v)>1e-9 for v in (*start,*end,*origin,step,radius,outer,clearance)):
        raise ProjectError('routing coordinates exceed supported numerical precision')
    obstacles=data.get('obstacles')
    if not isinstance(obstacles,list):raise ProjectError('explicit obstacle inventory required')
    boxes=[];ids=set()
    for obstacle in obstacles:
        if not isinstance(obstacle,dict):raise ProjectError('obstacle object required')
        name=obstacle.get('id');lo=obstacle.get('min_m');hi=obstacle.get('max_m')
        if not isinstance(name,str) or not name or name in ids or not point(lo) or not point(hi) or any(a>=b for a,b in zip(lo,hi)) or not isinstance(obstacle.get('source'),str) or not obstacle['source'].strip():
            raise ProjectError('unique sourced obstacle rectangles required')
        ids.add(name);boxes.append((lo,hi))
    ro=outer/2
    def world(node):return [origin[i]+step*node[i] for i in (0,1)]
    def index(p):
        node=tuple(round((p[i]-origin[i])/step) for i in (0,1))
        if any(not 0<=node[i]<counts[i] for i in (0,1)) or math.dist(p,world(node))>1e-8:
            raise ProjectError('endpoints must lie on the declared finite grid')
        return node
    first,last=index(start),index(end)
    if first==last:raise ProjectError('distinct routing endpoints required')
    # The declared grid spans a centreline search region. Physical route bounds
    # extend by OD/2; callers must supply actual available-space obstacles.
    def clear(lo,hi):
        return not any(all(hi[i]+clearance>b[0][i]+1e-10 and lo[i]-clearance<b[1][i]-1e-10 for i in (0,1)) for b in boxes)
    def line_clear(a,b):
        return clear([min(a[i],b[i])-ro for i in (0,1)],[max(a[i],b[i])+ro for i in (0,1)])
    directions=((1,0),(0,1),(-1,0),(0,-1))
    constraints=data.get('endpoint_directions')
    headings={}
    if constraints is not None:
        if not isinstance(constraints,dict) or not constraints or set(constraints)-{'start','end'}:raise ProjectError('Explicit start/end travel direction records required')
        for role,row in constraints.items():
            if not isinstance(row,dict) or set(row)!={'axis','source','classification'} or not point(row['axis']) or tuple(row['axis']) not in directions or not isinstance(row['source'],str) or not row['source'].strip() or row['classification'] not in ('given','measured','assumed','secondary_transcription','design_choice','geometry-derived'):raise ProjectError('Source-classified cardinal endpoint travel direction required')
            headings[role]=directions.index(tuple(row['axis']))
    def bend(a,u,v):
        entry=[a[i]-radius*u[i] for i in (0,1)]
        exit=[a[i]+radius*v[i] for i in (0,1)]
        centre=[entry[i]+radius*v[i] for i in (0,1)]
        # Exact extrema of a cardinal quarter-circle, expanded by tube radius.
        lo=[min(entry[i],exit[i])-ro for i in (0,1)]
        hi=[max(entry[i],exit[i])+ro for i in (0,1)]
        return dict(kind='elbow',start_m=entry,end_m=exit,centre_m=centre,
                    radius_m=radius,length_m=math.pi*radius/2,min_m=lo,max_m=hi)
    if not line_clear(start,start) or not line_clear(end,end):
        raise ProjectError('route endpoint violates obstacle clearance')
    initial=(*first,-1);dist={initial:0.};previous={};queue=[(0.,initial)];goal=None
    while queue:
        cost,state=heapq.heappop(queue)
        if cost!=dist[state]:continue
        x,y,heading=state
        if (x,y)==last:goal=state;break
        a=world((x,y))
        for direction,v in enumerate(directions):
            if heading<0 and 'start' in headings and direction!=headings['start']:continue
            if heading>=0 and direction==(heading+2)%4:continue
            node=(x+v[0],y+v[1])
            if any(not 0<=node[i]<counts[i] for i in (0,1)):continue
            if node==last and 'end' in headings and direction!=headings['end']:continue
            b=world(node)
            if not line_clear(a,b):continue
            turning=heading>=0 and heading!=direction
            if turning:
                piece=bend(a,directions[heading],v)
                if not clear(piece['min_m'],piece['max_m']):continue
            increment=step+(radius*(math.pi/2-2)+penalty if turning else 0.)
            target=(*node,direction);candidate=cost+increment
            if candidate<dist.get(target,math.inf)-1e-12:
                dist[target]=candidate;previous[target]=state
                heapq.heappush(queue,(candidate,target))
    base=dict(source=data['source'],design_accepted=False,visited_states=len(dist),
              bend_penalty_m=penalty,objective_source=data.get('objective_source','physical centreline length only'),
              scope='minimum centreline length plus declared per-bend penalty among accepted finite-grid paths; conservative rectangle clearance; no BIM, hydraulic, product or installation acceptance')
    if constraints is not None:base['endpoint_directions']=constraints
    if 'coordinate_plane' in data:base['coordinate_plane']=data['coordinate_plane']
    if goal is None:return dict(**base,route_found=False,reason='no path on the declared grid under conservative clearance checks')
    chain=[];state=goal
    while state!=initial:chain.append(world(state[:2]));state=previous[state]
    chain.append(start);chain.reverse()
    vertices=[chain[0]]
    for i in range(1,len(chain)-1):
        u=[chain[i][k]-chain[i-1][k] for k in (0,1)]
        v=[chain[i+1][k]-chain[i][k] for k in (0,1)]
        if u[0]*v[1]-u[1]*v[0]:vertices.append(chain[i])
    vertices.append(chain[-1]);pieces=[];cursor=start
    def straight(a,b):
        length=math.dist(a,b)
        if length<=1e-9:raise ProjectError('route produced a degenerate trimmed straight')
        return dict(kind='straight',start_m=a,end_m=b,length_m=length,
                    min_m=[min(a[i],b[i])-ro for i in (0,1)],max_m=[max(a[i],b[i])+ro for i in (0,1)])
    for a,b,c in zip(vertices,vertices[1:],vertices[2:]):
        u=[(b[i]-a[i])/math.dist(a,b) for i in (0,1)]
        v=[(c[i]-b[i])/math.dist(b,c) for i in (0,1)]
        piece=bend(b,u,v);pieces.extend((straight(cursor,piece['start_m']),piece));cursor=piece['end_m']
    pieces.append(straight(cursor,end))
    length=sum(p['length_m'] for p in pieces)
    bends=sum(p['kind']=='elbow' for p in pieces)
    if not math.isclose(length+bends*penalty,dist[goal],abs_tol=1e-8,rel_tol=1e-12):raise ProjectError('search cost differs from finite bend geometry and declared penalty')
    if any(not clear(p['min_m'],p['max_m']) for p in pieces):raise ProjectError('compiled route violates obstacle clearance')
    for role,piece in (('start',pieces[0]),('end',pieces[-1])):
        if role not in headings:continue
        vector=[(piece['end_m'][i]-piece['start_m'][i])/piece['length_m'] for i in (0,1)]
        if math.dist(vector,directions[headings[role]])>1e-8:raise ProjectError('Compiled route violates endpoint travel tangent')
    return dict(**base,route_found=True,vertices_m=vertices,pieces=pieces,length_m=length,
                bend_count=bends,objective_cost_m=dist[goal],obstacle_ids=sorted(ids))


def run(source,out):
    source,out=Path(source).resolve(),Path(out).resolve()
    if out==source or out in source.parents:raise ProjectError('output must not contain source')
    before=digest(source);result=search(json.loads(source.read_text(encoding='utf-8-sig')))
    if digest(source)!=before:raise ProjectError('routing source changed')
    result.update(input_sha256=before,input_unchanged=True)
    out.mkdir(parents=True,exist_ok=False)
    (out/'route.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:result=run(args.source,args.out)
    except (ProjectError,OSError,ValueError) as exc:parser.exit(2,str(exc)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['route_found'] else 2


if __name__=='__main__':raise SystemExit(main())
